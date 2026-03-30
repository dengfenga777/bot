#!/usr/bin/env python3
"""
从 Emby 访问日志中学习用户 token
通过分析 Nginx 日志，提取用户 token 并映射到 user_id
"""

import re
import sys
import sqlite3
import requests
from pathlib import Path
from collections import defaultdict

import redis

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from app.config import settings
from app.log import logger


class EmbyTokenLearner:
    """Emby Token 学习器"""

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

        # 日志文件路径
        self.log_file = Path("/var/log/nginx/emby_access.log")

    def extract_tokens_from_log(self, lines_to_read: int = 10000) -> dict:
        """
        从访问日志中提取 token

        Args:
            lines_to_read: 读取的行数

        Returns:
            {token: count} - token 出现的次数
        """
        token_counts = defaultdict(int)

        try:
            # 读取日志文件的最后 N 行
            with open(self.log_file, "r") as f:
                # 读取所有行并取最后 N 行
                lines = f.readlines()[-lines_to_read:]

            # 正则匹配 token
            # 匹配 URL 参数: ?api_key=xxx 或 &api_key=xxx
            # 匹配 Header: X-Emby-Token: xxx
            token_pattern = re.compile(r'[?&]api_key=([a-f0-9]+)|X-Emby-Token[=:\s]+([a-f0-9]+)')

            for line in lines:
                matches = token_pattern.findall(line)
                for match in matches:
                    # match 是 tuple，取非空的那个
                    token = match[0] or match[1]
                    if token and len(token) == 32:  # Emby token 通常是 32 位
                        token_counts[token] += 1

            logger.info(f"从日志中发现 {len(token_counts)} 个不同的 token")

            # 输出前 5 个最常见的 token（调试用）
            if token_counts:
                sorted_tokens = sorted(token_counts.items(), key=lambda x: x[1], reverse=True)
                logger.info("最常见的 token:")
                for token, count in sorted_tokens[:5]:
                    logger.info(f"  {token[:10]}... (出现 {count} 次, 长度 {len(token)})")

            return dict(token_counts)

        except Exception as e:
            logger.error(f"读取日志文件失败: {e}")
            return {}

    def get_user_from_token(self, token: str) -> str | None:
        """
        通过 Emby API 获取 token 对应的用户 ID

        Args:
            token: Emby token

        Returns:
            用户 ID 或 None
        """
        try:
            # 使用 token 调用 Emby API 获取当前用户信息
            response = requests.get(
                f"{self.emby_url}/Users/Me",
                headers={
                    "X-Emby-Token": token,
                },
                timeout=5,
            )

            if response.status_code == 200:
                user_info = response.json()
                user_id = user_info.get("Id")
                username = user_info.get("Name")
                logger.info(f"Token 映射: {token[:10]}... -> {username} ({user_id})")
                return user_id

            else:
                logger.warning(f"Token 验证失败 [{response.status_code}]: {token[:10]}... - {response.text[:100]}")
                return None

        except Exception as e:
            logger.error(f"验证 token 异常: {token[:10]}... - {e}")
            return None

    def learn_tokens(self, lines_to_read: int = 10000) -> int:
        """
        学习 token 映射并写入 Redis

        Args:
            lines_to_read: 从日志中读取的行数

        Returns:
            成功学习的 token 数量
        """
        # 1. 从日志提取 token
        token_counts = self.extract_tokens_from_log(lines_to_read)

        if not token_counts:
            logger.warning("没有发现任何 token")
            return 0

        # 2. 验证并存储 token
        learned_count = 0
        skipped_count = 0

        # 按出现频率排序（频率高的优先）
        sorted_tokens = sorted(token_counts.items(), key=lambda x: x[1], reverse=True)

        for token, count in sorted_tokens:
            # 检查是否已经学习过
            existing = self.redis_client.get(f"emby_token:{token}")
            if existing:
                logger.debug(f"Token 已存在: {token[:10]}... -> {existing}")
                continue

            # 验证 token 并获取 user_id
            user_id = self.get_user_from_token(token)

            if user_id:
                # 写入 Redis
                self.redis_client.set(f"emby_token:{token}", user_id)
                logger.info(f"学习成功: {token[:10]}... -> {user_id} (出现 {count} 次)")
                learned_count += 1
            else:
                skipped_count += 1

        logger.info(f"Token 学习完成: 成功 {learned_count} 个, 跳过 {skipped_count} 个")
        return learned_count

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

    def run_learning(self, lines_to_read: int = 10000):
        """执行学习流程"""
        logger.info("=" * 60)
        logger.info("开始学习 Emby Token 映射")
        logger.info("=" * 60)

        try:
            # 学习 token
            learned_count = self.learn_tokens(lines_to_read)

            # 输出统计信息
            stats = self.get_stats()
            logger.info("=" * 60)
            logger.info("学习完成统计:")
            logger.info(f"  用户映射: {stats.get('user_count', 0)}")
            logger.info(f"  线路绑定: {stats.get('line_count', 0)}")
            logger.info(f"  Token 映射: {stats.get('token_count', 0)} (新增 {learned_count})")
            logger.info("=" * 60)

            return True

        except Exception as e:
            logger.error(f"学习流程失败: {e}")
            return False


def main():
    """主函数"""
    try:
        # 从命令行参数获取要读取的行数（默认 10000）
        lines_to_read = int(sys.argv[1]) if len(sys.argv) > 1 else 10000

        learner = EmbyTokenLearner()
        success = learner.run_learning(lines_to_read)
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"脚本执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
