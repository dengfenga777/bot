#!/usr/bin/env python3
"""数据库基础模块 - 连接管理和表创建"""

import sqlite3
import threading
from pathlib import Path
from typing import Optional, Union

from app.config import settings
from app.log import logger


class DBBase:
    """数据库基础类 - 线程安全的连接管理"""

    _local: threading.local = threading.local()
    db_path: Path

    def __init__(self, db: Union[Path, str] = settings.DATA_PATH / "data.db") -> None:
        self.db_path = Path(db) if isinstance(db, str) else db
        self._ensure_connection()
        self.create_table()
        # executescript() 会关闭连接，需要重新确保连接可用
        self._ensure_connection()

    def _ensure_connection(self) -> None:
        """Ensure thread-local connection exists and is open"""
        needs_new_connection = (
            not hasattr(self._local, 'con') or
            self._local.con is None
        )

        if not needs_new_connection:
            try:
                self._local.con.execute("SELECT 1")
            except (sqlite3.ProgrammingError, sqlite3.OperationalError, sqlite3.DatabaseError) as e:
                logger.warning(f"数据库连接检查失败，将重新连接: {e}")
                needs_new_connection = True
                try:
                    self._local.con.close()
                except Exception:
                    pass
                self._local.con = None

        if needs_new_connection:
            try:
                self._local.con = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=30.0
                )
                self._local.con.row_factory = sqlite3.Row
                self._local.con.execute("PRAGMA journal_mode=WAL")
                self._local.con.execute("PRAGMA busy_timeout=30000")
                logger.debug(f"数据库连接已建立: {self.db_path}")
            except sqlite3.Error as e:
                logger.error(f"无法建立数据库连接: {e}")
                raise

    def _get_cursor(self) -> sqlite3.Cursor:
        """Get a fresh cursor for the current thread"""
        self._ensure_connection()
        return self._local.con.cursor()

    @property
    def con(self) -> sqlite3.Connection:
        """Get thread-local connection"""
        self._ensure_connection()
        return self._local.con

    @property
    def cur(self) -> sqlite3.Cursor:
        """Get a fresh cursor for operations"""
        return self._get_cursor()

    def close(self) -> None:
        """关闭数据库连接"""
        if hasattr(self._local, 'con') and self._local.con:
            try:
                self._local.con.close()
                logger.debug("数据库连接已关闭")
            except Exception as e:
                logger.error(f"关闭数据库连接时出错: {e}")
            finally:
                self._local.con = None

    def health_check(self) -> bool:
        """检查数据库连接是否健康"""
        try:
            self._ensure_connection()
            self._local.con.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return False

    def get_db_info(self) -> Optional[dict]:
        """获取数据库信息"""
        try:
            self._ensure_connection()
            cursor = self.cur
            
            # 获取数据库大小
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
            
            # 获取表数量
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            # 获取WAL模式状态
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            
            return {
                "path": str(self.db_path),
                "size_bytes": db_size,
                "size_mb": round(db_size / (1024 * 1024), 2),
                "table_count": table_count,
                "journal_mode": journal_mode,
                "healthy": True
            }
        except Exception as e:
            logger.error(f"获取数据库信息失败: {e}")
            return {"healthy": False, "error": str(e)}

    def create_table(self) -> None:
        """创建所有数据库表"""
        self.cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS user(
                plex_id,
                tg_id,
                credits,
                plex_email,
                plex_username,
                all_lib,
                unlock_time,
                watched_time,
                plex_line,
                is_premium,
                premium_expiry_time
            );

            CREATE TABLE IF NOT EXISTS invitation(
                code TEXT PRIMARY KEY,
                owner,
                is_used INTEGER DEFAULT 0,
                used_by,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                expires_at INTEGER DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS statistics(
                tg_id, donation, credits
            );

            CREATE TABLE IF NOT EXISTS emby_user(
                emby_username, emby_id, tg_id, emby_is_unlock, emby_unlock_time, emby_watched_time, emby_credits, emby_line, is_premium, premium_expiry_time
            );

            CREATE TABLE IF NOT EXISTS overseerr(
                user_id, user_email, tg_id
            );

            CREATE TABLE IF NOT EXISTS wheel_stats(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER,
                item_name TEXT,
                credits_change REAL,
                timestamp INTEGER,
                date TEXT
            );

            CREATE TABLE IF NOT EXISTS auctions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                starting_price REAL NOT NULL,
                current_price REAL NOT NULL,
                end_time INTEGER NOT NULL,
                created_by INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1,
                winner_id INTEGER DEFAULT NULL,
                bid_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS auction_bids(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                auction_id INTEGER NOT NULL,
                bidder_id INTEGER NOT NULL,
                bid_amount REAL NOT NULL,
                bid_time INTEGER NOT NULL,
                FOREIGN KEY (auction_id) REFERENCES auctions (id)
            );

            CREATE TABLE IF NOT EXISTS blackjack_stats(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL,
                bet_amount REAL NOT NULL,
                result TEXT NOT NULL,
                credits_change REAL NOT NULL,
                player_score INTEGER NOT NULL,
                dealer_score INTEGER NOT NULL,
                timestamp INTEGER NOT NULL,
                date TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS line_traffic_stats(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                line TEXT NOT NULL,
                send_bytes INTEGER NOT NULL,
                service TEXT NOT NULL,
                username TEXT NOT NULL,
                user_id TEXT DEFAULT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS line_traffic_monthly_stats(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                line TEXT NOT NULL,
                service TEXT NOT NULL,
                username TEXT NOT NULL,
                user_id TEXT DEFAULT NULL,
                year_month TEXT NOT NULL,
                total_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(line, service, username, year_month)
            );

            CREATE TABLE IF NOT EXISTS group_member_left_status(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL,
                left_time INTEGER NOT NULL,
                group_id INTEGER,
                is_processed INTEGER DEFAULT 0,
                warning_sent INTEGER DEFAULT 0,
                last_warning_time INTEGER DEFAULT 0,
                UNIQUE(tg_id)
            );

            CREATE INDEX IF NOT EXISTS idx_line_traffic_timestamp ON line_traffic_stats(timestamp);
            CREATE INDEX IF NOT EXISTS idx_line_traffic_service_user_time ON line_traffic_stats(service, username, timestamp);
            CREATE INDEX IF NOT EXISTS idx_line_traffic_line_time ON line_traffic_stats(line, timestamp);
            CREATE INDEX IF NOT EXISTS idx_line_traffic_daily_query ON line_traffic_stats(service, username, date(timestamp));
            CREATE INDEX IF NOT EXISTS idx_line_traffic_line_stats ON line_traffic_stats(line, timestamp, send_bytes);
            CREATE INDEX IF NOT EXISTS idx_line_traffic_month ON line_traffic_stats(date(timestamp, 'start of month'));
            CREATE INDEX IF NOT EXISTS idx_monthly_traffic_service_user_month ON line_traffic_monthly_stats(service, username, year_month);
            CREATE INDEX IF NOT EXISTS idx_monthly_traffic_line_month ON line_traffic_monthly_stats(line, year_month);
            CREATE INDEX IF NOT EXISTS idx_monthly_traffic_month ON line_traffic_monthly_stats(year_month);
            CREATE INDEX IF NOT EXISTS idx_monthly_traffic_line_stats ON line_traffic_monthly_stats(line, year_month, total_bytes);

            CREATE TABLE IF NOT EXISTS checkin_stats(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL,
                checkin_date TEXT NOT NULL,
                streak INTEGER NOT NULL DEFAULT 1,
                month TEXT NOT NULL,
                credits_earned REAL NOT NULL DEFAULT 0,
                UNIQUE(tg_id, checkin_date)
            );

            CREATE INDEX IF NOT EXISTS idx_checkin_tg_month ON checkin_stats(tg_id, month);
            CREATE INDEX IF NOT EXISTS idx_checkin_date ON checkin_stats(checkin_date);
            """
        )
        for sql in [
            "ALTER TABLE invitation ADD COLUMN created_at INTEGER DEFAULT NULL",
            "ALTER TABLE invitation ADD COLUMN expires_at INTEGER DEFAULT NULL",
        ]:
            try:
                self.cur.execute(sql)
            except Exception:
                pass
        self.cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_invitation_owner_status ON invitation(owner, is_used, expires_at)"
        )
        self.cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_invitation_expires_at ON invitation(expires_at)"
        )
        self.con.commit()
        self._migrate_tables()

    def _migrate_tables(self) -> None:
        """对现有表进行迁移，添加新字段（幂等操作）"""
        migrations = [
            "ALTER TABLE statistics ADD COLUMN debt_since INTEGER DEFAULT NULL",
        ]
        for sql in migrations:
            try:
                self.cur.execute(sql)
            except Exception:
                pass
        self.con.commit()
