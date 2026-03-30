#!/usr/bin/env python3
"""数据库邀请码模块 - 邀请码相关操作"""

import sqlite3
from typing import List, Optional, Tuple

from app.invitation_utils import get_invitation_timestamps
from app.log import logger


class InvitationMixin:
    """邀请码相关的数据库操作

    注意: 此 Mixin 需要与 DBBase 一起使用，DBBase 提供 con 和 cur 属性。
    """

    # 类型声明 - 由 DBBase 提供实现
    con: sqlite3.Connection
    cur: sqlite3.Cursor

    def invitation_code_exists(self, code: str) -> bool:
        result = self.cur.execute(
            "SELECT 1 FROM invitation WHERE code=? LIMIT 1", (code,)
        ).fetchone()
        return bool(result)

    def add_invitation_code(
        self,
        code: str,
        owner: int,
        is_used: int = 0,
        used_by: Optional[int] = None,
        created_at: Optional[int] = None,
        expires_at: Optional[int] = None,
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
            self.con.commit()
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"添加邀请码时数据重复: {e}")
            return False
        except sqlite3.OperationalError as e:
            logger.error(f"添加邀请码时数据库操作错误: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"添加邀请码时数据库错误: {e}")
            return False

    def update_invitation_status(self, code: str, used_by: int) -> bool:
        try:
            self.cur.execute(
                "UPDATE invitation SET is_used=?,used_by=? WHERE code=?",
                (1, used_by, code),
            )
            self.con.commit()
            return True
        except sqlite3.OperationalError as e:
            logger.error(f"更新邀请码状态时数据库操作错误: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"更新邀请码状态时数据库错误: {e}")
            return False

    def verify_invitation_code_is_used(self, code: str) -> Optional[sqlite3.Row]:
        rslt = self.cur.execute(
            "SELECT is_used, owner, expires_at FROM invitation WHERE code=?", (code,)
        )
        return rslt.fetchone()

    def get_invitation_code_by_owner(self, tg_id: int, is_available: bool = True) -> List[sqlite3.Row]:
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
        return rslt.fetchall()

    def get_invited_count_by_owner(self, tg_id: int) -> int:
        try:
            rslt = self.cur.execute(
                "SELECT count(*) FROM invitation WHERE owner=? and is_used=1", (tg_id,)
            )
            res = rslt.fetchone()
            return res[0] if res else 0
        except sqlite3.OperationalError as e:
            logger.error(f"获取邀请数量时数据库操作错误: {e}")
            return 0
        except sqlite3.DatabaseError as e:
            logger.error(f"获取邀请数量时数据库错误: {e}")
            return 0
