#!/usr/bin/env python3
"""
Plex Token 同步脚本
从 Plex 服务器获取所有用户的 authToken，并同步到 Redis
用于 Nginx Lua 脚本的 token -> username 映射
"""

import sys
import requests
from pathlib import Path
from datetime import datetime

import redis

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from app.config import settings
from app.log import logger


class PlexTokenSync:
    """Plex Token 同步器"""

    # 本地 Redis 配置
    LOCAL_REDIS_HOST = "127.0.0.1"
    LOCAL_REDIS_PORT = 6379

    def __init__(self):
        """初始化"""
        # Plex 服务器配置
        self.plex_url = settings.PLEX_BASE_URL.rstrip("/")
        self.admin_token = settings.PLEX_API_TOKEN

        # 连接 Redis
        try:
            self.redis_client = redis.Redis(
                host=self.LOCAL_REDIS_HOST,
                port=self.LOCAL_REDIS_PORT,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,
            )
            self.redis_client.ping()
            logger.info(f"Redis 连接成功: {self.LOCAL_REDIS_HOST}:{self.LOCAL_REDIS_PORT}")
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            raise

    def get_all_accounts(self) -> list:
        """
        获取所有 Plex 账户列表

        Returns:
            账户列表 [{id, name}, ...]
        """
        try:
            response = requests.get(
                f"{self.plex_url}/accounts",
                headers={
                    "X-Plex-Token": self.admin_token,
                    "Accept": "application/json",
                },
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()
            accounts = data.get("MediaContainer", {}).get("Account", [])

            logger.info(f"获取到 {len(accounts)} 个 Plex 账户")
            return accounts

        except Exception as e:
            logger.error(f"获取账户列表失败: {e}")
            return []

    def get_account_token(self, account_id: int) -> str | None:
        """
        获取指定账户的 authToken

        Args:
            account_id: 账户 ID

        Returns:
            authToken 或 None
        """
        try:
            response = requests.get(
                f"{self.plex_url}/accounts/{account_id}",
                headers={
                    "X-Plex-Token": self.admin_token,
                    "Accept": "application/json",
                },
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()
            accounts = data.get("MediaContainer", {}).get("Account", [])

            if accounts and len(accounts) > 0:
                return accounts[0].get("authToken")

            return None

        except Exception as e:
            logger.debug(f"获取账户 {account_id} 的 token 失败: {e}")
            return None

    def sync_tokens(self) -> int:
        """
        同步所有用户的 token 到 Redis

        Returns:
            同步的用户数量
        """
        accounts = self.get_all_accounts()

        if not accounts:
            logger.warning("没有获取到任何账户")
            return 0

        synced_count = 0
        skipped_count = 0

        for account in accounts:
            account_id = account.get("id")
            account_name = account.get("name")

            if not account_id or not account_name:
                continue

            # 获取用户的 authToken
            auth_token = self.get_account_token(account_id)

            if auth_token:
                # 写入 Redis: plex_token:<token> -> <username>
                redis_key = f"plex_token:{auth_token}"
                self.redis_client.set(redis_key, account_name)

                logger.debug(f"同步 token: {account_name} -> {auth_token[:10]}...")
                synced_count += 1
            else:
                logger.debug(f"跳过账户 {account_name} (ID: {account_id}): 无法获取 token")
                skipped_count += 1

        logger.info(f"Token 同步完成: 成功 {synced_count} 个, 跳过 {skipped_count} 个")
        return synced_count

    def cleanup_old_tokens(self):
        """
        清理 Redis 中过期的 token 键
        (可选：删除不再有效的 token)
        """
        try:
            # 获取当前所有有效的 token
            accounts = self.get_all_accounts()
            valid_tokens = set()

            for account in accounts:
                account_id = account.get("id")
                if account_id:
                    token = self.get_account_token(account_id)
                    if token:
                        valid_tokens.add(token)

            # 获取 Redis 中所有 plex_token:* 键
            redis_keys = self.redis_client.keys("plex_token:*")
            deleted_count = 0

            for key in redis_keys:
                token = key.replace("plex_token:", "")
                if token not in valid_tokens:
                    self.redis_client.delete(key)
                    logger.debug(f"删除过期 token 键: {key}")
                    deleted_count += 1

            if deleted_count > 0:
                logger.info(f"清理过期 token 键: {deleted_count} 个")

        except Exception as e:
            logger.error(f"清理过期 token 失败: {e}")

    def get_stats(self) -> dict:
        """获取 Redis 中的 token 统计信息"""
        try:
            token_keys = self.redis_client.keys("plex_token:*")
            line_keys = self.redis_client.keys("plex_email:*")

            return {
                "token_count": len(token_keys),
                "line_count": len(line_keys),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

    def run_sync(self):
        """执行完整同步流程"""
        logger.info("=" * 60)
        logger.info("开始同步 Plex Token 到 Redis")
        logger.info("=" * 60)

        try:
            # 同步 token
            synced_count = self.sync_tokens()

            # 输出统计信息
            stats = self.get_stats()
            logger.info("=" * 60)
            logger.info("同步完成统计:")
            logger.info(f"  Token 映射: {stats.get('token_count', 0)}")
            logger.info(f"  线路绑定: {stats.get('line_count', 0)}")
            logger.info(f"  时间: {stats.get('timestamp', 'N/A')}")
            logger.info("=" * 60)

            return True

        except Exception as e:
            logger.error(f"同步流程失败: {e}")
            return False


def main():
    """主函数"""
    try:
        syncer = PlexTokenSync()
        success = syncer.run_sync()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"脚本执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
