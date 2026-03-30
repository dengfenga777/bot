#!/usr/bin/env python3

import sqlite3
import threading
import time
import traceback
from datetime import date, datetime, timedelta
from typing import List, Optional

from app.config import settings
from app.invitation_utils import get_invitation_timestamps
from app.log import logger

CHECKIN_TOTAL_RANK_MEDALS = (
    {
        "rank": 1,
        "code": "checkin_top_1_ox",
        "name": "签到总榜牛王勋章",
        "description": "签到总榜第 1 名专属勋章，持有后每日积分结算享受 1.5 倍加成。",
        "multiplier": 1.5,
        "price": 0,
        "icon_url": "/medals/checkin-ox-honor.svg",
        "theme_color": "#F4B942",
        "is_active": 1,
        "is_special": 1,
        "is_shop_visible": 0,
        "display_order": 11,
    },
    {
        "rank": 2,
        "code": "checkin_top_2_ox",
        "name": "签到总榜牛魁勋章",
        "description": "签到总榜第 2 名专属勋章，持有后每日积分结算享受 1.3 倍加成。",
        "multiplier": 1.3,
        "price": 0,
        "icon_url": "/medals/checkin-ox-honor.svg",
        "theme_color": "#C9D4E5",
        "is_active": 1,
        "is_special": 1,
        "is_shop_visible": 0,
        "display_order": 12,
    },
    {
        "rank": 3,
        "code": "checkin_top_3_ox",
        "name": "签到总榜牛锋勋章",
        "description": "签到总榜第 3 名专属勋章，持有后每日积分结算享受 1.1 倍加成。",
        "multiplier": 1.1,
        "price": 0,
        "icon_url": "/medals/checkin-ox-honor.svg",
        "theme_color": "#C77745",
        "is_active": 1,
        "is_special": 1,
        "is_shop_visible": 0,
        "display_order": 13,
    },
)


class DB:
    """class DB with thread-safe connection management"""

    _local = threading.local()

    def __init__(self, db=settings.DATA_PATH / "data.db"):
        self.db_path = db
        self._ensure_connection()
        self.create_table()
        # executescript() 会关闭连接，需要重新确保连接可用
        self._ensure_connection()

    def _ensure_connection(self):
        """Ensure thread-local connection exists and is open"""
        # 检查连接是否存在且未关闭
        needs_new_connection = (
            not hasattr(self._local, 'con') or
            self._local.con is None
        )

        # 如果连接存在，检查是否已关闭
        if not needs_new_connection:
            try:
                # 尝试执行简单查询来验证连接是否可用
                self._local.con.execute("SELECT 1")
            except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                # 连接已关闭，需要重新创建
                needs_new_connection = True
                self._local.con = None

        if needs_new_connection:
            self._local.con = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0  # 30秒超时
            )
            self._local.con.row_factory = sqlite3.Row
            # 启用 WAL 模式提高并发性能
            self._local.con.execute("PRAGMA journal_mode=WAL")
            self._local.con.execute("PRAGMA busy_timeout=30000")  # 30秒忙等待

    def _get_cursor(self):
        """Get a fresh cursor for the current thread"""
        self._ensure_connection()
        return self._local.con.cursor()

    @property
    def con(self):
        """Get thread-local connection"""
        self._ensure_connection()
        return self._local.con

    @property
    def cur(self):
        """Get a fresh cursor for operations"""
        return self._get_cursor()

    def create_table(self):
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

            -- 月度流量聚合表
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

            -- 索引优化：为 line_traffic_stats 表添加关键索引（当月数据）
            CREATE INDEX IF NOT EXISTS idx_line_traffic_timestamp ON line_traffic_stats(timestamp);
            CREATE INDEX IF NOT EXISTS idx_line_traffic_service_timestamp ON line_traffic_stats(service, timestamp);
            CREATE INDEX IF NOT EXISTS idx_line_traffic_service_user_time ON line_traffic_stats(service, username, timestamp);
            CREATE INDEX IF NOT EXISTS idx_line_traffic_line_time ON line_traffic_stats(line, timestamp);
            CREATE INDEX IF NOT EXISTS idx_line_traffic_daily_query ON line_traffic_stats(service, username, date(timestamp));
            CREATE INDEX IF NOT EXISTS idx_line_traffic_line_stats ON line_traffic_stats(line, timestamp, send_bytes);
            -- 添加月份索引，用于快速识别和处理当月数据
            CREATE INDEX IF NOT EXISTS idx_line_traffic_month ON line_traffic_stats(date(timestamp, 'start of month'));

            -- 索引优化：为 line_traffic_monthly_stats 表添加索引（历史月度数据）
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
            CREATE INDEX IF NOT EXISTS idx_invitation_owner_status ON invitation(owner, is_used, expires_at);
            CREATE INDEX IF NOT EXISTS idx_invitation_expires_at ON invitation(expires_at);

            CREATE TABLE IF NOT EXISTS medal_catalog(
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                multiplier REAL NOT NULL DEFAULT 1.1,
                price REAL NOT NULL DEFAULT 0,
                icon_url TEXT,
                theme_color TEXT DEFAULT '#F4B942',
                is_active INTEGER DEFAULT 1,
                is_special INTEGER DEFAULT 0,
                is_shop_visible INTEGER DEFAULT 1,
                display_order INTEGER DEFAULT 0,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            );

            CREATE TABLE IF NOT EXISTS user_medals(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL,
                medal_code TEXT NOT NULL,
                source TEXT DEFAULT 'shop',
                acquired_at INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1,
                UNIQUE(tg_id, medal_code),
                FOREIGN KEY (medal_code) REFERENCES medal_catalog(code)
            );

            CREATE INDEX IF NOT EXISTS idx_user_medals_tg_active
                ON user_medals(tg_id, is_active);
            """
        )
        self.con.commit()
        self._migrate_legacy_tables()
        self._seed_default_medals()

    def _migrate_legacy_tables(self) -> None:
        """幂等迁移：为现有表添加新字段"""
        for sql in [
            "ALTER TABLE statistics ADD COLUMN debt_since INTEGER DEFAULT NULL",
            "ALTER TABLE medal_catalog ADD COLUMN is_shop_visible INTEGER DEFAULT 1",
            "ALTER TABLE invitation ADD COLUMN created_at INTEGER DEFAULT NULL",
            "ALTER TABLE invitation ADD COLUMN expires_at INTEGER DEFAULT NULL",
        ]:
            try:
                self.cur.execute(sql)
            except Exception:
                pass
        self.con.commit()

    def _seed_default_medals(self) -> None:
        """写入默认勋章配置"""
        try:
            medal_rows = [
                (
                    "special_contribution",
                    "特殊贡献勋章",
                    "Misaya 特别贡献纪念勋章，持有后每日积分结算享受 1.5 倍加成。",
                    1.5,
                    1314,
                    "/medals/special-contribution-misaya.svg",
                    "#F4B942",
                    1,
                    1,
                    1,
                    1,
                ),
            ]
            medal_rows.extend(
                (
                    medal["code"],
                    medal["name"],
                    medal["description"],
                    medal["multiplier"],
                    medal["price"],
                    medal["icon_url"],
                    medal["theme_color"],
                    medal["is_active"],
                    medal["is_special"],
                    medal["is_shop_visible"],
                    medal["display_order"],
                )
                for medal in CHECKIN_TOTAL_RANK_MEDALS
            )
            self.cur.executemany(
                """
                INSERT INTO medal_catalog
                    (code, name, description, multiplier, price, icon_url, theme_color, is_active, is_special, is_shop_visible, display_order)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    multiplier = excluded.multiplier,
                    price = excluded.price,
                    icon_url = excluded.icon_url,
                    theme_color = excluded.theme_color,
                    is_active = excluded.is_active,
                    is_special = excluded.is_special,
                    is_shop_visible = excluded.is_shop_visible,
                    display_order = excluded.display_order
                """,
                medal_rows,
            )
            self.con.commit()
        except Exception as e:
            logger.error(f"写入默认勋章配置失败: {e}")

    def add_plex_user(
        self,
        plex_id: Optional[int] = None,
        tg_id: Optional[int] = None,
        plex_email: Optional[str] = None,
        plex_username: Optional[str] = None,
        credits: int = 0,
        all_lib=0,
        unlock_time=None,
        watched_time=0,
        plex_line: Optional[str] = None,
        is_premium: Optional[int] = 0,
        premium_expiry_time: Optional[str] = None,
    ):
        try:
            self.cur.execute(
                "INSERT INTO user VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
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
                    premium_expiry_time,
                ),
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        else:
            self.con.commit()
        return True

    def add_emby_user(
        self,
        emby_username: str,
        emby_id: Optional[str] = None,
        tg_id: Optional[int] = None,
        emby_is_unlock: Optional[int] = 0,
        emby_unlock_time: Optional[int] = None,
        emby_watched_time: float = 0,
        emby_credits: float = 0,
        emby_line: Optional[str] = None,
        is_premium: Optional[int] = 0,
        premium_expiry_time: Optional[str] = None,
    ) -> bool:
        try:
            self.cur.execute(
                "INSERT INTO emby_user VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    emby_username,
                    emby_id,
                    tg_id,
                    emby_is_unlock,
                    emby_unlock_time,
                    emby_watched_time,
                    emby_credits,
                    emby_line,
                    is_premium,
                    premium_expiry_time,
                ),
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        else:
            self.con.commit()
        return True

    def add_overseerr_user(self, user_id: int, user_email: str, tg_id: int):
        try:
            self.cur.execute(
                "INSERT INTO overseerr VALUES (?, ?, ?)",
                (user_id, user_email, tg_id),
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        else:
            self.con.commit()
            return True

    def add_user_data(self, tg_id, credits=0, donation=0):
        try:
            self.cur.execute(
                "INSERT INTO statistics (tg_id, donation, credits) VALUES (?, ?, ?)",
                (tg_id, donation, credits),
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        else:
            self.con.commit()
        return True

    def update_user_tg_id(self, tg_id, plex_id=None, emby_id=None):
        try:
            if plex_id:
                self.cur.execute(
                    "UPDATE user SET tg_id=? WHERE plex_id=?", (tg_id, plex_id)
                )
            if emby_id:
                self.cur.execute(
                    "UPDATE emby_user SET tg_id=? WHERE emby_id=?", (tg_id, emby_id)
                )
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        else:
            self.con.commit()
        return True

    def invitation_code_exists(self, code: str) -> bool:
        res = self.cur.execute(
            "SELECT 1 FROM invitation WHERE code=? LIMIT 1", (code,)
        ).fetchone()
        return bool(res)

    def add_invitation_code(
        self,
        code,
        owner,
        is_used=0,
        used_by=None,
        created_at=None,
        expires_at=None,
    ) -> bool:
        try:
            if created_at is None or expires_at is None:
                default_created_at, default_expires_at = get_invitation_timestamps()
                created_at = default_created_at if created_at is None else created_at
                expires_at = default_expires_at if expires_at is None else expires_at
            self.cur.execute(
                """
                INSERT INTO invitation
                    (code, owner, is_used, used_by, created_at, expires_at)
                VALUES
                    (?, ?, ?, ?, ?, ?)
                """,
                (code, owner, is_used, used_by, created_at, expires_at),
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        else:
            self.con.commit()
        return True

    def get_stats_by_tg_id(self, tg_id):
        return self.cur.execute(
            "SELECT * from statistics WHERE tg_id=?", (tg_id,)
        ).fetchone()

    def update_user_credits(
        self, credits: float, plex_id=None, emby_id=None, tg_id=None
    ):
        """Update user's credits"""
        try:
            if tg_id:
                self.cur.execute(
                    "UPDATE statistics SET credits=? WHERE tg_id=?", (credits, tg_id)
                )
            elif plex_id:
                self.cur.execute(
                    "UPDATE user SET credits=? WHERE plex_id=?", (credits, plex_id)
                )
            elif emby_id:
                self.cur.execute(
                    "UPDATE emby_user SET emby_credits=? WHERE emby_id=?",
                    (credits, emby_id),
                )
            else:
                logger.error("Error: there is no enough params")
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        else:
            self.con.commit()
        return True

    def get_user_credits(self, tg_id):
        """Get user's credits by tg_id"""
        try:
            rslt = self.cur.execute(
                "SELECT credits FROM statistics WHERE tg_id=?", (tg_id,)
            )
            res = rslt.fetchone()
            if res:
                return True, res[0]
            return False, f"未找到用户: {tg_id}"
        except Exception as e:
            logger.error(f"Error: {e}")
            return False, "获取积分失败"

    def update_user_donation(self, donation: int, tg_id):
        """Update user's donation"""
        try:
            self.cur.execute(
                "UPDATE statistics SET donation=? WHERE tg_id=?", (donation, tg_id)
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        else:
            self.con.commit()
        return True

    def transfer_tg_binding_assets(
        self,
        old_tg_id: int,
        new_tg_id: int,
        fee: float = 100.0,
        plex_id=None,
        emby_id=None,
    ):
        """迁移 TG 绑定关联数据。

        会合并积分/捐赠、签到、勋章、邀请码和活动历史，避免换绑后
        只迁了媒体账号但用户面板、排行和活动记录仍留在旧 TG ID。
        """
        if old_tg_id == new_tg_id:
            raise ValueError("新旧 TG ID 不能相同")

        cursor = self.cur
        fee = round(float(fee), 2)

        try:
            cursor.execute("BEGIN IMMEDIATE")

            old_stats = cursor.execute(
                "SELECT tg_id, donation, credits, debt_since FROM statistics WHERE tg_id=?",
                (old_tg_id,),
            ).fetchone()
            new_stats = cursor.execute(
                "SELECT tg_id, donation, credits, debt_since FROM statistics WHERE tg_id=?",
                (new_tg_id,),
            ).fetchone()

            old_donation = round(float(old_stats["donation"]), 2) if old_stats else 0.0
            old_credits = round(float(old_stats["credits"]), 2) if old_stats else 0.0
            old_debt_since = old_stats["debt_since"] if old_stats else None

            new_donation = round(float(new_stats["donation"]), 2) if new_stats else 0.0
            new_credits = round(float(new_stats["credits"]), 2) if new_stats else 0.0
            new_debt_since = new_stats["debt_since"] if new_stats else None

            remaining_credits = round(old_credits - fee, 2)
            final_credits = round(new_credits + remaining_credits, 2)
            final_donation = round(new_donation + old_donation, 2)

            debt_candidates = [ts for ts in (old_debt_since, new_debt_since) if ts]
            final_debt_since = None
            if final_credits < 0:
                final_debt_since = (
                    min(debt_candidates) if debt_candidates else int(time.time())
                )

            if new_stats:
                cursor.execute(
                    """
                    UPDATE statistics
                    SET donation = ?, credits = ?, debt_since = ?
                    WHERE tg_id = ?
                    """,
                    (final_donation, final_credits, final_debt_since, new_tg_id),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO statistics (tg_id, donation, credits, debt_since)
                    VALUES (?, ?, ?, ?)
                    """,
                    (new_tg_id, final_donation, final_credits, final_debt_since),
                )

            if old_stats:
                cursor.execute("DELETE FROM statistics WHERE tg_id = ?", (old_tg_id,))

            if plex_id:
                cursor.execute(
                    "UPDATE user SET tg_id = ? WHERE plex_id = ?",
                    (new_tg_id, plex_id),
                )
            if emby_id:
                cursor.execute(
                    "UPDATE emby_user SET tg_id = ? WHERE emby_id = ?",
                    (new_tg_id, emby_id),
                )

            cursor.execute(
                "UPDATE invitation SET owner = ? WHERE owner = ?",
                (new_tg_id, old_tg_id),
            )
            cursor.execute(
                "UPDATE wheel_stats SET tg_id = ? WHERE tg_id = ?",
                (new_tg_id, old_tg_id),
            )
            cursor.execute(
                "UPDATE blackjack_stats SET tg_id = ? WHERE tg_id = ?",
                (new_tg_id, old_tg_id),
            )
            cursor.execute(
                "UPDATE auctions SET created_by = ? WHERE created_by = ?",
                (new_tg_id, old_tg_id),
            )
            cursor.execute(
                "UPDATE auctions SET winner_id = ? WHERE winner_id = ?",
                (new_tg_id, old_tg_id),
            )
            cursor.execute(
                "UPDATE auction_bids SET bidder_id = ? WHERE bidder_id = ?",
                (new_tg_id, old_tg_id),
            )
            cursor.execute(
                "UPDATE overseerr SET tg_id = ? WHERE tg_id = ?",
                (new_tg_id, old_tg_id),
            )

            old_checkins = cursor.execute(
                """
                SELECT id, checkin_date, streak, month, credits_earned
                FROM checkin_stats
                WHERE tg_id = ?
                ORDER BY id ASC
                """,
                (old_tg_id,),
            ).fetchall()
            for row in old_checkins:
                existing = cursor.execute(
                    """
                    SELECT id, streak, credits_earned
                    FROM checkin_stats
                    WHERE tg_id = ? AND checkin_date = ?
                    """,
                    (new_tg_id, row["checkin_date"]),
                ).fetchone()
                if existing:
                    merged_streak = max(
                        int(existing["streak"] or 0), int(row["streak"] or 0)
                    )
                    merged_credits = round(
                        float(existing["credits_earned"] or 0)
                        + float(row["credits_earned"] or 0),
                        2,
                    )
                    cursor.execute(
                        """
                        UPDATE checkin_stats
                        SET streak = ?, credits_earned = ?
                        WHERE id = ?
                        """,
                        (merged_streak, merged_credits, existing["id"]),
                    )
                    cursor.execute(
                        "DELETE FROM checkin_stats WHERE id = ?", (row["id"],)
                    )
                else:
                    cursor.execute(
                        "UPDATE checkin_stats SET tg_id = ? WHERE id = ?",
                        (new_tg_id, row["id"]),
                    )

            old_medals = cursor.execute(
                """
                SELECT id, medal_code, source, acquired_at, is_active
                FROM user_medals
                WHERE tg_id = ?
                ORDER BY acquired_at ASC, id ASC
                """,
                (old_tg_id,),
            ).fetchall()
            for row in old_medals:
                existing = cursor.execute(
                    """
                    SELECT id, acquired_at, is_active
                    FROM user_medals
                    WHERE tg_id = ? AND medal_code = ?
                    """,
                    (new_tg_id, row["medal_code"]),
                ).fetchone()
                if existing:
                    merged_acquired_at = min(
                        int(existing["acquired_at"] or row["acquired_at"]),
                        int(row["acquired_at"]),
                    )
                    merged_is_active = max(
                        int(existing["is_active"] or 0), int(row["is_active"] or 0)
                    )
                    cursor.execute(
                        """
                        UPDATE user_medals
                        SET acquired_at = ?, is_active = ?
                        WHERE id = ?
                        """,
                        (merged_acquired_at, merged_is_active, existing["id"]),
                    )
                    cursor.execute(
                        "DELETE FROM user_medals WHERE id = ?", (row["id"],)
                    )
                else:
                    cursor.execute(
                        "UPDATE user_medals SET tg_id = ? WHERE id = ?",
                        (new_tg_id, row["id"]),
                    )

            # 清掉旧号和新号可能残留的离群记录，避免刚换绑就被旧状态影响。
            cursor.execute(
                "DELETE FROM group_member_left_status WHERE tg_id IN (?, ?)",
                (old_tg_id, new_tg_id),
            )

            self.con.commit()
            return {
                "fee_amount": fee,
                "remaining_credits": remaining_credits,
                "final_credits": final_credits,
                "final_donation": final_donation,
                "final_debt_since": final_debt_since,
            }
        except Exception:
            self.con.rollback()
            raise

    def update_invitation_status(self, code, used_by):
        try:
            self.cur.execute(
                "UPDATE invitation SET is_used=?,used_by=? WHERE code=?",
                (1, used_by, code),
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        else:
            self.con.commit()
        return True

    def update_all_lib_flag(
        self,
        all_lib: int,
        unlock_time=None,
        plex_id=None,
        emby_id=None,
        tg_id=None,
        media_server="plex",
    ):
        try:
            if media_server.lower() == "plex":
                if plex_id:
                    self.cur.execute(
                        "UPDATE user SET all_lib=?,unlock_time=? WHERE plex_id=?",
                        (all_lib, unlock_time, plex_id),
                    )
                elif tg_id:
                    self.cur.execute(
                        "UPDATE user SET all_lib=?,unlock_time=? WHERE tg_id=?",
                        (all_lib, unlock_time, tg_id),
                    )
            elif media_server.lower() == "emby":
                if emby_id:
                    self.cur.execute(
                        "UPDATE emby_user SET emby_is_unlock=?,emby_unlock_time=? WHERE emby_id=?",
                        (all_lib, unlock_time, emby_id),
                    )
                elif tg_id:
                    self.cur.execute(
                        "UPDATE emby_user SET emby_is_unlock=?,emby_unlock_time=? WHERE tg_id=?",
                        (all_lib, unlock_time, tg_id),
                    )
            else:
                logger.error("Error: please specify correct media server")
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        else:
            self.con.commit()
        return True

    def get_plex_users_num(self):
        rslt = self.cur.execute("SELECT count(*) FROM user")
        return rslt.fetchone()[0]

    def get_emby_users_num(self):
        rslt = self.cur.execute("SELECT count(*) FROM emby_user")
        return rslt.fetchone()[0]

    def get_plex_info_by_tg_id(self, tg_id):
        rslt = self.cur.execute("SELECT * FROM user WHERE tg_id = ?", (tg_id,))
        info = rslt.fetchone()
        return info

    def get_plex_info_by_plex_id(self, plex_id):
        rslt = self.cur.execute("SELECT * FROM user WHERE plex_id = ?", (plex_id,))
        info = rslt.fetchone()
        return info

    def get_plex_info_by_plex_username(self, plex_username: str):
        rslt = self.cur.execute(
            "SELECT * FROM user WHERE plex_username = ?", (plex_username,)
        )
        info = rslt.fetchone()
        return info

    def get_plex_info_by_plex_email(self, plex_email: str):
        rslt = self.cur.execute(
            "SELECT * FROM user WHERE LOWER(plex_email) = ?", (plex_email.lower(),)
        )
        info = rslt.fetchone()
        return info

    def get_emby_info_by_emby_username(self, username: str):
        return self.cur.execute(
            "SELECT * FROM emby_user WHERE LOWER(emby_username) = ?",
            (username.lower(),),
        ).fetchone()

    def get_emby_info_by_tg_id(self, tg_id):
        return self.cur.execute(
            "SELECT * FROM emby_user WHERE tg_id = ?", (tg_id,)
        ).fetchone()

    def get_emby_info_by_emby_id(self, emby_id):
        return self.cur.execute(
            "SELECT * FROM emby_user WHERE emby_id = ?", (emby_id,)
        ).fetchone()

    def get_overseerr_info_by_tg_id(self, tg_id):
        return self.cur.execute(
            "SELECT * FROM overseerr WHERE tg_id = ?", (tg_id,)
        ).fetchone()

    def get_overseerr_info_by_email(self, email):
        return self.cur.execute(
            "SELECT * FROM overseerr WHERE user_email = ?", (email,)
        ).fetchone()

    def get_credits_rank(self):
        """获取积分排行榜，只包含有账号的用户"""
        rslt = self.cur.execute(
            """SELECT DISTINCT s.tg_id, s.credits
            FROM statistics s
            WHERE EXISTS (
                SELECT 1 FROM user u WHERE u.tg_id = s.tg_id AND u.plex_id IS NOT NULL
            ) OR EXISTS (
                SELECT 1 FROM emby_user eu WHERE eu.tg_id = s.tg_id AND eu.emby_id IS NOT NULL
            )
            ORDER BY s.credits DESC"""
        )
        res = rslt.fetchall()
        return res

    def get_donation_rank(self):
        rslt = self.cur.execute(
            "SELECT tg_id,donation FROM statistics ORDER BY donation DESC"
        )
        res = rslt.fetchall()
        return res

    def get_plex_watched_time_rank(self):
        rslt = self.cur.execute(
            "SELECT plex_id,tg_id,plex_username,watched_time,is_premium FROM user ORDER BY watched_time DESC"
        )
        res = rslt.fetchall()
        return res

    def get_emby_watched_time_rank(self):
        return self.cur.execute(
            "SELECT emby_id,emby_username,emby_watched_time,is_premium,tg_id FROM emby_user ORDER BY emby_watched_time DESC"
        ).fetchall()

    def _normalize_medal_row(self, row):
        medal = dict(row)
        medal["multiplier"] = float(medal.get("multiplier") or 1.0)
        medal["price"] = float(medal.get("price") or 0.0)
        medal["is_special"] = bool(medal.get("is_special"))
        medal["is_active"] = bool(medal.get("is_active", 1))
        medal["owned"] = bool(medal.get("owned", 0))
        return medal

    def get_user_medals(self, tg_id: int):
        rows = self.cur.execute(
            """
            SELECT
                c.code,
                c.name,
                c.description,
                c.multiplier,
                c.price,
                c.icon_url,
                c.theme_color,
                c.is_special,
                c.is_active,
                um.acquired_at
            FROM user_medals um
            JOIN medal_catalog c ON c.code = um.medal_code
            WHERE um.tg_id = ? AND um.is_active = 1 AND c.is_active = 1
            ORDER BY c.display_order ASC, um.acquired_at ASC
            """,
            (tg_id,),
        ).fetchall()
        return [self._normalize_medal_row(row) for row in rows]

    def get_checkin_total_leaderboard(self, limit: int = 3):
        return self.cur.execute(
            """
            SELECT tg_id, COUNT(*) AS total_days, MAX(id) AS last_checkin_id
            FROM checkin_stats
            GROUP BY tg_id
            ORDER BY total_days DESC, last_checkin_id ASC, tg_id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    def sync_checkin_total_rank_medals(self):
        medal_codes = [medal["code"] for medal in CHECKIN_TOTAL_RANK_MEDALS]
        leaderboard = self.get_checkin_total_leaderboard(limit=len(CHECKIN_TOTAL_RANK_MEDALS))
        now_ts = int(time.time())
        placeholders = ",".join("?" for _ in medal_codes)

        try:
            cursor = self.cur
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                f"""
                UPDATE user_medals
                SET is_active = 0
                WHERE medal_code IN ({placeholders}) AND is_active = 1
                """,
                tuple(medal_codes),
            )

            for medal, row in zip(CHECKIN_TOTAL_RANK_MEDALS, leaderboard):
                cursor.execute(
                    """
                    INSERT INTO user_medals (tg_id, medal_code, source, acquired_at, is_active)
                    VALUES (?, ?, ?, ?, 1)
                    ON CONFLICT(tg_id, medal_code) DO UPDATE SET
                        source = excluded.source,
                        acquired_at = excluded.acquired_at,
                        is_active = 1
                    """,
                    (
                        row["tg_id"],
                        medal["code"],
                        "checkin_total_rank",
                        now_ts,
                    ),
                )

            self.con.commit()
            return leaderboard
        except Exception as e:
            self.con.rollback()
            logger.error(f"同步签到总榜勋章失败: {e}")
            return []

    def get_users_medals_map(self, tg_ids):
        if not tg_ids:
            return {}

        unique_tg_ids = []
        seen = set()
        for tg_id in tg_ids:
            if tg_id is None or tg_id in seen:
                continue
            unique_tg_ids.append(tg_id)
            seen.add(tg_id)

        if not unique_tg_ids:
            return {}

        placeholders = ",".join("?" for _ in unique_tg_ids)
        rows = self.cur.execute(
            f"""
            SELECT
                um.tg_id,
                c.code,
                c.name,
                c.description,
                c.multiplier,
                c.price,
                c.icon_url,
                c.theme_color,
                c.is_special,
                c.is_active,
                um.acquired_at
            FROM user_medals um
            JOIN medal_catalog c ON c.code = um.medal_code
            WHERE um.tg_id IN ({placeholders}) AND um.is_active = 1 AND c.is_active = 1
            ORDER BY c.display_order ASC, um.acquired_at ASC
            """,
            tuple(unique_tg_ids),
        ).fetchall()

        medal_map = {tg_id: [] for tg_id in unique_tg_ids}
        for row in rows:
            normalized = self._normalize_medal_row(row)
            tg_id = normalized.pop("tg_id")
            medal_map.setdefault(tg_id, []).append(normalized)
        return medal_map

    def get_user_medal_multiplier(self, tg_id: int) -> float:
        multiplier = 1.0
        for medal in self.get_user_medals(tg_id):
            multiplier *= float(medal.get("multiplier") or 1.0)
        return round(multiplier, 4)

    def get_medal_shop_payload(self, tg_id: int):
        self.sync_checkin_total_rank_medals()
        owned_medals = self.get_user_medals(tg_id)
        owned_codes = {medal["code"] for medal in owned_medals}
        shop_rows = self.cur.execute(
            """
            SELECT
                code,
                name,
                description,
                multiplier,
                price,
                icon_url,
                theme_color,
                is_special,
                is_active,
                is_shop_visible,
                CASE WHEN EXISTS (
                    SELECT 1
                    FROM user_medals um
                    WHERE um.medal_code = medal_catalog.code
                      AND um.tg_id = ?
                      AND um.is_active = 1
                ) THEN 1 ELSE 0 END AS owned
            FROM medal_catalog
            WHERE is_active = 1 AND is_shop_visible = 1
            ORDER BY display_order ASC, created_at ASC
            """,
            (tg_id,),
        ).fetchall()
        shop_items = [self._normalize_medal_row(row) for row in shop_rows]

        credits_ok, current_credits = self.get_user_credits(tg_id)
        current_credits = float(current_credits) if credits_ok else 0.0
        current_multiplier = self.get_user_medal_multiplier(tg_id)

        return {
            "current_credits": round(current_credits, 2),
            "current_multiplier": round(current_multiplier, 2),
            "owned_medals": owned_medals,
            "shop_items": shop_items,
            "owned_count": len(owned_medals),
            "owned_codes": list(owned_codes),
        }

    def purchase_medal(self, tg_id: int, medal_code: str):
        medal = self.cur.execute(
            """
            SELECT code, name, description, multiplier, price, icon_url, theme_color, is_special, is_active, is_shop_visible
            FROM medal_catalog
            WHERE code = ? AND is_active = 1 AND is_shop_visible = 1
            """,
            (medal_code,),
        ).fetchone()
        if not medal:
            return False, "勋章不存在或已下架", None

        existing = self.cur.execute(
            "SELECT 1 FROM user_medals WHERE tg_id = ? AND medal_code = ? AND is_active = 1",
            (tg_id, medal_code),
        ).fetchone()
        if existing:
            return False, "你已经拥有这枚勋章了", self.get_medal_shop_payload(tg_id)

        stats_row = self.cur.execute(
            "SELECT credits FROM statistics WHERE tg_id = ?",
            (tg_id,),
        ).fetchone()
        if not stats_row:
            return False, "当前用户没有积分账户，暂时无法购买勋章", None

        price = float(medal["price"] or 0.0)
        current_credits = float(stats_row["credits"] or 0.0)
        if current_credits < price:
            return (
                False,
                f"积分不足，还需要 {round(price - current_credits, 2):.2f} 积分",
                self.get_medal_shop_payload(tg_id),
            )

        try:
            cursor = self.cur
            cursor.execute("BEGIN IMMEDIATE")

            fresh_credits_row = cursor.execute(
                "SELECT credits FROM statistics WHERE tg_id = ?",
                (tg_id,),
            ).fetchone()
            fresh_credits = float(fresh_credits_row["credits"] or 0.0) if fresh_credits_row else 0.0
            if fresh_credits < price:
                self.con.rollback()
                return (
                    False,
                    f"积分不足，还需要 {round(price - fresh_credits, 2):.2f} 积分",
                    self.get_medal_shop_payload(tg_id),
                )

            cursor.execute(
                "UPDATE statistics SET credits = ? WHERE tg_id = ?",
                (round(fresh_credits - price, 2), tg_id),
            )
            cursor.execute(
                """
                INSERT INTO user_medals (tg_id, medal_code, source, acquired_at, is_active)
                VALUES (?, ?, 'shop', ?, 1)
                """,
                (tg_id, medal_code, int(time.time())),
            )
            self.con.commit()
        except Exception as e:
            self.con.rollback()
            logger.error(f"购买勋章失败: {e}")
            return False, "购买勋章失败，请稍后再试", self.get_medal_shop_payload(tg_id)

        payload = self.get_medal_shop_payload(tg_id)
        return True, f"已成功购入 {medal['name']}", payload

    def verify_invitation_code_is_used(self, code):
        rslt = self.cur.execute(
            "SELECT is_used, owner, expires_at FROM invitation WHERE code=?", (code,)
        )
        res = rslt.fetchone()
        return res

    def get_invitation_code_by_owner(self, tg_id, is_available=True):
        if is_available:
            rslt = self.cur.execute(
                """
                SELECT code FROM invitation
                WHERE owner=? AND is_used=0
                  AND (expires_at IS NULL OR expires_at > strftime('%s', 'now'))
                ORDER BY created_at DESC, code DESC
                """,
                (tg_id,),
            )
        else:
            rslt = self.cur.execute(
                "SELECT code FROM invitation WHERE owner=? ORDER BY created_at DESC, code DESC",
                (tg_id,),
            )
        res = rslt.fetchall()
        res = [_[0] for _ in res]
        return res

    def get_invited_count_by_owner(self, tg_id):
        """获取某个用户通过邀请码邀请的人数（不包括兑换积分的邀请码）"""
        try:
            # 只统计真正注册账号的邀请，排除兑换积分的情况
            # 兑换积分时 used_by 格式为 "credits_by_{user_id}"
            result = self.cur.execute(
                "SELECT COUNT(*) FROM invitation WHERE owner=? AND is_used=1 AND used_by NOT LIKE 'credits_by_%'",
                (tg_id,),
            )
            count = result.fetchone()
            return count[0] if count else 0
        except Exception as e:
            logger.error(f"Error getting invited count: {e}")
            return 0

    def set_emby_line(self, line, tg_id=None, emby_id=None):
        try:
            if tg_id:
                self.cur.execute(
                    "UPDATE emby_user SET emby_line=? WHERE tg_id=?", (line, tg_id)
                )
            elif emby_id:
                self.cur.execute(
                    "UPDATE emby_user SET emby_line=? WHERE emby_id=?", (line, emby_id)
                )
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        else:
            self.con.commit()
        return True

    def get_emby_line(self, tg_id):
        return self.cur.execute(
            "SELECT emby_line FROM emby_user WHERE tg_id=?", (tg_id,)
        ).fetchone()[0]

    def get_emby_user_with_binded_line(self):
        rslt = self.cur.execute(
            "SELECT emby_username,tg_id,emby_line,is_premium FROM emby_user WHERE emby_line IS NOT NULL"
        )
        return rslt.fetchall()

    def set_plex_line(self, line, tg_id=None, plex_id=None):
        try:
            if tg_id:
                self.cur.execute(
                    "UPDATE user SET plex_line=? WHERE tg_id=?", (line, tg_id)
                )
            elif plex_id:
                self.cur.execute(
                    "UPDATE user SET plex_line=? WHERE plex_id=?", (line, plex_id)
                )
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        else:
            self.con.commit()
        return True

    def get_plex_line(self, tg_id):
        return self.cur.execute(
            "SELECT plex_line FROM user WHERE tg_id=?", (tg_id,)
        ).fetchone()[0]

    def get_plex_user_with_binded_line(self):
        rslt = self.cur.execute(
            "SELECT plex_username,tg_id,plex_line,is_premium FROM user WHERE plex_line IS NOT NULL"
        )
        return rslt.fetchall()

    def add_wheel_spin_record(self, tg_id: int, item_name: str, credits_change: float):
        """记录转盘旋转记录"""
        try:
            timestamp = int(time.time())
            date = datetime.now(settings.TZ).strftime("%Y-%m-%d")

            self.cur.execute(
                "INSERT INTO wheel_stats (tg_id, item_name, credits_change, timestamp, date) VALUES (?, ?, ?, ?, ?)",
                (tg_id, item_name, credits_change, timestamp, date),
            )
            self.con.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding wheel spin record: {e}")
            return False

    def get_wheel_stats(self):
        """获取转盘统计数据"""
        try:
            # 获取总抽奖次数
            total_spins = self.cur.execute(
                "SELECT COUNT(*) FROM wheel_stats"
            ).fetchone()[0]

            # 获取参与用户数（去重）
            active_users = self.cur.execute(
                "SELECT COUNT(DISTINCT tg_id) FROM wheel_stats"
            ).fetchone()[0]

            # 获取今日抽奖次数（使用UTC+8北京时间）
            today = datetime.now(settings.TZ).strftime("%Y-%m-%d")
            today_spins = self.cur.execute(
                "SELECT COUNT(*) FROM wheel_stats WHERE date = ?", (today,)
            ).fetchone()[0]

            # 获取本周抽奖次数（使用UTC+8北京时间）
            week_ago = (datetime.now(settings.TZ) - timedelta(days=7)).strftime(
                "%Y-%m-%d"
            )
            week_spins = self.cur.execute(
                "SELECT COUNT(*) FROM wheel_stats WHERE date >= ?", (week_ago,)
            ).fetchone()[0]

            # 获取转盘总积分变化（通过转盘获得或失去的积分总和）
            total_credits_change_result = self.cur.execute(
                "SELECT SUM(credits_change) FROM wheel_stats"
            ).fetchone()
            total_credits_change = (
                float(total_credits_change_result[0])
                if total_credits_change_result[0]
                else 0.0
            )

            # 获取幸运大转盘中总邀请码发放数
            total_invite_codes_result = self.cur.execute(
                'SELECT COUNT(*) FROM wheel_stats where item_name="邀请码 1 枚"'
            ).fetchone()
            total_invite_codes = (
                int(total_invite_codes_result[0]) if total_invite_codes_result[0] else 0
            )

            return {
                "totalSpins": total_spins,
                "activeUsers": active_users,
                "todaySpins": today_spins,
                "lastWeekSpins": week_spins,
                "totalCreditsChange": total_credits_change,
                "totalInviteCodes": total_invite_codes,
            }
        except Exception as e:
            logger.error(f"Error getting wheel stats: {e}")
            return {
                "totalSpins": 0,
                "activeUsers": 0,
                "todaySpins": 0,
                "lastWeekSpins": 0,
                "totalCreditsChange": 0.0,
                "totalInviteCodes": 0,
            }

    def create_auction(
        self,
        title: str,
        description: str,
        starting_price: float,
        end_time: int,
        created_by: int,
    ) -> Optional[int]:
        """创建竞拍"""
        try:
            import time

            created_at = int(time.time())

            self.cur.execute(
                """INSERT INTO auctions 
                   (title, description, starting_price, current_price, end_time, created_by, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    title,
                    description,
                    starting_price,
                    starting_price,
                    end_time,
                    created_by,
                    created_at,
                ),
            )
            self.con.commit()
            return self.cur.lastrowid
        except Exception as e:
            logger.error(f"Error creating auction: {e}")
            return None

    def get_auction_by_id(self, auction_id: int) -> Optional[dict]:
        """根据ID获取竞拍信息"""
        try:
            result = self.cur.execute(
                "SELECT * FROM auctions WHERE id = ?", (auction_id,)
            ).fetchone()

            if result:
                return {
                    "id": result[0],
                    "title": result[1] or f"竞拍活动 #{result[0]}",
                    "description": result[2] or "无描述",
                    "starting_price": result[3] or 0,
                    "current_price": result[4] or result[3] or 0,
                    "end_time": result[5],
                    "created_by": result[6],
                    "created_at": result[7],
                    "is_active": result[8],
                    "winner_id": result[9],
                    "bid_count": result[10],
                }
            return None
        except Exception as e:
            logger.error(f"Error getting auction by id: {e}")
            return None

    def get_active_auctions(self, limit: int = 50) -> List[dict]:
        """获取活跃竞拍列表"""
        try:
            import time

            current_time = int(time.time())

            results = self.cur.execute(
                """SELECT * FROM auctions 
                   WHERE is_active = 1 AND end_time > ? 
                   ORDER BY created_at DESC LIMIT ?""",
                (current_time, limit),
            ).fetchall()

            auctions = []
            for result in results:
                auctions.append(
                    {
                        "id": result[0],
                        "title": result[1] or f"竞拍活动 #{result[0]}",
                        "description": result[2] or "无描述",
                        "starting_price": result[3] or 0,
                        "current_price": result[4] or result[3] or 0,
                        "end_time": result[5],
                        "created_by": result[6],
                        "created_at": result[7],
                        "is_active": result[8],
                        "winner_id": result[9],
                        "bid_count": result[10],
                    }
                )
            return auctions
        except Exception as e:
            logger.error(f"Error getting active auctions: {e}")
            return []

    def place_bid(self, auction_id: int, bidder_id: int, bid_amount: float) -> bool:
        """出价"""
        try:
            import time

            bid_time = int(time.time())

            # 检查竞拍是否存在且活跃
            auction = self.get_auction_by_id(auction_id)
            if (
                not auction
                or not auction["is_active"]
                or auction["end_time"] <= bid_time
            ):
                return False

            # 检查出价是否高于当前价格
            if bid_amount <= auction["current_price"]:
                return False

            # 插入出价记录
            self.cur.execute(
                "INSERT INTO auction_bids (auction_id, bidder_id, bid_amount, bid_time) VALUES (?, ?, ?, ?)",
                (auction_id, bidder_id, bid_amount, bid_time),
            )

            # 更新竞拍当前价格和出价次数
            self.cur.execute(
                "UPDATE auctions SET current_price = ?, bid_count = bid_count + 1 WHERE id = ?",
                (bid_amount, auction_id),
            )

            self.con.commit()
            return True
        except Exception as e:
            logger.error(f"Error placing bid: {e}")
            return False

    def get_auction_bids(self, auction_id: int, limit: int = 50) -> List[dict]:
        """获取竞拍出价记录"""
        try:
            results = self.cur.execute(
                """SELECT ab.* 
                FROM auction_bids ab 
                WHERE ab.auction_id = ? 
                ORDER BY ab.bid_time DESC 
                LIMIT ?""",
                (auction_id, limit),
            ).fetchall()

            bids = []
            for result in results:
                bids.append(
                    {
                        "id": result[0],
                        "auction_id": result[1],
                        "bidder_id": result[2],
                        "bid_amount": result[3],
                        "bid_time": result[4],
                        "bidder_name": f"用户{result[2]}",
                    }
                )
            return bids
        except Exception as e:
            logger.error(f"Error getting auction bids: {e}")
            return []

    def get_user_highest_bid(self, auction_id: int, user_id: int) -> Optional[float]:
        """获取用户在特定竞拍中的最高出价"""
        try:
            result = self.cur.execute(
                "SELECT MAX(bid_amount) FROM auction_bids WHERE auction_id = ? AND bidder_id = ?",
                (auction_id, user_id),
            ).fetchone()

            return result[0] if result and result[0] else None
        except Exception as e:
            logger.error(f"Error getting user highest bid: {e}")
            return None

    def finish_expired_auctions(self) -> List[dict]:
        """结束过期的竞拍"""
        try:
            import time

            current_time = int(time.time())

            # 查找过期的活跃竞拍
            expired_auctions = self.cur.execute(
                "SELECT * FROM auctions WHERE is_active = 1 AND end_time <= ?",
                (current_time,),
            ).fetchall()

            finished_auctions = []
            for auction in expired_auctions:
                auction_id = auction[0]

                # 获取最高出价者
                highest_bid = self.cur.execute(
                    """SELECT bidder_id, MAX(bid_amount) FROM auction_bids 
                       WHERE auction_id = ? GROUP BY auction_id""",
                    (auction_id,),
                ).fetchone()

                winner_id = highest_bid[0] if highest_bid else None
                final_price = auction[4]  # current_price from auctions table
                credits_reduced = False
                # 如果有获胜者，扣除其积分
                if winner_id and highest_bid:
                    final_price = highest_bid[1]  # 使用最高出价作为最终价格

                    # 扣除获胜者的积分
                    success, current_credits = self.get_user_credits(winner_id)
                    if success and current_credits >= final_price:
                        self.cur.execute(
                            "UPDATE statistics SET credits = credits - ? WHERE tg_id = ?",
                            (final_price, winner_id),
                        )
                        credits_reduced = True
                        logger.info(
                            f"Auction {auction_id} finished: deducted {final_price} credits from winner {winner_id}"
                        )
                    else:
                        logger.warning(
                            f"Winner {winner_id} has insufficient credits ({current_credits}) for auction {auction_id} (price: {final_price})"
                        )

                # 更新竞拍状态
                self.cur.execute(
                    "UPDATE auctions SET is_active = 0, winner_id = ?, current_price = ? WHERE id = ?",
                    (winner_id, final_price, auction_id),
                )

                finished_auctions.append(
                    {
                        "id": auction_id,
                        "title": auction[1] or f"竞拍活动 #{auction_id}",
                        "winner_id": winner_id,
                        "final_price": final_price,
                        "credits_reduced": credits_reduced,
                    }
                )

            self.con.commit()
            return finished_auctions
        except Exception as e:
            logger.error(f"Error finishing expired auctions: {e}")
            logger.error(traceback.format_exc())
            return []

    def get_auction_stats(self) -> dict:
        """获取竞拍统计数据"""
        try:
            # 总竞拍数
            total_auctions = self.cur.execute(
                "SELECT COUNT(*) FROM auctions"
            ).fetchone()[0]

            # 活跃竞拍数
            import time

            current_time = int(time.time())
            active_auctions = self.cur.execute(
                "SELECT COUNT(*) FROM auctions WHERE is_active = 1 AND end_time > ?",
                (current_time,),
            ).fetchone()[0]

            # 总出价数
            total_bids = self.cur.execute(
                "SELECT COUNT(*) FROM auction_bids"
            ).fetchone()[0]

            # 总成交价值
            total_value_result = self.cur.execute(
                "SELECT SUM(current_price) FROM auctions WHERE winner_id IS NOT NULL"
            ).fetchone()
            total_value = float(total_value_result[0]) if total_value_result[0] else 0.0

            return {
                "total_auctions": total_auctions,
                "active_auctions": active_auctions,
                "total_bids": total_bids,
                "total_value": total_value,
            }
        except Exception as e:
            logger.error(f"Error getting auction stats: {e}")
            return {
                "total_auctions": 0,
                "active_auctions": 0,
                "total_bids": 0,
                "total_value": 0.0,
            }

    def get_all_auctions(
        self, status: str = None, limit: int = 50, offset: int = 0
    ) -> List[dict]:
        """获取所有竞拍活动（管理员用）"""
        try:
            if status:
                if status == "active":
                    import time

                    current_time = int(time.time())
                    self.cur.execute(
                        """SELECT * FROM auctions 
                        WHERE is_active = 1 AND end_time > ? 
                        ORDER BY created_at DESC 
                        LIMIT ? OFFSET ?""",
                        (current_time, limit, offset),
                    )
                elif status == "ended":
                    import time

                    current_time = int(time.time())
                    self.cur.execute(
                        """SELECT * FROM auctions 
                        WHERE is_active = 0 OR end_time <= ? 
                        ORDER BY created_at DESC 
                        LIMIT ? OFFSET ?""",
                        (current_time, limit, offset),
                    )
                else:
                    self.cur.execute(
                        "SELECT * FROM auctions ORDER BY created_at DESC LIMIT ? OFFSET ?",
                        (limit, offset),
                    )
            else:
                self.cur.execute(
                    "SELECT * FROM auctions ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )

            auctions = []
            for auction in self.cur.fetchall():
                # 获取出价数量
                bid_count = self.cur.execute(
                    "SELECT COUNT(*) FROM auction_bids WHERE auction_id = ?",
                    (auction[0],),
                ).fetchone()[0]

                auctions.append(
                    {
                        "id": auction[0],
                        "title": auction[1] or f"竞拍活动 #{auction[0]}",
                        "description": auction[2] or "无描述",
                        "starting_price": auction[3] or 0,
                        "current_price": auction[4] or auction[3] or 0,
                        "end_time": auction[5],
                        "created_by": auction[6],
                        "created_at": auction[7],
                        "is_active": bool(auction[8]),
                        "winner_id": auction[9],
                        "bid_count": bid_count,
                        "status": self._get_auction_status(auction),
                    }
                )

            return auctions
        except Exception as e:
            logger.error(f"Error getting all auctions: {e}")
            return []

    def _get_auction_status(self, auction) -> str:
        """获取竞拍状态"""
        import time

        current_time = int(time.time())

        if not auction[8]:  # is_active
            return "ended"
        elif auction[5] <= current_time:  # end_time
            return "ended"
        else:
            return "active"

    def update_auction(self, auction_id: int, update_data: dict) -> bool:
        """更新竞拍活动"""
        try:
            # 构建更新语句
            set_clauses = []
            values = []

            if "title" in update_data:
                set_clauses.append("title = ?")
                values.append(update_data["title"])

            if "description" in update_data:
                set_clauses.append("description = ?")
                values.append(update_data["description"])

            if "starting_price" in update_data:
                set_clauses.append("starting_price = ?")
                values.append(update_data["starting_price"])

            if "end_time" in update_data:
                set_clauses.append("end_time = ?")
                values.append(update_data["end_time"])

            if not set_clauses:
                return False

            values.append(auction_id)

            self.cur.execute(
                f"UPDATE auctions SET {', '.join(set_clauses)} WHERE id = ?",
                tuple(values),
            )

            self.con.commit()
            return self.cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating auction: {e}")
            return False

    def delete_auction(self, auction_id: int) -> bool:
        """删除竞拍活动"""
        try:
            # 先删除相关的出价记录
            self.cur.execute(
                "DELETE FROM auction_bids WHERE auction_id = ?", (auction_id,)
            )

            # 再删除竞拍活动
            self.cur.execute("DELETE FROM auctions WHERE id = ?", (auction_id,))

            self.con.commit()
            return self.cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting auction: {e}")
            return False

    def finish_auction_by_id(self, auction_id: int) -> tuple:
        """手动结束指定竞拍活动"""
        try:
            # 获取竞拍信息
            auction = self.get_auction_by_id(auction_id)
            if not auction:
                return False, f"竞拍 id {auction_id} 不存在"

            # 获取最高出价
            highest_bid = self.cur.execute(
                """SELECT bidder_id, bid_amount FROM auction_bids 
                WHERE auction_id = ? ORDER BY bid_amount DESC LIMIT 1""",
                (auction_id,),
            ).fetchone()

            winner_id = None
            final_price = auction["starting_price"]
            credits_reduced = False

            if highest_bid:
                winner_id = highest_bid[0]
                final_price = highest_bid[1]

                # 扣除获胜者的积分
                success, current_credits = self.get_user_credits(winner_id)
                if success and current_credits >= final_price:
                    self.cur.execute(
                        "UPDATE statistics SET credits = credits - ? WHERE tg_id = ?",
                        (final_price, winner_id),
                    )
                    credits_reduced = True

            # 更新竞拍状态
            self.cur.execute(
                """UPDATE auctions 
                SET is_active = 0, winner_id = ?, current_price = ? 
                WHERE id = ?""",
                (winner_id, final_price, auction_id),
            )

            self.con.commit()
            return True, {
                "id": auction_id,
                "title": auction["title"],
                "winner_id": winner_id,
                "final_price": final_price,
                "credits_reduced": credits_reduced,
            }

        except Exception as e:
            logger.error(f"Error finishing auction {auction_id}: {e}")
            logger.error(traceback.format_exc())
            return False, str(e)

    def get_user_auction_history(self, user_id: int, limit: int = 20) -> List[dict]:
        """获取用户参与的竞拍历史"""
        try:
            self.cur.execute(
                """SELECT DISTINCT a.*, ab.bid_amount as user_highest_bid
                FROM auctions a
                JOIN auction_bids ab ON a.id = ab.auction_id
                WHERE ab.bidder_id = ?
                ORDER BY a.created_at DESC
                LIMIT ?""",
                (user_id, limit),
            )

            auctions = []
            for auction in self.cur.fetchall():
                # 获取用户最高出价
                highest_bid = self.cur.execute(
                    """SELECT MAX(bid_amount) FROM auction_bids 
                    WHERE auction_id = ? AND bidder_id = ?""",
                    (auction[0], user_id),
                ).fetchone()[0]

                auctions.append(
                    {
                        "id": auction[0],
                        "title": auction[1] or f"竞拍活动 #{auction[0]}",
                        "description": auction[2] or "无描述",
                        "starting_price": auction[3] or 0,
                        "current_price": auction[4] or auction[3] or 0,
                        "end_time": auction[5],
                        "created_by": auction[6],
                        "created_at": auction[7],
                        "is_active": bool(auction[8]),
                        "winner_id": auction[9],
                        "user_highest_bid": highest_bid,
                        "is_winner": auction[9] == user_id,
                    }
                )

            return auctions
        except Exception as e:
            logger.error(f"Error getting user auction history: {e}")
            return []

    def get_detailed_auction_stats(
        self, start_date: int = None, end_date: int = None
    ) -> dict:
        """获取详细的竞拍统计数据"""
        try:
            # 设置默认时间范围（如果未提供）
            if not start_date:
                start_date = 0
            if not end_date:
                end_date = int(time.time())

            # 基本统计
            stats = self.get_auction_stats()

            # 时间段内的统计
            period_auctions = self.cur.execute(
                "SELECT COUNT(*) FROM auctions WHERE created_at BETWEEN ? AND ?",
                (start_date, end_date),
            ).fetchone()[0]

            period_bids = self.cur.execute(
                """SELECT COUNT(*) FROM auction_bids ab
                JOIN auctions a ON ab.auction_id = a.id
                WHERE a.created_at BETWEEN ? AND ?""",
                (start_date, end_date),
            ).fetchone()[0]

            # 平均出价数
            avg_bids_result = self.cur.execute(
                """SELECT AVG(bid_count) FROM (
                    SELECT COUNT(*) as bid_count FROM auction_bids 
                    GROUP BY auction_id
                )"""
            ).fetchone()
            avg_bids = float(avg_bids_result[0]) if avg_bids_result[0] else 0.0

            # 最高成交价
            highest_price_result = self.cur.execute(
                "SELECT MAX(current_price) FROM auctions WHERE winner_id IS NOT NULL"
            ).fetchone()
            highest_price = (
                float(highest_price_result[0]) if highest_price_result[0] else 0.0
            )

            stats.update(
                {
                    "period_auctions": period_auctions,
                    "period_bids": period_bids,
                    "avg_bids_per_auction": avg_bids,
                    "highest_transaction": highest_price,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )

            return stats
        except Exception as e:
            logger.error(f"Error getting detailed auction stats: {e}")
            return self.get_auction_stats()

    def get_user_wheel_stats(self, tg_id: int):
        """获取用户个人转盘统计数据"""
        try:
            # 使用UTC+8北京时间
            today = datetime.now(settings.TZ).strftime("%Y-%m-%d")
            week_ago = (datetime.now(settings.TZ) - timedelta(days=7)).strftime(
                "%Y-%m-%d"
            )

            # 获取用户今日游戏次数
            today_spins = self.cur.execute(
                "SELECT COUNT(*) FROM wheel_stats WHERE tg_id = ? AND date = ?",
                (tg_id, today),
            ).fetchone()[0]

            # 获取用户总游戏次数
            total_spins = self.cur.execute(
                "SELECT COUNT(*) FROM wheel_stats WHERE tg_id = ?", (tg_id,)
            ).fetchone()[0]

            # 获取用户本周游戏次数
            week_spins = self.cur.execute(
                "SELECT COUNT(*) FROM wheel_stats WHERE tg_id = ? AND date >= ?",
                (tg_id, week_ago),
            ).fetchone()[0]

            # 获取用户总积分变化
            total_credits_change_result = self.cur.execute(
                "SELECT SUM(credits_change) FROM wheel_stats WHERE tg_id = ?", (tg_id,)
            ).fetchone()
            total_credits_change = (
                float(total_credits_change_result[0])
                if total_credits_change_result[0]
                else 0.0
            )

            # 获取用户今日积分变化
            today_credits_change_result = self.cur.execute(
                "SELECT SUM(credits_change) FROM wheel_stats WHERE tg_id = ? AND date = ?",
                (tg_id, today),
            ).fetchone()
            today_credits_change = (
                float(today_credits_change_result[0])
                if today_credits_change_result[0]
                else 0.0
            )

            # 获取用户本周积分变化
            week_credits_change_result = self.cur.execute(
                "SELECT SUM(credits_change) FROM wheel_stats WHERE tg_id = ? AND date >= ?",
                (tg_id, week_ago),
            ).fetchone()
            week_credits_change = (
                float(week_credits_change_result[0])
                if week_credits_change_result[0]
                else 0.0
            )

            # 获取用户通过转盘获得的邀请码数量
            invite_codes_earned = self.cur.execute(
                'SELECT COUNT(*) FROM wheel_stats WHERE tg_id = ? AND item_name = "邀请码 1 枚"',
                (tg_id,),
            ).fetchone()[0]

            # 获取用户今日获得的邀请码数量
            today_invite_codes = self.cur.execute(
                'SELECT COUNT(*) FROM wheel_stats WHERE tg_id = ? AND item_name = "邀请码 1 枚" AND date = ?',
                (tg_id, today),
            ).fetchone()[0]

            # 获取用户本周获得的邀请码数量
            week_invite_codes = self.cur.execute(
                'SELECT COUNT(*) FROM wheel_stats WHERE tg_id = ? AND item_name = "邀请码 1 枚" AND date >= ?',
                (tg_id, week_ago),
            ).fetchone()[0]

            # 获取用户最近5次游戏记录
            recent_games = self.cur.execute(
                """SELECT item_name, credits_change, date, timestamp 
                   FROM wheel_stats 
                   WHERE tg_id = ? 
                   ORDER BY timestamp DESC 
                   LIMIT 5""",
                (tg_id,),
            ).fetchall()

            recent_games_list = []
            for game in recent_games:
                recent_games_list.append(
                    {
                        "item_name": game[0],
                        "credits_change": game[1],
                        "date": game[2],
                        "timestamp": game[3],
                    }
                )

            return {
                "today_spins": today_spins,
                "total_spins": total_spins,
                "week_spins": week_spins,
                "total_credits_change": total_credits_change,
                "today_credits_change": today_credits_change,
                "week_credits_change": week_credits_change,
                "total_invite_codes": invite_codes_earned,
                "today_invite_codes": today_invite_codes,
                "week_invite_codes": week_invite_codes,
                "recent_games": recent_games_list,
            }
        except Exception as e:
            logger.error(f"Error getting user wheel stats: {e}")
            return {
                "today_spins": 0,
                "total_spins": 0,
                "week_spins": 0,
                "total_credits_change": 0.0,
                "today_credits_change": 0.0,
                "week_credits_change": 0.0,
                "total_invite_codes": 0,
                "today_invite_codes": 0,
                "week_invite_codes": 0,
                "recent_games": [],
            }

    def add_blackjack_game_record(
        self,
        user_id: int,
        bet_amount: float,
        result: str,
        credits_change: float,
        player_score: int,
        dealer_score: int,
    ):
        """记录21点游戏记录"""
        try:
            timestamp = int(time.time())
            date = datetime.now(settings.TZ).strftime("%Y-%m-%d")

            self.cur.execute(
                """INSERT INTO blackjack_stats
                   (tg_id, bet_amount, result, credits_change, player_score, dealer_score, timestamp, date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, bet_amount, result, credits_change, player_score, dealer_score, timestamp, date),
            )
            self.con.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding blackjack game record: {e}")
            return False

    def get_blackjack_stats(self):
        """获取21点游戏统计数据"""
        try:
            # 获取总游戏局数
            total_games = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats"
            ).fetchone()[0]

            # 获取玩家总赢次数
            total_wins = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats WHERE result IN ('win', 'blackjack', 'dealer_bust')"
            ).fetchone()[0]

            # 获取玩家总输次数
            total_losses = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats WHERE result IN ('lose', 'bust')"
            ).fetchone()[0]

            # 获取平局次数
            total_pushes = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats WHERE result = 'push'"
            ).fetchone()[0]

            # 获取黑杰克次数
            total_blackjacks = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats WHERE result = 'blackjack'"
            ).fetchone()[0]

            # 获取总下注金额
            total_bet_result = self.cur.execute(
                "SELECT SUM(bet_amount) FROM blackjack_stats"
            ).fetchone()
            total_bet_amount = float(total_bet_result[0]) if total_bet_result[0] else 0.0

            # 获取总赔付金额（正数为玩家赢，负数为庄家赢）
            total_payout_result = self.cur.execute(
                "SELECT SUM(credits_change) FROM blackjack_stats"
            ).fetchone()
            total_payout_amount = float(total_payout_result[0]) if total_payout_result[0] else 0.0

            # 计算庄家优势
            house_edge = ((total_bet_amount - total_payout_amount) / total_bet_amount * 100) if total_bet_amount > 0 else 0.0

            # 获取活跃玩家数
            active_players = self.cur.execute(
                "SELECT COUNT(DISTINCT tg_id) FROM blackjack_stats"
            ).fetchone()[0]

            # 获取今日游戏局数
            today = datetime.now(settings.TZ).strftime("%Y-%m-%d")
            today_games = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats WHERE date = ?", (today,)
            ).fetchone()[0]

            # 获取本周游戏局数
            week_ago = (datetime.now(settings.TZ) - timedelta(days=7)).strftime("%Y-%m-%d")
            week_games = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats WHERE date >= ?", (week_ago,)
            ).fetchone()[0]

            return {
                "total_games": total_games,
                "total_wins": total_wins,
                "total_losses": total_losses,
                "total_pushes": total_pushes,
                "total_blackjacks": total_blackjacks,
                "total_bet_amount": total_bet_amount,
                "total_payout_amount": total_payout_amount,
                "house_edge": round(house_edge, 2),
                "active_players": active_players,
                "today_games": today_games,
                "week_games": week_games,
            }
        except Exception as e:
            logger.error(f"Error getting blackjack stats: {e}")
            return {
                "total_games": 0,
                "total_wins": 0,
                "total_losses": 0,
                "total_pushes": 0,
                "total_blackjacks": 0,
                "total_bet_amount": 0.0,
                "total_payout_amount": 0.0,
                "house_edge": 0.0,
                "active_players": 0,
                "today_games": 0,
                "week_games": 0,
            }

    def get_user_blackjack_stats(self, tg_id: int):
        """获取用户个人21点统计数据"""
        try:
            # 使用UTC+8北京时间
            today = datetime.now(settings.TZ).strftime("%Y-%m-%d")
            week_ago = (datetime.now(settings.TZ) - timedelta(days=7)).strftime("%Y-%m-%d")

            # 获取用户今日游戏次数
            today_games = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats WHERE tg_id = ? AND date = ?",
                (tg_id, today),
            ).fetchone()[0]

            # 获取用户总游戏次数
            total_games = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats WHERE tg_id = ?", (tg_id,)
            ).fetchone()[0]

            # 获取用户本周游戏次数
            week_games = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats WHERE tg_id = ? AND date >= ?",
                (tg_id, week_ago),
            ).fetchone()[0]

            # 获取用户总胜场
            total_wins = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats WHERE tg_id = ? AND result IN ('win', 'blackjack', 'dealer_bust')",
                (tg_id,),
            ).fetchone()[0]

            # 获取用户今日胜场
            today_wins = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats WHERE tg_id = ? AND date = ? AND result IN ('win', 'blackjack', 'dealer_bust')",
                (tg_id, today),
            ).fetchone()[0]

            # 获取用户本周胜场
            week_wins = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats WHERE tg_id = ? AND date >= ? AND result IN ('win', 'blackjack', 'dealer_bust')",
                (tg_id, week_ago),
            ).fetchone()[0]

            # 获取用户总败场
            total_losses = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats WHERE tg_id = ? AND result IN ('lose', 'bust')",
                (tg_id,),
            ).fetchone()[0]

            # 获取用户平局次数
            total_pushes = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats WHERE tg_id = ? AND result = 'push'",
                (tg_id,),
            ).fetchone()[0]

            # 获取用户黑杰克次数
            total_blackjacks = self.cur.execute(
                "SELECT COUNT(*) FROM blackjack_stats WHERE tg_id = ? AND result = 'blackjack'",
                (tg_id,),
            ).fetchone()[0]

            # 获取用户总积分变化
            total_credits_change_result = self.cur.execute(
                "SELECT SUM(credits_change) FROM blackjack_stats WHERE tg_id = ?", (tg_id,)
            ).fetchone()
            total_credits_change = (
                float(total_credits_change_result[0])
                if total_credits_change_result[0]
                else 0.0
            )

            # 获取用户今日积分变化
            today_credits_change_result = self.cur.execute(
                "SELECT SUM(credits_change) FROM blackjack_stats WHERE tg_id = ? AND date = ?",
                (tg_id, today),
            ).fetchone()
            today_credits_change = (
                float(today_credits_change_result[0])
                if today_credits_change_result[0]
                else 0.0
            )

            # 获取用户本周积分变化
            week_credits_change_result = self.cur.execute(
                "SELECT SUM(credits_change) FROM blackjack_stats WHERE tg_id = ? AND date >= ?",
                (tg_id, week_ago),
            ).fetchone()
            week_credits_change = (
                float(week_credits_change_result[0])
                if week_credits_change_result[0]
                else 0.0
            )

            # 获取用户胜率
            win_rate = (total_wins / total_games * 100) if total_games > 0 else 0.0

            # 获取用户最近5次游戏记录
            recent_games = self.cur.execute(
                """SELECT bet_amount, result, credits_change, player_score, dealer_score, date, timestamp
                   FROM blackjack_stats
                   WHERE tg_id = ?
                   ORDER BY timestamp DESC
                   LIMIT 5""",
                (tg_id,),
            ).fetchall()

            recent_games_list = []
            for game in recent_games:
                recent_games_list.append(
                    {
                        "bet_amount": game[0],
                        "result": game[1],
                        "credits_change": game[2],
                        "player_score": game[3],
                        "dealer_score": game[4],
                        "date": game[5],
                        "timestamp": game[6],
                    }
                )

            return {
                "today_games": today_games,
                "total_games": total_games,
                "week_games": week_games,
                "today_wins": today_wins,
                "week_wins": week_wins,
                "total_wins": total_wins,
                "total_losses": total_losses,
                "total_pushes": total_pushes,
                "total_blackjacks": total_blackjacks,
                "win_rate": round(win_rate, 2),
                "total_credits_change": total_credits_change,
                "today_credits_change": today_credits_change,
                "week_credits_change": week_credits_change,
                "recent_games": recent_games_list,
            }
        except Exception as e:
            logger.error(f"Error getting user blackjack stats: {e}")
            return {
                "today_games": 0,
                "total_games": 0,
                "week_games": 0,
                "today_wins": 0,
                "week_wins": 0,
                "total_wins": 0,
                "total_losses": 0,
                "total_pushes": 0,
                "total_blackjacks": 0,
                "win_rate": 0.0,
                "total_credits_change": 0.0,
                "today_credits_change": 0.0,
                "week_credits_change": 0.0,
                "recent_games": [],
            }

    def close(self):
        self.cur.close()
        self.con.close()

    def get_expired_premium_users(self):
        """获取所有 Premium 已过期的用户"""

        expired_users = []
        current_time = datetime.now(settings.TZ).isoformat()

        # 检查 Plex 用户
        plex_users = self.cur.execute(
            "SELECT tg_id, plex_username, premium_expiry_time, plex_line FROM user WHERE is_premium=1 AND premium_expiry_time IS NOT NULL AND premium_expiry_time < ?",
            (current_time,),
        ).fetchall()

        for user in plex_users:
            expired_users.append(
                {
                    "tg_id": user[0],
                    "username": user[1],
                    "service": "plex",
                    "expiry_time": user[2],
                    "line": user[3],
                }
            )

        # 检查 Emby 用户
        emby_users = self.cur.execute(
            "SELECT tg_id, emby_username, premium_expiry_time, emby_line FROM emby_user WHERE is_premium=1 AND premium_expiry_time IS NOT NULL AND premium_expiry_time < ?",
            (current_time,),
        ).fetchall()

        for user in emby_users:
            expired_users.append(
                {
                    "tg_id": user[0],
                    "username": user[1],
                    "service": "emby",
                    "expiry_time": user[2],
                    "line": user[3],
                }
            )

        return expired_users

    def update_expired_premium_status(self):
        """批量更新已过期的 Premium 用户状态"""

        current_time = datetime.now(settings.TZ).isoformat()

        # 更新 Plex 用户 - 清空过期时间
        plex_result = self.cur.execute(
            "UPDATE user SET is_premium=0, premium_expiry_time=NULL WHERE is_premium=1 AND premium_expiry_time IS NOT NULL AND premium_expiry_time < ?",
            (current_time,),
        )

        # 更新 Emby 用户 - 清空过期时间
        emby_result = self.cur.execute(
            "UPDATE emby_user SET is_premium=0, premium_expiry_time=NULL WHERE is_premium=1 AND premium_expiry_time IS NOT NULL AND premium_expiry_time < ?",
            (current_time,),
        )

        self.con.commit()

        total_updated = plex_result.rowcount + emby_result.rowcount
        return total_updated

    def get_premium_users_expiring_soon(self, days: int = 3):
        """获取即将过期的 Premium 用户（默认3天内）"""

        current_time = datetime.now(settings.TZ)
        warning_time = (current_time + timedelta(days=days)).isoformat()
        current_time_str = current_time.isoformat()

        expiring_users = []

        # 检查 Plex 用户
        plex_users = self.cur.execute(
            "SELECT tg_id, plex_username, premium_expiry_time FROM user WHERE is_premium=1 AND premium_expiry_time IS NOT NULL AND premium_expiry_time > ? AND premium_expiry_time <= ?",
            (current_time_str, warning_time),
        ).fetchall()

        for user in plex_users:
            expiry_dt = datetime.fromisoformat(user[2]).astimezone(settings.TZ)
            days_remaining = (expiry_dt - current_time).days
            expiring_users.append(
                {
                    "tg_id": user[0],
                    "username": user[1],
                    "service": "plex",
                    "expiry_time": user[2],
                    "days_remaining": days_remaining,
                }
            )

        # 检查 Emby 用户
        emby_users = self.cur.execute(
            "SELECT tg_id, emby_username, premium_expiry_time FROM emby_user WHERE is_premium=1 AND premium_expiry_time IS NOT NULL AND premium_expiry_time > ? AND premium_expiry_time <= ?",
            (current_time_str, warning_time),
        ).fetchall()

        for user in emby_users:
            expiry_dt = datetime.fromisoformat(user[2]).astimezone(settings.TZ)
            days_remaining = (expiry_dt - current_time).days
            expiring_users.append(
                {
                    "tg_id": user[0],
                    "username": user[1],
                    "service": "emby",
                    "expiry_time": user[2],
                    "days_remaining": days_remaining,
                }
            )

        return expiring_users

    def get_premium_statistics(self):
        """获取 Premium 用户统计信息"""
        try:
            current_time = datetime.now(settings.TZ).isoformat()

            # 总 Premium 用户数（包含 Plex 和 Emby，去重）
            total_premium_users_query = """
            SELECT COUNT(DISTINCT tg_id) FROM (
                SELECT tg_id FROM user WHERE is_premium=1 AND tg_id IS NOT NULL
                UNION
                SELECT tg_id FROM emby_user WHERE is_premium=1 AND tg_id IS NOT NULL
            )
            """
            total_premium_users = self.cur.execute(
                total_premium_users_query
            ).fetchone()[0]

            # 活跃 Premium 用户数（未过期的）
            active_premium_users_query = """
            SELECT COUNT(DISTINCT tg_id) FROM (
                SELECT tg_id FROM user 
                WHERE is_premium=1 AND tg_id IS NOT NULL 
                AND (premium_expiry_time IS NULL OR premium_expiry_time > ?)
                UNION
                SELECT tg_id FROM emby_user 
                WHERE is_premium=1 AND tg_id IS NOT NULL 
                AND (premium_expiry_time IS NULL OR premium_expiry_time > ?)
            )
            """
            active_premium_users = self.cur.execute(
                active_premium_users_query, (current_time, current_time)
            ).fetchone()[0]

            # Premium Plex 用户数（未过期的）
            premium_plex_users = self.cur.execute(
                """SELECT COUNT(*) FROM user 
                WHERE is_premium=1 
                AND (premium_expiry_time IS NULL OR premium_expiry_time > ?)""",
                (current_time,),
            ).fetchone()[0]

            # Premium Emby 用户数（未过期的）
            premium_emby_users = self.cur.execute(
                """SELECT COUNT(*) FROM emby_user 
                WHERE is_premium=1 
                AND (premium_expiry_time IS NULL OR premium_expiry_time > ?)""",
                (current_time,),
            ).fetchone()[0]

            return {
                "total_premium_users": total_premium_users,
                "active_premium_users": active_premium_users,
                "premium_plex_users": premium_plex_users,
                "premium_emby_users": premium_emby_users,
            }

        except Exception as e:
            logger.error(f"Error getting premium statistics: {e}")
            return {
                "total_premium_users": 0,
                "active_premium_users": 0,
                "premium_plex_users": 0,
                "premium_emby_users": 0,
            }

    def create_line_traffic_entry(
        self,
        line: str,
        send_bytes: int,
        service: str,
        username: str,
        user_id: str,
        timestamp: str,
    ):
        try:
            self.cur.execute(
                "INSERT INTO line_traffic_stats (line, send_bytes, service, username, user_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (line, send_bytes, service, username, user_id, timestamp),
            )
        except Exception as e:
            logger.error(f"Error creating line traffic entry: {e}")
            return False
        else:
            self.con.commit()
            return True

    def get_premium_line_traffic_statistics(self):
        """获取Premium线路流量统计信息"""
        try:
            now = datetime.now(settings.TZ)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=now.weekday())
            month_start = today_start.replace(day=1)

            # 动态从数据库获取所有实际使用的线路（排除估算数据）
            get_lines_query = """
            SELECT DISTINCT line
            FROM line_traffic_stats
            WHERE line NOT LIKE '%estimate%'
            ORDER BY line
            """
            lines_result = self.cur.execute(get_lines_query).fetchall()
            premium_lines = [row[0] for row in lines_result]

            # 如果数据库中没有线路，回退到配置文件
            if not premium_lines:
                premium_lines = settings.PREMIUM_STREAM_BACKEND

            line_stats = []

            for line in premium_lines:
                # 计算今日流量
                today_traffic_query = """
                SELECT COALESCE(SUM(send_bytes), 0) as traffic
                FROM line_traffic_stats 
                WHERE line = ? AND timestamp >= ?
                """
                today_traffic = self.cur.execute(
                    today_traffic_query, (line, today_start.isoformat())
                ).fetchone()[0]

                # 计算本周流量
                week_traffic_query = """
                SELECT COALESCE(SUM(send_bytes), 0) as traffic
                FROM line_traffic_stats 
                WHERE line = ? AND timestamp >= ?
                """
                week_traffic = self.cur.execute(
                    week_traffic_query, (line, week_start.isoformat())
                ).fetchone()[0]

                # 计算本月流量
                month_traffic_query = """
                SELECT COALESCE(SUM(send_bytes), 0) as traffic
                FROM line_traffic_stats 
                WHERE line = ? AND timestamp >= ?
                """
                month_traffic = self.cur.execute(
                    month_traffic_query, (line, month_start.isoformat())
                ).fetchone()[0]

                # 获取当前线路流量排名前五的用户（基于本月数据）
                top_users_query = """
                SELECT username, SUM(send_bytes) as total_traffic
                FROM line_traffic_stats 
                WHERE line = ? AND timestamp >= ?
                GROUP BY username 
                ORDER BY total_traffic DESC 
                LIMIT 5
                """
                top_users_result = self.cur.execute(
                    top_users_query, (line, month_start.isoformat())
                ).fetchall()

                top_users = []
                for user_data in top_users_result:
                    username, traffic = user_data
                    top_users.append({"username": username, "traffic": traffic})

                line_stats.append(
                    {
                        "line": line,
                        "today_traffic": today_traffic,
                        "week_traffic": week_traffic,
                        "month_traffic": month_traffic,
                        "top_users": top_users,
                    }
                )

            return line_stats

        except Exception as e:
            logger.error(f"Error getting premium line traffic statistics: {e}")
            return []

    def get_all_lines_traffic_statistics(self):
        """获取所有线路（普通+高级）的流量统计信息"""
        try:
            now = datetime.now(settings.TZ)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=now.weekday())
            month_start = today_start.replace(day=1)

            # 动态从数据库获取所有实际使用的线路（排除估算数据）
            get_lines_query = """
            SELECT DISTINCT line
            FROM line_traffic_stats
            WHERE line NOT LIKE '%estimate%'
            ORDER BY line
            """
            lines_result = self.cur.execute(get_lines_query).fetchall()
            all_lines = [row[0] for row in lines_result]

            # 如果数据库中没有线路，回退到配置文件
            if not all_lines:
                all_lines = list(set(settings.STREAM_BACKEND + settings.PREMIUM_STREAM_BACKEND))

            line_stats = []

            for line in all_lines:
                # 判断线路类型
                is_premium = line in settings.PREMIUM_STREAM_BACKEND

                # 计算今日流量
                today_traffic_query = """
                SELECT COALESCE(SUM(send_bytes), 0) as traffic
                FROM line_traffic_stats
                WHERE line = ? AND timestamp >= ?
                """
                today_traffic = self.cur.execute(
                    today_traffic_query, (line, today_start.isoformat())
                ).fetchone()[0]

                # 计算本周流量
                week_traffic_query = """
                SELECT COALESCE(SUM(send_bytes), 0) as traffic
                FROM line_traffic_stats
                WHERE line = ? AND timestamp >= ?
                """
                week_traffic = self.cur.execute(
                    week_traffic_query, (line, week_start.isoformat())
                ).fetchone()[0]

                # 计算本月流量
                month_traffic_query = """
                SELECT COALESCE(SUM(send_bytes), 0) as traffic
                FROM line_traffic_stats
                WHERE line = ? AND timestamp >= ?
                """
                month_traffic = self.cur.execute(
                    month_traffic_query, (line, month_start.isoformat())
                ).fetchone()[0]

                # 获取当前线路使用人数（今日活跃用户）
                active_users_query = """
                SELECT COUNT(DISTINCT username)
                FROM line_traffic_stats
                WHERE line = ? AND timestamp >= ?
                """
                active_users = self.cur.execute(
                    active_users_query, (line, today_start.isoformat())
                ).fetchone()[0]

                # 获取当前线路流量排名前五的用户（基于本月数据）
                top_users_query = """
                SELECT username, SUM(send_bytes) as total_traffic
                FROM line_traffic_stats
                WHERE line = ? AND timestamp >= ?
                GROUP BY username
                ORDER BY total_traffic DESC
                LIMIT 5
                """
                top_users_result = self.cur.execute(
                    top_users_query, (line, month_start.isoformat())
                ).fetchall()

                top_users = []
                for user_data in top_users_result:
                    username, traffic = user_data
                    top_users.append({"username": username, "traffic": traffic})

                line_stats.append(
                    {
                        "line": line,
                        "is_premium": is_premium,
                        "today_traffic": today_traffic,
                        "week_traffic": week_traffic,
                        "month_traffic": month_traffic,
                        "active_users": active_users,
                        "top_users": top_users,
                    }
                )

            return line_stats

        except Exception as e:
            logger.error(f"Error getting all lines traffic statistics: {e}")
            return []

    def get_line_switch_history(self, tg_id: int = None, limit: int = 10):
        """获取线路切换历史记录

        Args:
            tg_id: 用户TG ID，如果为None则获取所有用户的记录
            limit: 返回记录数量限制
        """
        try:
            # 创建线路切换历史表（如果不存在）
            self.cur.execute("""
                CREATE TABLE IF NOT EXISTS line_switch_history(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    service TEXT NOT NULL,
                    old_line TEXT,
                    new_line TEXT,
                    switch_time INTEGER NOT NULL,
                    switch_date TEXT NOT NULL
                )
            """)
            self.con.commit()

            # 查询历史记录
            if tg_id:
                query = """
                SELECT username, service, old_line, new_line, switch_time, switch_date
                FROM line_switch_history
                WHERE tg_id = ?
                ORDER BY switch_time DESC
                LIMIT ?
                """
                result = self.cur.execute(query, (tg_id, limit)).fetchall()
            else:
                query = """
                SELECT username, service, old_line, new_line, switch_time, switch_date
                FROM line_switch_history
                ORDER BY switch_time DESC
                LIMIT ?
                """
                result = self.cur.execute(query, (limit,)).fetchall()

            history = []
            for row in result:
                history.append({
                    "username": row[0],
                    "service": row[1],
                    "old_line": row[2],
                    "new_line": row[3],
                    "switch_time": row[4],
                    "switch_date": row[5],
                })

            return history

        except Exception as e:
            logger.error(f"Error getting line switch history: {e}")
            return []

    def record_line_switch(self, tg_id: int, username: str, service: str, old_line: str, new_line: str):
        """记录线路切换操作

        Args:
            tg_id: 用户TG ID
            username: 用户名
            service: 服务类型 (emby/plex)
            old_line: 旧线路
            new_line: 新线路
        """
        try:
            switch_time = int(time.time())
            switch_date = datetime.now(settings.TZ).strftime("%Y-%m-%d %H:%M:%S")

            self.cur.execute("""
                INSERT INTO line_switch_history
                (tg_id, username, service, old_line, new_line, switch_time, switch_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (tg_id, username, service, old_line, new_line, switch_time, switch_date))

            self.con.commit()
            return True

        except Exception as e:
            logger.error(f"Error recording line switch: {e}")
            return False

    def get_user_daily_traffic(
        self,
        username: str,
        service: str = None,
        date: datetime = None,
        premium_only: bool = False,
    ):
        """获取用户指定日期的流量消耗，默认为今日

        Args:
            username: 用户名
            service: 服务类型 (plex/emby)
            date: 指定日期，默认为今日
            premium_only: 是否只统计 premium 线路流量，默认为 False
        """
        try:
            # 如果未指定日期，使用今日
            if date is None:
                date = datetime.now(settings.TZ)

            # 确保日期对象包含时区信息
            if date.tzinfo is None:
                date = date.replace(tzinfo=settings.TZ)
            else:
                date = date.astimezone(settings.TZ)

            # 计算指定日期的开始和结束时间
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)

            # 判断查询日期是否为当月
            now = datetime.now(settings.TZ)
            current_month_start = now.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )

            if date >= current_month_start:
                # 当月数据，从 line_traffic_stats 表查询
                # 构建查询条件
                base_conditions = "LOWER(username) = ? AND service = ? AND timestamp >= ? AND timestamp <= ?"
                params = [
                    username.lower(),
                    service,
                    day_start.isoformat(),
                    day_end.isoformat(),
                ]

                # 如果只统计 premium 线路
                if premium_only:
                    premium_lines = settings.PREMIUM_STREAM_BACKEND
                    if premium_lines:
                        # 构建线路过滤条件
                        line_conditions = " OR ".join(
                            ["line = ?" for _ in premium_lines]
                        )
                        base_conditions += f" AND ({line_conditions})"
                        params.extend(premium_lines)
                    else:
                        # 如果没有配置 premium 线路，返回 0
                        return 0

                # 查询特定服务的指定日期流量
                query = f"""
                SELECT COALESCE(SUM(send_bytes), 0) as traffic
                FROM line_traffic_stats 
                WHERE {base_conditions}
                """
                result = self.cur.execute(query, params).fetchone()
                return result[0] if result else 0
            else:
                # 历史月份数据，从 line_traffic_monthly_stats 表查询
                # 注意：月度表只有月度总计，无法精确到天，返回 0
                logger.warning(
                    f"无法获取历史日期 {date.strftime('%Y-%m-%d')} 的精确日流量数据"
                )
                return 0

        except Exception as e:
            logger.error(f"Error getting user daily traffic for {username}: {e}")
            return 0

    def get_traffic_statistics(self):
        """获取全面的流量统计信息，包括今日/本周/本月，按服务类型和线路分类"""
        try:
            now = datetime.now(settings.TZ)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=now.weekday())
            month_start = today_start.replace(day=1)

            # 获取所有服务类型的流量统计
            periods = [
                ("today", today_start.isoformat()),
                ("week", week_start.isoformat()),
                ("month", month_start.isoformat()),
            ]

            result = {}

            for period_name, start_time in periods:
                # 查询按服务类型分组的流量统计
                service_query = """
                SELECT 
                    service,
                    COALESCE(SUM(send_bytes), 0) as total_traffic
                FROM line_traffic_stats 
                WHERE timestamp >= ?
                GROUP BY service
                """
                service_results = self.cur.execute(
                    service_query, (start_time,)
                ).fetchall()

                # 查询按线路分组的流量统计
                line_query = """
                SELECT 
                    line,
                    COALESCE(SUM(send_bytes), 0) as total_traffic
                FROM line_traffic_stats 
                WHERE timestamp >= ?
                GROUP BY line
                ORDER BY total_traffic DESC
                """
                line_results = self.cur.execute(line_query, (start_time,)).fetchall()

                # 计算总流量
                total_query = """
                SELECT COALESCE(SUM(send_bytes), 0) as total_traffic
                FROM line_traffic_stats 
                WHERE timestamp >= ?
                """
                total_traffic = self.cur.execute(total_query, (start_time,)).fetchone()[
                    0
                ]

                # 构建期间数据
                period_data = {
                    "total": total_traffic,
                    "emby": 0,
                    "plex": 0,
                    "lines": [],
                }

                for service, traffic in service_results:
                    if service.lower() == "emby":
                        period_data["emby"] = traffic
                    elif service.lower() == "plex":
                        period_data["plex"] = traffic

                # 添加线路数据
                for line, traffic in line_results:
                    # 排除自定义线路
                    for _line in (
                        settings.STREAM_BACKEND + settings.PREMIUM_STREAM_BACKEND
                    ):
                        if line.lower() in _line.lower():
                            # 只统计已知的线路
                            period_data["lines"].append(
                                {"line": line, "traffic": traffic}
                            )
                            break

                result[period_name] = period_data

            return result

        except Exception as e:
            logger.error(f"Error getting comprehensive traffic statistics: {e}")
            return {
                "today": {"total": 0, "emby": 0, "plex": 0, "lines": []},
                "week": {"total": 0, "emby": 0, "plex": 0, "lines": []},
                "month": {"total": 0, "emby": 0, "plex": 0, "lines": []},
            }

    def get_plex_traffic_rank(self, start_date=None, end_date=None):
        """获取 Plex 流量排行榜

        Args:
            start_date: 开始日期 (datetime对象)，默认为今日开始
            end_date: 结束日期 (datetime对象)，默认为今日结束
        """
        try:
            # 使用北京时间
            now_beijing = datetime.now(settings.TZ)

            if start_date is None:
                # 默认为今日开始
                start_date = now_beijing.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            else:
                # 确保是当月的日期
                current_month_start = now_beijing.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                if start_date < current_month_start:
                    start_date = current_month_start

            if end_date is None:
                # 默认为今日结束
                end_date = now_beijing.replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
            else:
                # 确保不超过今日
                today_end = now_beijing.replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
                if end_date > today_end:
                    end_date = today_end

            # 仅当月数据，从 line_traffic_stats 表查询
            query = """
            SELECT u.plex_username, lts.user_id, SUM(lts.send_bytes) as total_traffic,
                   COALESCE(u.is_premium, 0) as is_premium,
                   u.tg_id
            FROM line_traffic_stats lts
            LEFT JOIN user u ON LOWER(lts.username) = LOWER(u.plex_username)
            WHERE lts.service = 'plex' 
                AND lts.timestamp >= ?
                AND lts.timestamp <= ?
                AND lts.username IS NOT NULL
                AND lts.username != ''
            GROUP BY LOWER(lts.username), lts.user_id, u.is_premium, u.tg_id
            ORDER BY total_traffic DESC
            LIMIT 50
            """

            result = self.cur.execute(
                query, (start_date.isoformat(), end_date.isoformat())
            ).fetchall()
            return result

        except Exception as e:
            logger.error(f"Error getting Plex traffic rank: {e}")
            return []

    def get_emby_traffic_rank(self, start_date=None, end_date=None):
        """获取 Emby 流量排行榜

        Args:
            start_date: 开始日期 (datetime对象)，默认为今日开始
            end_date: 结束日期 (datetime对象)，默认为今日结束
        """
        try:
            # 使用北京时间
            now_beijing = datetime.now(settings.TZ)

            if start_date is None:
                # 默认为今日开始
                start_date = now_beijing.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            else:
                # 确保是当月的日期
                current_month_start = now_beijing.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                if start_date < current_month_start:
                    start_date = current_month_start

            if end_date is None:
                # 默认为今日结束
                end_date = now_beijing.replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
            else:
                # 确保不超过今日
                today_end = now_beijing.replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
                if end_date > today_end:
                    end_date = today_end

            query = """
            SELECT eu.emby_username, lts.user_id, SUM(lts.send_bytes) as total_traffic,
                   COALESCE(eu.is_premium, 0) as is_premium,
                   eu.tg_id
            FROM line_traffic_stats lts
            LEFT JOIN emby_user eu ON LOWER(lts.username) = LOWER(eu.emby_username)
            WHERE lts.service = 'emby' 
                AND lts.timestamp >= ?
                AND lts.timestamp <= ?
                AND lts.username IS NOT NULL
                AND lts.username != ''
            GROUP BY LOWER(lts.username), lts.user_id, eu.is_premium, eu.tg_id
            ORDER BY total_traffic DESC
            LIMIT 50
            """

            result = self.cur.execute(
                query, (start_date.isoformat(), end_date.isoformat())
            ).fetchall()
            return result

        except Exception as e:
            logger.error(f"Error getting Emby traffic rank: {e}")
            return []

    def aggregate_monthly_traffic_data(
        self, target_month: str = None
    ) -> tuple[bool, str]:
        """
        聚合指定月份的流量数据到月度统计表

        Args:
            target_month: 目标月份，格式为 'YYYY-MM'，如果为 None 则处理上个月的数据

        Returns:
            tuple: (是否成功, 消息)
        """
        try:
            from datetime import datetime, timedelta

            if target_month is None:
                # 默认处理上个月的数据
                now = datetime.now(settings.TZ)
                if now.day == 1:
                    # 如果是每月1号，处理上个月数据
                    last_month = now.replace(day=1) - timedelta(days=1)
                    target_month = last_month.strftime("%Y-%m")
                else:
                    return False, "只能在每月1号自动处理上个月数据"

            logger.info(f"开始聚合 {target_month} 的流量数据")

            # 验证月份格式
            try:
                datetime.strptime(target_month, "%Y-%m")
            except ValueError:
                return False, f"月份格式错误: {target_month}，应为 YYYY-MM 格式"

            # 检查是否已经聚合过该月份的数据
            existing_check = self.cur.execute(
                "SELECT COUNT(*) FROM line_traffic_monthly_stats WHERE year_month = ?",
                (target_month,),
            ).fetchone()[0]

            if existing_check > 0:
                return False, f"月份 {target_month} 的数据已经聚合过，跳过处理"

            # 计算目标月份的开始和结束时间
            month_start = datetime.strptime(f"{target_month}-01", "%Y-%m-%d").replace(
                tzinfo=settings.TZ
            )
            if month_start.month == 12:
                next_month_start = month_start.replace(
                    year=month_start.year + 1, month=1
                )
            else:
                next_month_start = month_start.replace(month=month_start.month + 1)

            month_start_str = month_start.isoformat()
            next_month_start_str = next_month_start.isoformat()

            # 聚合查询：按 line, service, username 分组求和
            aggregation_query = """
            SELECT 
                line,
                service,
                username,
                user_id,
                SUM(send_bytes) as total_bytes,
                COUNT(*) as record_count
            FROM line_traffic_stats 
            WHERE timestamp >= ? AND timestamp < ?
            GROUP BY line, service, username
            HAVING SUM(send_bytes) > 0
            ORDER BY total_bytes DESC
            """

            aggregated_data = self.cur.execute(
                aggregation_query, (month_start_str, next_month_start_str)
            ).fetchall()

            if not aggregated_data:
                return False, f"月份 {target_month} 没有找到需要聚合的数据"

            # 插入聚合数据到月度统计表
            current_time = datetime.now(settings.TZ).isoformat()
            insert_count = 0

            for record in aggregated_data:
                line, service, username, user_id, total_bytes, record_count = record

                try:
                    self.cur.execute(
                        """
                        INSERT INTO line_traffic_monthly_stats 
                        (line, service, username, user_id, year_month, total_bytes, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            line,
                            service,
                            username,
                            user_id,
                            target_month,
                            total_bytes,
                            current_time,
                        ),
                    )
                    insert_count += 1
                except Exception as e:
                    logger.warning(f"插入月度聚合数据失败: {e}, 数据: {record}")

            self.con.commit()

            logger.info(
                f"成功聚合 {target_month} 月份数据: {len(aggregated_data)} 个用户组合，插入 {insert_count} 条记录"
            )
            return (
                True,
                f"成功聚合 {target_month} 月份数据: 处理了 {len(aggregated_data)} 个用户组合",
            )

        except Exception as e:
            logger.error(f"聚合月度流量数据失败: {e}")
            return False, f"聚合月度流量数据失败: {str(e)}"

    def cleanup_monthly_traffic_data(self, target_month: str) -> tuple[bool, str]:
        """
        清理已聚合月份的原始流量数据

        Args:
            target_month: 目标月份，格式为 'YYYY-MM'

        Returns:
            tuple: (是否成功, 消息)
        """
        try:
            # 验证月份格式
            try:
                datetime.strptime(target_month, "%Y-%m")
            except ValueError:
                return False, f"月份格式错误: {target_month}，应为 YYYY-MM 格式"

            # 检查月度聚合数据是否存在
            monthly_check = self.cur.execute(
                "SELECT COUNT(*) FROM line_traffic_monthly_stats WHERE year_month = ?",
                (target_month,),
            ).fetchone()[0]

            if monthly_check == 0:
                return False, f"月份 {target_month} 的聚合数据不存在，不能清理原始数据"

            # 计算目标月份的时间范围
            month_start = datetime.strptime(f"{target_month}-01", "%Y-%m-%d").replace(
                tzinfo=settings.TZ
            )
            if month_start.month == 12:
                next_month_start = month_start.replace(
                    year=month_start.year + 1, month=1
                )
            else:
                next_month_start = month_start.replace(month=month_start.month + 1)

            month_start_str = month_start.isoformat()
            next_month_start_str = next_month_start.isoformat()

            # 统计要删除的记录数
            delete_count_query = """
            SELECT COUNT(*) FROM line_traffic_stats
            WHERE timestamp >= ? AND timestamp < ?
            """
            delete_count = self.cur.execute(
                delete_count_query, (month_start_str, next_month_start_str)
            ).fetchone()[0]

            if delete_count == 0:
                return True, f"月份 {target_month} 没有需要清理的原始数据"

            # 删除原始数据
            delete_query = """
            DELETE FROM line_traffic_stats
            WHERE timestamp >= ? AND timestamp < ?
            """

            self.cur.execute(delete_query, (month_start_str, next_month_start_str))
            self.con.commit()

            logger.info(f"已清理 {target_month} 月份的 {delete_count} 条原始流量数据")
            return True, f"成功清理 {target_month} 月份的 {delete_count} 条原始流量数据"

        except Exception as e:
            logger.error(f"清理月度流量数据失败: {e}")
            return False, f"清理月度流量数据失败: {str(e)}"

    def add_group_member_left_record(
        self, tg_id: int, left_time: int, group_id: int = None
    ) -> bool:
        """记录群组成员离开"""
        try:
            self.cur.execute(
                "INSERT OR REPLACE INTO group_member_left_status (tg_id, left_time, group_id, is_processed) VALUES (?, ?, ?, 0)",
                (tg_id, left_time, group_id),
            )
            self.con.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding group member left record: {e}")
            return False

    def get_unprocessed_left_members(self, time_threshold: int) -> List[dict]:
        """获取离开超过指定时间且未处理的成员

        Args:
            time_threshold: 时间阈值（时间戳），早于此时间的离开记录将被返回

        Returns:
            List[dict]: 符合条件的成员列表
        """
        try:
            results = self.cur.execute(
                """SELECT tg_id, left_time, group_id
                   FROM group_member_left_status
                   WHERE is_processed = 0 AND left_time <= ?""",
                (time_threshold,),
            ).fetchall()

            members = []
            for result in results:
                members.append(
                    {
                        "tg_id": result[0],
                        "left_time": result[1],
                        "group_id": result[2],
                    }
                )
            return members
        except Exception as e:
            logger.error(f"Error getting unprocessed left members: {e}")
            return []

    def mark_left_member_as_processed(self, tg_id: int) -> bool:
        """标记离开成员为已处理"""
        try:
            self.cur.execute(
                "UPDATE group_member_left_status SET is_processed = 1 WHERE tg_id = ?",
                (tg_id,),
            )
            self.con.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking left member as processed: {e}")
            return False

    def mark_left_member_warning_sent(self, tg_id: int) -> bool:
        """标记已向离开成员发送警告"""
        try:
            current_time = int(__import__('time').time())
            self.cur.execute(
                "UPDATE group_member_left_status SET warning_sent = 1, last_warning_time = ? WHERE tg_id = ?",
                (current_time, tg_id),
            )
            self.con.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking warning sent for left member: {e}")
            return False

    def remove_group_member_left_record(self, tg_id: int) -> bool:
        """删除群组成员离开记录（用于成员重新加入群组的情况）"""
        try:
            self.cur.execute(
                "DELETE FROM group_member_left_status WHERE tg_id = ?", (tg_id,)
            )
            self.con.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing group member left record: {e}")
            return False

    def delete_plex_user(self, tg_id: int) -> bool:
        """删除Plex用户记录"""
        try:
            self.cur.execute("DELETE FROM user WHERE tg_id = ?", (tg_id,))
            self.con.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting plex user: {e}")
            return False

    def delete_emby_user(self, tg_id: int) -> bool:
        """删除Emby用户记录"""
        try:
            self.cur.execute("DELETE FROM emby_user WHERE tg_id = ?", (tg_id,))
            self.con.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting emby user: {e}")
            return False

    def health_check(self) -> bool:
        """检查数据库连接是否健康"""
        try:
            self._ensure_connection()
            self._local.con.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return False

    def get_db_info(self) -> dict:
        """获取数据库信息"""
        from pathlib import Path
        try:
            self._ensure_connection()
            cursor = self.cur
            
            # 获取数据库大小
            db_path = Path(self.db_path)
            db_size = db_path.stat().st_size if db_path.exists() else 0
            
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


    # ─────────────────── 债务管理（换绑欠积分）───────────────────

    def get_debt_since(self, tg_id: int):
        row = self.cur.execute(
            "SELECT debt_since FROM statistics WHERE tg_id = ?", (tg_id,)
        ).fetchone()
        return row[0] if row else None

    def set_debt_since(self, tg_id: int, timestamp: int) -> None:
        if self.get_debt_since(tg_id) is None:
            self.cur.execute(
                "UPDATE statistics SET debt_since = ? WHERE tg_id = ?", (timestamp, tg_id)
            )
            self.con.commit()

    def clear_debt_since(self, tg_id: int) -> None:
        self.cur.execute(
            "UPDATE statistics SET debt_since = NULL WHERE tg_id = ?", (tg_id,)
        )
        self.con.commit()

    def get_all_debtors(self):
        return self.cur.execute(
            "SELECT tg_id, credits, debt_since FROM statistics WHERE credits < 0 AND debt_since IS NOT NULL"
        ).fetchall()

    # ─────────────────── 签到 ───────────────────

    def get_checkin_today(self, tg_id: int, today: str):
        return self.cur.execute(
            "SELECT * FROM checkin_stats WHERE tg_id = ? AND checkin_date = ?",
            (tg_id, today),
        ).fetchone()

    def get_checkin_last(self, tg_id: int):
        return self.cur.execute(
            "SELECT * FROM checkin_stats WHERE tg_id = ? ORDER BY checkin_date DESC LIMIT 1",
            (tg_id,),
        ).fetchone()

    def add_checkin(self, tg_id: int, checkin_date: str, streak: int, month: str, credits_earned: float) -> bool:
        try:
            self.cur.execute(
                "INSERT INTO checkin_stats (tg_id, checkin_date, streak, month, credits_earned) VALUES (?, ?, ?, ?, ?)",
                (tg_id, checkin_date, streak, month, credits_earned),
            )
            self.con.commit()
            return True
        except Exception as e:
            logger.error(f"添加签到记录失败: {e}")
            return False

    def get_checkin_month_count(self, tg_id: int, month: str) -> int:
        row = self.cur.execute(
            "SELECT COUNT(*) FROM checkin_stats WHERE tg_id = ? AND month = ?",
            (tg_id, month),
        ).fetchone()
        return row[0] if row else 0

    def get_checkin_total_count(self, tg_id: int) -> int:
        row = self.cur.execute(
            "SELECT COUNT(*) FROM checkin_stats WHERE tg_id = ?",
            (tg_id,),
        ).fetchone()
        return row[0] if row else 0

    def get_checkin_total_rank(self, tg_id: int):
        current = self.cur.execute(
            """
            SELECT COUNT(*) AS total_days, MAX(id) AS last_checkin_id
            FROM checkin_stats
            WHERE tg_id = ?
            """,
            (tg_id,),
        ).fetchone()
        total_count = current["total_days"] if current else 0
        last_checkin_id = current["last_checkin_id"] if current else None
        if total_count <= 0 or last_checkin_id is None:
            return None

        row = self.cur.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT tg_id, COUNT(*) AS total_days, MAX(id) AS last_checkin_id
                FROM checkin_stats
                GROUP BY tg_id
                HAVING COUNT(*) > ?
                    OR (COUNT(*) = ? AND MAX(id) < ?)
            )
            """,
            (total_count, total_count, last_checkin_id),
        ).fetchone()
        higher_count = row[0] if row else 0
        return higher_count + 1

    def get_checkin_monthly_leaderboard(self, month: str):
        return self.cur.execute(
            """SELECT tg_id, COUNT(*) as days, SUM(credits_earned) as total_credits, MAX(id) as last_checkin_id
               FROM checkin_stats WHERE month = ?
               GROUP BY tg_id
               ORDER BY days DESC, last_checkin_id ASC, tg_id ASC
               LIMIT 20""",
            (month,),
        ).fetchall()

    def get_checkin_status(self, tg_id: int, today: str) -> dict:
        today_row = self.get_checkin_today(tg_id, today)
        last_row = self.get_checkin_last(tg_id)
        month = today[:7]
        month_count = self.get_checkin_month_count(tg_id, month)
        total_count = self.get_checkin_total_count(tg_id)
        total_rank = self.get_checkin_total_rank(tg_id)
        streak = 0
        today_date = date.fromisoformat(today)
        yesterday = today_date - timedelta(days=1)
        if today_row:
            streak = today_row["streak"]
        elif last_row:
            last_date = date.fromisoformat(last_row["checkin_date"])
            if last_date == yesterday:
                streak = last_row["streak"]
        return {
            "checked_in_today": today_row is not None,
            "streak": streak,
            "month_count": month_count,
            "total_count": total_count,
            "total_rank": total_rank,
            "last_checkin": last_row["checkin_date"] if last_row else None,
        }

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
