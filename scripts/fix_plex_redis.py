#!/usr/bin/env python3
"""
修复 Plex 线路同步问题
从数据库读取所有用户的线路绑定，强制同步到 Redis
"""

import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import redis
from app.line_mapping import LineMapping
from app.log import logger
from app.config import settings


def fix_plex_redis_sync():
    """修复 Plex Redis 同步"""

    # 连接数据库
    db_path = Path(__file__).parents[1] / "data" / "data.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 获取所有 Plex 用户的线路绑定
    cursor.execute("""
        SELECT plex_username, plex_line
        FROM user
        WHERE plex_username IS NOT NULL
        AND plex_username != ''
    """)

    users = cursor.fetchall()
    conn.close()

    # 连接 Redis (直接连接本地 Redis)
    redis_client = redis.Redis(
        host="127.0.0.1",
        port=6379,
        password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
        decode_responses=True,
    )

    logger.info("=" * 60)
    logger.info(f"开始修复 Plex Redis 同步，共 {len(users)} 个用户")
    logger.info("=" * 60)

    updated_count = 0

    for username, line in users:
        redis_key = f"plex_email:{username}"

        if line and line != "":
            # 有绑定线路
            vps_address = LineMapping.get_vps_address(line)

            if vps_address:
                # 检查当前 Redis 值
                current_value = redis_client.get(redis_key)

                if current_value != vps_address:
                    # 需要更新
                    redis_client.set(redis_key, vps_address)
                    logger.info(f"✓ 更新: {username} -> {line} ({vps_address})")
                    logger.info(f"  旧值: {current_value or 'None'}")
                    updated_count += 1
                else:
                    logger.debug(f"✓ 正确: {username} -> {line} ({vps_address})")
            else:
                # 默认线路，删除 Redis 键
                if redis_client.exists(redis_key):
                    redis_client.delete(redis_key)
                    logger.info(f"✓ 删除: {username} (默认线路)")
                    updated_count += 1
        else:
            # 没有绑定线路，删除 Redis 键
            if redis_client.exists(redis_key):
                redis_client.delete(redis_key)
                logger.info(f"✓ 删除: {username} (未绑定)")
                updated_count += 1

    logger.info("=" * 60)
    logger.info(f"修复完成: 更新了 {updated_count} 个用户的 Redis 数据")
    logger.info("=" * 60)

    # 验证关键用户
    logger.info("\n验证关键用户:")
    test_users = ["ECbot", "ranzhideya"]
    for username in test_users:
        cursor = conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT plex_line FROM user WHERE plex_username=?", (username,))
        result = cursor.fetchone()
        conn.close()

        if result:
            db_line = result[0]
            redis_value = redis_client.get(f"plex_email:{username}")
            logger.info(f"  {username}:")
            logger.info(f"    数据库: {db_line}")
            logger.info(f"    Redis: {redis_value}")


if __name__ == "__main__":
    try:
        fix_plex_redis_sync()
    except Exception as e:
        logger.error(f"修复失败: {e}")
        sys.exit(1)
