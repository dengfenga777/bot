#!/usr/bin/env python3
"""
Plex 用户同步到 Redis
从数据库读取 Plex 用户名，通过 Plex API 获取对应的 userId，
然后为每个用户生成访问 token 并同步到 Redis
"""

import sys
import sqlite3
from pathlib import Path
from plexapi.server import PlexServer

import redis

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from app.config import settings
from app.log import logger


class PlexUserTokenSync:
    """Plex 用户 Token 同步器"""

    def __init__(self):
        """初始化"""
        # Plex 服务器
        self.plex = PlexServer(settings.PLEX_BASE_URL, settings.PLEX_API_TOKEN)

        # Redis
        self.redis_client = redis.Redis(
            host="127.0.0.1",
            port=6379,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=True,
        )

        # 数据库
        self.db_path = settings.DATA_PATH / "data.db"

    def get_users_from_db(self) -> list:
        """
        从数据库获取所有 Plex 用户

        Returns:
            [(plex_username, plex_email), ...]
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT plex_username, plex_email
                FROM user
                WHERE plex_username IS NOT NULL
                AND plex_username != ''
            """)

            users = cursor.fetchall()
            conn.close()

            logger.info(f"从数据库获取到 {len(users)} 个 Plex 用户")
            return users

        except Exception as e:
            logger.error(f"读取数据库失败: {e}")
            return []

    def get_user_token(self, username: str) -> str | None:
        """
        通过 PlexAPI 获取用户的访问 token

        Args:
            username: Plex 用户名

        Returns:
            用户的 authToken 或 None
        """
        try:
            # 方法1: 检查是否是服务器所有者
            owner_username = self.plex.myPlexUsername
            if username == owner_username:
                # 服务器所有者使用管理员 token
                logger.info(f"用户 {username} 是服务器所有者，使用管理员 token")
                return settings.PLEX_API_TOKEN

            # 方法2: 通过 myPlexAccount 获取共享用户
            account = self.plex.myPlexAccount()

            for user in account.users():
                if user.username == username:
                    # 获取该用户的 token
                    # PlexAPI 的 user 对象有 get_token() 方法
                    if hasattr(user, 'get_token'):
                        token = user.get_token(self.plex.machineIdentifier)
                        return token

            # 方法3: 尝试通过服务器的 systemAccounts 获取
            try:
                for account in self.plex.systemAccounts():
                    if account.name == username:
                        logger.info(f"从 systemAccounts 找到用户: {username}")
                        # systemAccount 可能有 authToken 或 key 属性
                        if hasattr(account, 'authToken') and account.authToken:
                            return account.authToken
                        if hasattr(account, 'key') and account.key:
                            # 尝试使用账户 key 作为标识
                            # 对于本地账户，可以生成一个临时 token
                            # 或者使用管理员 token 代替
                            logger.info(f"本地账户 {username} 使用管理员 token 代替")
                            return settings.PLEX_API_TOKEN
            except Exception as e:
                logger.debug(f"systemAccounts 查询失败: {e}")
                pass

            logger.warning(f"未找到用户: {username}")
            return None

        except Exception as e:
            logger.error(f"获取用户 {username} 的 token 失败: {e}")
            return None

    def sync_to_redis(self) -> int:
        """
        同步所有用户的 token 到 Redis

        Returns:
            同步成功的用户数量
        """
        users = self.get_users_from_db()

        if not users:
            logger.warning("没有用户需要同步")
            return 0

        synced_count = 0
        skipped_count = 0

        for plex_username, plex_email in users:
            if not plex_username:
                continue

            # 获取用户 token
            token = self.get_user_token(plex_username)

            if token:
                # 写入 Redis: plex_token:<token> -> <username>
                redis_key = f"plex_token:{token}"
                self.redis_client.set(redis_key, plex_username)

                logger.info(f"同步 token: {plex_username} -> {token[:10]}...")
                synced_count += 1
            else:
                logger.warning(f"跳过用户 {plex_username}: 无法获取 token")
                skipped_count += 1

        logger.info(f"Token 同步完成: 成功 {synced_count} 个, 跳过 {skipped_count} 个")
        return synced_count

    def get_stats(self) -> dict:
        """获取 Redis 统计信息"""
        try:
            token_keys = self.redis_client.keys("plex_token:*")
            line_keys = self.redis_client.keys("plex_email:*")

            return {
                "token_count": len(token_keys),
                "line_count": len(line_keys),
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

    def run_sync(self):
        """执行完整同步流程"""
        logger.info("=" * 60)
        logger.info("开始同步 Plex 用户 Token 到 Redis")
        logger.info("=" * 60)

        try:
            # 同步 token
            synced_count = self.sync_to_redis()

            # 输出统计信息
            stats = self.get_stats()
            logger.info("=" * 60)
            logger.info("同步完成统计:")
            logger.info(f"  Token 映射: {stats.get('token_count', 0)}")
            logger.info(f"  线路绑定: {stats.get('line_count', 0)}")
            logger.info("=" * 60)

            return True

        except Exception as e:
            logger.error(f"同步流程失败: {e}")
            return False


def main():
    """主函数"""
    try:
        syncer = PlexUserTokenSync()
        success = syncer.run_sync()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"脚本执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
