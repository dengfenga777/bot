#!/usr/bin/env python3
"""
Emby 用户同步到 Redis
从数据库读取 Emby 用户，通过 Emby API 获取用户的访问 token 并同步到 Redis
"""

import sys
import sqlite3
import requests
from pathlib import Path

import redis

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from app.config import settings
from app.log import logger


class EmbyUserTokenSync:
    """Emby 用户 Token 同步器"""

    def __init__(self):
        """初始化"""
        # Emby 服务器配置
        self.emby_url = settings.EMBY_BASE_URL.rstrip("/")
        self.admin_token = settings.EMBY_API_TOKEN

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
        从数据库获取所有 Emby 用户

        Returns:
            [(emby_id, emby_username), ...]
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT emby_id, emby_username
                FROM emby_user
                WHERE emby_id IS NOT NULL
                AND emby_id != ''
            """)

            users = cursor.fetchall()
            conn.close()

            logger.info(f"从数据库获取到 {len(users)} 个 Emby 用户")
            return users

        except Exception as e:
            logger.error(f"读取数据库失败: {e}")
            return []

    def get_user_access_tokens(self, user_id: str) -> list:
        """
        通过 Emby API 获取用户的访问令牌

        Args:
            user_id: Emby 用户 ID

        Returns:
            用户的 access token 列表
        """
        try:
            # 获取用户的所有访问令牌
            response = requests.get(
                f"{self.emby_url}/Auth/Keys",
                headers={
                    "X-Emby-Token": self.admin_token,
                },
                params={
                    "userId": user_id,
                },
                timeout=10,
            )

            if response.status_code == 200:
                items = response.json().get("Items", [])
                tokens = []
                for item in items:
                    token = item.get("AccessToken")
                    app_name = item.get("AppName", "Unknown")
                    if token:
                        tokens.append((token, app_name))
                        logger.info(f"  找到令牌: {app_name} - {token[:10]}...")
                return tokens
            else:
                logger.debug(f"无法获取用户 {user_id} 的令牌: {response.status_code}")
                return []

        except Exception as e:
            logger.debug(f"获取用户 {user_id} 令牌失败: {e}")
            return []

    def get_active_sessions(self) -> dict:
        """
        获取当前活跃会话，从中提取用户 token

        Returns:
            {user_id: token} 映射
        """
        try:
            response = requests.get(
                f"{self.emby_url}/Sessions",
                headers={
                    "X-Emby-Token": self.admin_token,
                },
                timeout=10,
            )

            if response.status_code != 200:
                logger.warning("无法获取活跃会话")
                return {}

            sessions = response.json()
            token_map = {}

            for session in sessions:
                user_id = session.get("UserId")
                # Emby 会话中不直接包含 token
                # Token 通常在请求参数或 Header 中
                # 这里无法直接获取

            logger.info(f"找到 {len(sessions)} 个活跃会话")
            return token_map

        except Exception as e:
            logger.error(f"获取活跃会话失败: {e}")
            return {}

    def sync_user_mappings(self) -> tuple:
        """
        同步用户 ID 映射和访问令牌到 Redis

        Returns:
            (用户数量, token数量)
        """
        users = self.get_users_from_db()

        if not users:
            logger.warning("没有用户需要同步")
            return 0, 0

        user_count = 0
        token_count = 0

        for emby_id, emby_username in users:
            if not emby_id:
                continue

            # 1. 存储用户 ID -> 用户名映射（供日志使用）
            redis_key = f"emby_user:{emby_id}"
            self.redis_client.set(redis_key, emby_username)
            logger.debug(f"同步用户映射: {emby_id} -> {emby_username}")
            user_count += 1

            # 2. 尝试获取用户的访问令牌
            tokens = self.get_user_access_tokens(emby_id)
            for token, app_name in tokens:
                # 存储 token -> user_id 映射
                token_key = f"emby_token:{token}"
                self.redis_client.set(token_key, emby_id)
                logger.info(f"同步令牌: {emby_username} ({app_name}) -> {token[:10]}...")
                token_count += 1

        logger.info(f"用户映射同步完成: {user_count} 个用户, {token_count} 个令牌")
        return user_count, token_count

    def get_stats(self) -> dict:
        """获取 Redis 统计信息"""
        try:
            user_keys = self.redis_client.keys("emby_user:*")
            line_keys = self.redis_client.keys("emby_line:*")
            token_keys = self.redis_client.keys("emby_token:*")

            return {
                "user_count": len(user_keys),
                "line_count": len(line_keys),
                "token_count": len(token_keys),
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

    def run_sync(self):
        """执行完整同步流程"""
        logger.info("=" * 60)
        logger.info("开始同步 Emby 用户到 Redis")
        logger.info("=" * 60)

        try:
            # 同步用户映射和访问令牌
            user_count, token_count = self.sync_user_mappings()

            # 输出统计信息
            stats = self.get_stats()
            logger.info("=" * 60)
            logger.info("同步完成统计:")
            logger.info(f"  用户映射: {stats.get('user_count', 0)}")
            logger.info(f"  线路绑定: {stats.get('line_count', 0)}")
            logger.info(f"  Token 映射: {stats.get('token_count', 0)}")
            logger.info("=" * 60)

            if token_count > 0:
                logger.info(f"成功同步 {token_count} 个用户访问令牌")
            else:
                logger.info("未找到访问令牌，Token 将通过活跃会话自动学习")

            return True

        except Exception as e:
            logger.error(f"同步流程失败: {e}")
            return False


def main():
    """主函数"""
    try:
        syncer = EmbyUserTokenSync()
        success = syncer.run_sync()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"脚本执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
