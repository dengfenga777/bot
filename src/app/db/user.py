#!/usr/bin/env python3
"""数据库用户模块 - 用户相关操作"""

import sqlite3
from typing import TYPE_CHECKING, Optional

from app.log import logger

if TYPE_CHECKING:
    from app.db._types import HasDBConnection


class UserMixin:
    """用户相关的数据库操作

    注意: 此 Mixin 需要与 DBBase 一起使用，DBBase 提供 con 和 cur 属性。
    """

    # 类型声明 - 由 DBBase 提供实现
    con: sqlite3.Connection
    cur: sqlite3.Cursor

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
    ) -> bool:
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
            self.con.commit()
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"添加 Plex 用户时数据重复: {e}")
            return False
        except sqlite3.OperationalError as e:
            logger.error(f"添加 Plex 用户时数据库操作错误: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"添加 Plex 用户时数据库错误: {e}")
            return False

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
            self.con.commit()
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"添加 Emby 用户时数据重复: {e}")
            return False
        except sqlite3.OperationalError as e:
            logger.error(f"添加 Emby 用户时数据库操作错误: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"添加 Emby 用户时数据库错误: {e}")
            return False

    def add_overseerr_user(self, user_id: int, user_email: str, tg_id: int) -> bool:
        try:
            self.cur.execute(
                "INSERT INTO overseerr VALUES (?, ?, ?)",
                (user_id, user_email, tg_id),
            )
            self.con.commit()
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"添加 Overseerr 用户时数据重复: {e}")
            return False
        except sqlite3.OperationalError as e:
            logger.error(f"添加 Overseerr 用户时数据库操作错误: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"添加 Overseerr 用户时数据库错误: {e}")
            return False

    def add_user_data(self, tg_id: int, credits: float = 0, donation: float = 0) -> bool:
        try:
            self.cur.execute(
                "INSERT INTO statistics (tg_id, donation, credits) VALUES (?, ?, ?)",
                (tg_id, donation, credits),
            )
            self.con.commit()
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"添加用户统计数据时数据重复: {e}")
            return False
        except sqlite3.OperationalError as e:
            logger.error(f"添加用户统计数据时数据库操作错误: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"添加用户统计数据时数据库错误: {e}")
            return False

    def update_user_tg_id(self, tg_id: int, plex_id: Optional[int] = None, emby_id: Optional[str] = None) -> bool:
        try:
            if plex_id:
                self.cur.execute(
                    "UPDATE user SET tg_id=? WHERE plex_id=?", (tg_id, plex_id)
                )
            if emby_id:
                self.cur.execute(
                    "UPDATE emby_user SET tg_id=? WHERE emby_id=?", (tg_id, emby_id)
                )
            self.con.commit()
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"更新用户 TG ID 时数据完整性错误: {e}")
            return False
        except sqlite3.OperationalError as e:
            logger.error(f"更新用户 TG ID 时数据库操作错误: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"更新用户 TG ID 时数据库错误: {e}")
            return False

    def get_plex_users_num(self) -> int:
        rslt = self.cur.execute("SELECT count(*) FROM user")
        return rslt.fetchone()[0]

    def get_emby_users_num(self) -> int:
        rslt = self.cur.execute("SELECT count(*) FROM emby_user")
        return rslt.fetchone()[0]

    def get_plex_info_by_tg_id(self, tg_id: int) -> Optional[sqlite3.Row]:
        rslt = self.cur.execute("SELECT * FROM user WHERE tg_id = ?", (tg_id,))
        return rslt.fetchone()

    def get_plex_info_by_plex_id(self, plex_id: int) -> Optional[sqlite3.Row]:
        rslt = self.cur.execute("SELECT * FROM user WHERE plex_id = ?", (plex_id,))
        return rslt.fetchone()

    def get_plex_info_by_plex_username(self, plex_username: str) -> Optional[sqlite3.Row]:
        rslt = self.cur.execute(
            "SELECT * FROM user WHERE plex_username = ?", (plex_username,)
        )
        return rslt.fetchone()

    def get_plex_info_by_plex_email(self, plex_email: str) -> Optional[sqlite3.Row]:
        rslt = self.cur.execute(
            "SELECT * FROM user WHERE LOWER(plex_email) = ?", (plex_email.lower(),)
        )
        return rslt.fetchone()

    def get_emby_info_by_emby_username(self, username: str) -> Optional[sqlite3.Row]:
        return self.cur.execute(
            "SELECT * FROM emby_user WHERE LOWER(emby_username) = ?",
            (username.lower(),),
        ).fetchone()

    def get_emby_info_by_tg_id(self, tg_id: int) -> Optional[sqlite3.Row]:
        return self.cur.execute(
            "SELECT * FROM emby_user WHERE tg_id = ?", (tg_id,)
        ).fetchone()

    def get_emby_info_by_emby_id(self, emby_id: str) -> Optional[sqlite3.Row]:
        return self.cur.execute(
            "SELECT * FROM emby_user WHERE emby_id = ?", (emby_id,)
        ).fetchone()

    def get_overseerr_info_by_tg_id(self, tg_id: int) -> Optional[sqlite3.Row]:
        return self.cur.execute(
            "SELECT * FROM overseerr WHERE tg_id = ?", (tg_id,)
        ).fetchone()

    def get_overseerr_info_by_email(self, email: str) -> Optional[sqlite3.Row]:
        return self.cur.execute(
            "SELECT * FROM overseerr WHERE user_email = ?", (email,)
        ).fetchone()

    def delete_plex_user(self, tg_id: int) -> bool:
        try:
            self.cur.execute("DELETE FROM user WHERE tg_id = ?", (tg_id,))
            self.con.commit()
            return True
        except sqlite3.OperationalError as e:
            logger.error(f"删除 Plex 用户时数据库操作错误: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"删除 Plex 用户时数据库错误: {e}")
            return False

    def delete_emby_user(self, tg_id: int) -> bool:
        try:
            self.cur.execute("DELETE FROM emby_user WHERE tg_id = ?", (tg_id,))
            self.con.commit()
            return True
        except sqlite3.OperationalError as e:
            logger.error(f"删除 Emby 用户时数据库操作错误: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"删除 Emby 用户时数据库错误: {e}")
            return False
