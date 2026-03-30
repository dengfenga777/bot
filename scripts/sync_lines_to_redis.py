#!/usr/bin/env python3
"""
Redis 线路同步脚本
将数据库中的用户线路绑定同步到 Redis 缓存
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import redis

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from app.config import settings
from app.log import logger


# 线路映射配置
# 将线路域名映射为 VPS IP:Port
# 注意: 默认线路是主域名 (emby.misaya.org / plex.misaya.org)，不需要映射
LINE_MAPPING = {
    # ===== 可选线路 =====
    "hk.stream.misaya.org": "154.3.36.75:443",      # 香港线路
    "sg.stream.misaya.org": "213.35.105.166:443",   # 新加坡线路
    "us.stream.misaya.org": "146.235.219.32:443",   # 美国线路
    "jp.stream.misaya.org": "154.31.114.167:443",   # 日本线路 (Premium)

    # ===== 默认线路 =====
    # 默认线路是主域名，用户直连主服务器，不经过 VPS
    # 当用户未绑定线路时，Lua 脚本会使用本地 127.0.0.1
    "default": "",  # 空值表示使用默认（本地）
}


class RedisLineSync:
    """Redis 线路同步器"""

    # 本地 Redis 配置 (脚本在宿主机运行，直接连接本地 Redis)
    # Docker 容器内的应用使用 Docker 网络名称 (pmsmanagebot-redis)
    LOCAL_REDIS_HOST = "127.0.0.1"
    LOCAL_REDIS_PORT = 6379

    def __init__(self):
        """初始化 Redis 连接和数据库连接"""
        # 连接 Redis (使用本地地址，因为脚本在宿主机上运行)
        try:
            self.redis_client = redis.Redis(
                host=self.LOCAL_REDIS_HOST,
                port=self.LOCAL_REDIS_PORT,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,  # 自动解码为字符串
            )
            # 测试连接
            self.redis_client.ping()
            logger.info(f"Redis 连接成功: {self.LOCAL_REDIS_HOST}:{self.LOCAL_REDIS_PORT}")
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            raise

        # 连接数据库
        try:
            self.db_path = settings.DATA_PATH / "data.db"
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            logger.info(f"数据库连接成功: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def map_line_to_vps(self, line_name: str) -> str:
        """
        将线路名称映射为 VPS IP:Port

        Args:
            line_name: 线路域名 (如 "hk.stream.misaya.org")

        Returns:
            VPS IP:Port (如 "154.3.36.75:443")
        """
        if not line_name:
            return LINE_MAPPING["default"]

        # 精确匹配
        if line_name in LINE_MAPPING:
            return LINE_MAPPING[line_name]

        # 模糊匹配 (如果线路名只包含关键词)
        line_lower = line_name.lower()
        for key in LINE_MAPPING:
            if key in line_lower or line_lower in key:
                return LINE_MAPPING[key]

        # 如果没有匹配，返回默认线路
        logger.warning(f"未找到线路映射: {line_name}，使用默认线路")
        return LINE_MAPPING["default"]

    def sync_emby_lines(self) -> int:
        """
        同步 Emby 用户线路到 Redis

        Returns:
            同步的用户数量
        """
        try:
            # 查询所有绑定了线路的 Emby 用户
            query = """
                SELECT emby_id, emby_username, emby_line
                FROM emby_user
                WHERE emby_line IS NOT NULL AND emby_line != ''
            """
            self.cursor.execute(query)
            users = self.cursor.fetchall()

            synced_count = 0
            for emby_id, emby_username, emby_line in users:
                # 映射线路为 VPS IP
                vps_address = self.map_line_to_vps(emby_line)

                # 写入 Redis
                redis_key = f"emby_line:{emby_id}"
                self.redis_client.set(redis_key, vps_address)

                logger.debug(f"同步 Emby 用户: {emby_username} ({emby_id}) -> {emby_line} -> {vps_address}")
                synced_count += 1

            logger.info(f"Emby 用户线路同步完成: {synced_count} 个用户")
            return synced_count

        except Exception as e:
            logger.error(f"同步 Emby 线路失败: {e}")
            return 0

    def sync_plex_lines(self) -> int:
        """
        同步 Plex 用户线路到 Redis

        注意: Nginx Lua 脚本使用 plex_email:<plex_username> 作为键
        通过 Plex API 获取 username 后查询 Redis

        Returns:
            同步的用户数量
        """
        try:
            # 查询所有绑定了线路的 Plex 用户
            query = """
                SELECT plex_id, plex_username, plex_line
                FROM user
                WHERE plex_line IS NOT NULL AND plex_line != ''
            """
            self.cursor.execute(query)
            users = self.cursor.fetchall()

            synced_count = 0
            for plex_id, plex_username, plex_line in users:
                # 映射线路为 VPS IP
                vps_address = self.map_line_to_vps(plex_line)

                # Nginx Lua 脚本使用 plex_email:<plex_username> 作为键
                # 因为 Lua 脚本通过 Plex API 获取的是 username
                redis_key = f"plex_email:{plex_username}"
                self.redis_client.set(redis_key, vps_address)

                logger.debug(f"同步 Plex 用户: {plex_username} ({plex_id}) -> {plex_line} -> {vps_address}")
                synced_count += 1

            logger.info(f"Plex 用户线路同步完成: {synced_count} 个用户")
            return synced_count

        except Exception as e:
            logger.error(f"同步 Plex 线路失败: {e}")
            return 0

    def set_default_line(self):
        """设置默认线路到 Redis"""
        try:
            default_vps = LINE_MAPPING.get("default", "")
            if default_vps:
                # 有指定默认 VPS，设置到 Redis
                self.redis_client.set("default_line", default_vps)
                logger.info(f"默认线路设置完成: {default_vps}")
            else:
                # 默认线路是主域名直连，删除 Redis 中的 default_line 键
                self.redis_client.delete("default_line")
                logger.info("默认线路: 主域名直连 (无 VPS 代理)")
        except Exception as e:
            logger.error(f"设置默认线路失败: {e}")

    def cleanup_old_keys(self):
        """
        清理 Redis 中不存在于数据库的旧键
        避免 Redis 中残留已删除用户的线路绑定
        """
        try:
            deleted_count = 0

            # 清理 Emby 过期键
            self.cursor.execute("SELECT emby_id FROM emby_user WHERE emby_line IS NOT NULL")
            valid_emby_ids = set(str(row[0]) for row in self.cursor.fetchall())

            redis_keys = self.redis_client.keys("emby_line:*")
            for key in redis_keys:
                emby_id = key.replace("emby_line:", "")
                if emby_id not in valid_emby_ids:
                    self.redis_client.delete(key)
                    logger.debug(f"删除过期键: {key}")
                    deleted_count += 1

            # 清理 Plex 过期键 (plex_email:<username> 格式)
            self.cursor.execute("SELECT plex_username FROM user WHERE plex_line IS NOT NULL AND plex_line != ''")
            valid_plex_usernames = set(row[0] for row in self.cursor.fetchall())

            plex_keys = self.redis_client.keys("plex_email:*")
            for key in plex_keys:
                username = key.replace("plex_email:", "")
                if username not in valid_plex_usernames:
                    self.redis_client.delete(key)
                    logger.debug(f"删除过期键: {key}")
                    deleted_count += 1

            # 清理旧格式的 plex_line:* 键 (已废弃)
            old_plex_keys = self.redis_client.keys("plex_line:*")
            for key in old_plex_keys:
                self.redis_client.delete(key)
                logger.debug(f"删除旧格式键: {key}")
                deleted_count += 1

            if deleted_count > 0:
                logger.info(f"清理过期键完成: {deleted_count} 个")

        except Exception as e:
            logger.error(f"清理过期键失败: {e}")

    def get_stats(self) -> dict:
        """获取 Redis 同步统计信息"""
        try:
            emby_count = len(self.redis_client.keys("emby_line:*"))
            # Plex 使用 plex_email:<username> 格式
            plex_count = len(self.redis_client.keys("plex_email:*"))

            return {
                "emby_users": emby_count,
                "plex_users": plex_count,
                "total": emby_count + plex_count,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

    def run_sync(self):
        """执行完整同步流程"""
        logger.info("=" * 60)
        logger.info("开始同步用户线路到 Redis")
        logger.info("=" * 60)

        try:
            # 设置默认线路
            self.set_default_line()

            # 同步 Emby 用户
            emby_count = self.sync_emby_lines()

            # 同步 Plex 用户
            plex_count = self.sync_plex_lines()

            # 清理过期键
            self.cleanup_old_keys()

            # 输出统计信息
            stats = self.get_stats()
            logger.info("=" * 60)
            logger.info("同步完成统计:")
            logger.info(f"  Emby 用户: {stats.get('emby_users', 0)}")
            logger.info(f"  Plex 用户: {stats.get('plex_users', 0)}")
            logger.info(f"  总计: {stats.get('total', 0)}")
            logger.info(f"  时间: {stats.get('timestamp', 'N/A')}")
            logger.info("=" * 60)

            return True

        except Exception as e:
            logger.error(f"同步流程失败: {e}")
            return False
        finally:
            # 关闭连接
            self.conn.close()

    def __del__(self):
        """清理资源"""
        if hasattr(self, 'conn'):
            self.conn.close()


def main():
    """主函数"""
    try:
        syncer = RedisLineSync()
        success = syncer.run_sync()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"脚本执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
