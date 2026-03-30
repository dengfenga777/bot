#!/usr/bin/env python3
"""
线路域名迁移脚本
将数据库中旧格式的线路域名更新为新格式

旧格式: 3286hk.misaya.org, 6798sg.misaya.org, 4512us.misaya.org
新格式: hk.stream.misaya.org, sg.stream.misaya.org, us.stream.misaya.org, jp.stream.misaya.org
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from app.config import settings
from app.log import logger


# 线路名称映射: 旧格式 -> 新格式
LINE_NAME_MIGRATION = {
    # 香港线路
    "3286hk.misaya.org": "hk.stream.misaya.org",

    # 新加坡线路
    "6798sg.misaya.org": "sg.stream.misaya.org",

    # 美国线路
    "4512us.misaya.org": "us.stream.misaya.org",
}


def migrate_emby_lines(cursor) -> int:
    """迁移 Emby 用户线路"""
    migrated = 0

    for old_name, new_name in LINE_NAME_MIGRATION.items():
        cursor.execute(
            "UPDATE emby_user SET emby_line = ? WHERE emby_line = ?",
            (new_name, old_name)
        )
        count = cursor.rowcount
        if count > 0:
            logger.info(f"Emby: {old_name} -> {new_name}: {count} 个用户")
            migrated += count

    return migrated


def migrate_plex_lines(cursor) -> int:
    """迁移 Plex 用户线路"""
    migrated = 0

    for old_name, new_name in LINE_NAME_MIGRATION.items():
        cursor.execute(
            "UPDATE user SET plex_line = ? WHERE plex_line = ?",
            (new_name, old_name)
        )
        count = cursor.rowcount
        if count > 0:
            logger.info(f"Plex: {old_name} -> {new_name}: {count} 个用户")
            migrated += count

    return migrated


def migrate_line_switch_history(cursor) -> int:
    """迁移线路切换历史记录"""
    migrated = 0

    for old_name, new_name in LINE_NAME_MIGRATION.items():
        # 更新 old_line 字段
        cursor.execute(
            "UPDATE line_switch_history SET old_line = ? WHERE old_line = ?",
            (new_name, old_name)
        )
        migrated += cursor.rowcount

        # 更新 new_line 字段
        cursor.execute(
            "UPDATE line_switch_history SET new_line = ? WHERE new_line = ?",
            (new_name, old_name)
        )
        migrated += cursor.rowcount

    return migrated


def show_current_lines(cursor):
    """显示当前数据库中的线路分布"""
    logger.info("=" * 60)
    logger.info("当前数据库线路分布:")
    logger.info("=" * 60)

    # Emby 线路
    cursor.execute("""
        SELECT emby_line, COUNT(*) as count
        FROM emby_user
        WHERE emby_line IS NOT NULL AND emby_line != ''
        GROUP BY emby_line
    """)
    emby_lines = cursor.fetchall()

    logger.info("Emby 用户线路:")
    for line, count in emby_lines:
        logger.info(f"  {line}: {count} 个用户")

    # Plex 线路
    cursor.execute("""
        SELECT plex_line, COUNT(*) as count
        FROM user
        WHERE plex_line IS NOT NULL AND plex_line != ''
        GROUP BY plex_line
    """)
    plex_lines = cursor.fetchall()

    logger.info("Plex 用户线路:")
    for line, count in plex_lines:
        logger.info(f"  {line}: {count} 个用户")

    logger.info("=" * 60)


def main():
    """主函数"""
    db_path = settings.DATA_PATH / "data.db"

    if not db_path.exists():
        logger.error(f"数据库文件不存在: {db_path}")
        sys.exit(1)

    # 备份数据库
    backup_path = db_path.parent / f"data.db.bak-migrate-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    logger.info("=" * 60)
    logger.info("线路域名迁移脚本")
    logger.info("=" * 60)
    logger.info(f"数据库路径: {db_path}")
    logger.info(f"备份路径: {backup_path}")
    logger.info("")
    logger.info("迁移规则:")
    for old_name, new_name in LINE_NAME_MIGRATION.items():
        logger.info(f"  {old_name} -> {new_name}")
    logger.info("=" * 60)

    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 显示迁移前的状态
        show_current_lines(cursor)

        # 创建备份
        logger.info(f"创建数据库备份: {backup_path}")
        import shutil
        shutil.copy2(db_path, backup_path)

        # 执行迁移
        logger.info("")
        logger.info("开始迁移...")
        logger.info("-" * 60)

        emby_migrated = migrate_emby_lines(cursor)
        plex_migrated = migrate_plex_lines(cursor)
        history_migrated = migrate_line_switch_history(cursor)

        # 提交事务
        conn.commit()

        logger.info("-" * 60)
        logger.info("迁移完成统计:")
        logger.info(f"  Emby 用户: {emby_migrated} 条记录")
        logger.info(f"  Plex 用户: {plex_migrated} 条记录")
        logger.info(f"  切换历史: {history_migrated} 条记录")
        logger.info(f"  总计: {emby_migrated + plex_migrated + history_migrated} 条记录")
        logger.info("")

        # 显示迁移后的状态
        show_current_lines(cursor)

        conn.close()

        logger.info("✅ 迁移成功完成！")
        logger.info("")
        logger.info("下一步: 运行 Redis 同步脚本")
        logger.info("  python3 scripts/sync_lines_to_redis.py")

        return 0

    except Exception as e:
        logger.error(f"迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
