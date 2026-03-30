#!/usr/bin/env python3
"""数据库积分模块 - 积分和统计相关操作"""

import sqlite3
from datetime import date, timedelta
from typing import List, Optional, Tuple

from app.log import logger


class CreditsMixin:
    """积分和统计相关的数据库操作

    注意: 此 Mixin 需要与 DBBase 一起使用，DBBase 提供 con 和 cur 属性。
    """

    # 类型声明 - 由 DBBase 提供实现
    con: sqlite3.Connection
    cur: sqlite3.Cursor

    def get_stats_by_tg_id(self, tg_id: int) -> Optional[sqlite3.Row]:
        return self.cur.execute(
            "SELECT * from statistics WHERE tg_id=?", (tg_id,)
        ).fetchone()

    def update_user_credits(
        self, credits: float, plex_id: Optional[int] = None,
        emby_id: Optional[str] = None, tg_id: Optional[int] = None
    ) -> bool:
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
                logger.error("update_user_credits: 缺少必要参数 (tg_id/plex_id/emby_id)")
                return False
            self.con.commit()
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"更新积分时数据完整性错误: {e}")
            return False
        except sqlite3.OperationalError as e:
            logger.error(f"更新积分时数据库操作错误: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"更新积分时数据库错误: {e}")
            return False

    def get_user_credits(self, tg_id: int) -> Tuple[bool, float | str]:
        """Get user's credits by tg_id"""
        try:
            rslt = self.cur.execute(
                "SELECT credits FROM statistics WHERE tg_id=?", (tg_id,)
            )
            res = rslt.fetchone()
            if res:
                return True, res[0]
            return False, f"未找到用户: {tg_id}"
        except sqlite3.OperationalError as e:
            logger.error(f"获取积分时数据库操作错误: {e}")
            return False, "数据库操作失败"
        except sqlite3.DatabaseError as e:
            logger.error(f"获取积分时数据库错误: {e}")
            return False, "获取积分失败"

    def update_user_donation(self, donation: int, tg_id: int) -> bool:
        """Update user's donation"""
        try:
            self.cur.execute(
                "UPDATE statistics SET donation=? WHERE tg_id=?", (donation, tg_id)
            )
            self.con.commit()
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"更新捐赠金额时数据完整性错误: {e}")
            return False
        except sqlite3.OperationalError as e:
            logger.error(f"更新捐赠金额时数据库操作错误: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"更新捐赠金额时数据库错误: {e}")
            return False

    def get_credits_rank(self) -> List[sqlite3.Row]:
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
        return rslt.fetchall()

    def get_donation_rank(self) -> List[sqlite3.Row]:
        rslt = self.cur.execute(
            "SELECT tg_id,donation FROM statistics ORDER BY donation DESC"
        )
        return rslt.fetchall()

    def get_plex_watched_time_rank(self) -> List[sqlite3.Row]:
        rslt = self.cur.execute(
            "SELECT plex_id,tg_id,plex_username,watched_time,is_premium FROM user ORDER BY watched_time DESC"
        )
        return rslt.fetchall()

    def get_emby_watched_time_rank(self) -> List[sqlite3.Row]:
        return self.cur.execute(
            "SELECT emby_id,emby_username,emby_watched_time,is_premium,tg_id FROM emby_user ORDER BY emby_watched_time DESC"
        ).fetchall()

    # ─────────────────── 债务管理 ───────────────────

    def get_debt_since(self, tg_id: int) -> Optional[int]:
        """返回债务起始时间戳，无债务返回 None"""
        row = self.cur.execute(
            "SELECT debt_since FROM statistics WHERE tg_id = ?", (tg_id,)
        ).fetchone()
        if row:
            return row[0]
        return None

    def set_debt_since(self, tg_id: int, timestamp: int) -> None:
        """设置债务起始时间（仅在尚未设置时写入，避免重置计时器）"""
        existing = self.get_debt_since(tg_id)
        if existing is None:
            self.cur.execute(
                "UPDATE statistics SET debt_since = ? WHERE tg_id = ?", (timestamp, tg_id)
            )
            self.con.commit()

    def clear_debt_since(self, tg_id: int) -> None:
        """清除债务记录"""
        self.cur.execute(
            "UPDATE statistics SET debt_since = NULL WHERE tg_id = ?", (tg_id,)
        )
        self.con.commit()

    def get_all_debtors(self) -> List[sqlite3.Row]:
        """获取所有有债务的用户（credits < 0 且 debt_since 不为 NULL）"""
        return self.cur.execute(
            "SELECT tg_id, credits, debt_since FROM statistics WHERE credits < 0 AND debt_since IS NOT NULL"
        ).fetchall()

    # ─────────────────── 签到 ───────────────────

    def get_checkin_today(self, tg_id: int, today: str) -> Optional[sqlite3.Row]:
        """查询用户今日是否已签到"""
        return self.cur.execute(
            "SELECT * FROM checkin_stats WHERE tg_id = ? AND checkin_date = ?",
            (tg_id, today),
        ).fetchone()

    def get_checkin_last(self, tg_id: int) -> Optional[sqlite3.Row]:
        """查询用户最近一次签到记录"""
        return self.cur.execute(
            "SELECT * FROM checkin_stats WHERE tg_id = ? ORDER BY checkin_date DESC LIMIT 1",
            (tg_id,),
        ).fetchone()

    def add_checkin(self, tg_id: int, checkin_date: str, streak: int, month: str, credits_earned: float) -> bool:
        """记录一次签到"""
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
        """获取用户某月签到天数"""
        row = self.cur.execute(
            "SELECT COUNT(*) FROM checkin_stats WHERE tg_id = ? AND month = ?",
            (tg_id, month),
        ).fetchone()
        return row[0] if row else 0

    def get_checkin_total_count(self, tg_id: int) -> int:
        """获取用户累计签到天数"""
        row = self.cur.execute(
            "SELECT COUNT(*) FROM checkin_stats WHERE tg_id = ?",
            (tg_id,),
        ).fetchone()
        return row[0] if row else 0

    def get_checkin_total_rank(self, tg_id: int):
        """获取用户按累计签到天数统计的总榜排名，同天数按先签到者优先"""
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

    def get_checkin_monthly_leaderboard(self, month: str) -> List[sqlite3.Row]:
        """获取某月签到天数排行，同天数按先签到者优先"""
        return self.cur.execute(
            """SELECT tg_id, COUNT(*) as days, SUM(credits_earned) as total_credits, MAX(id) as last_checkin_id
               FROM checkin_stats WHERE month = ?
               GROUP BY tg_id
               ORDER BY days DESC, last_checkin_id ASC, tg_id ASC
               LIMIT 20""",
            (month,),
        ).fetchall()

    def get_checkin_status(self, tg_id: int, today: str) -> dict:
        """获取用户签到状态汇总"""
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
