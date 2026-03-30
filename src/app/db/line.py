#!/usr/bin/env python3
"""数据库线路模块 - 线路和媒体库相关操作"""

import sqlite3
from typing import List, Optional

from app.log import logger


class LineMixin:
    """线路和媒体库相关的数据库操作

    注意: 此 Mixin 需要与 DBBase 一起使用，DBBase 提供 con 和 cur 属性。
    """

    # 类型声明 - 由 DBBase 提供实现
    con: sqlite3.Connection
    cur: sqlite3.Cursor

    def update_all_lib_flag(
        self,
        all_lib: int,
        unlock_time: Optional[int] = None,
        plex_id: Optional[int] = None,
        emby_id: Optional[str] = None,
        tg_id: Optional[int] = None,
        media_server: str = "plex",
    ) -> bool:
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
                logger.error("更新媒体库权限失败: 请指定正确的媒体服务器类型")
                return False
            self.con.commit()
            return True
        except sqlite3.OperationalError as e:
            logger.error(f"更新媒体库权限时数据库操作错误: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"更新媒体库权限时数据库错误: {e}")
            return False

    def set_emby_line(self, line: str, tg_id: Optional[int] = None, emby_id: Optional[str] = None) -> bool:
        try:
            if tg_id:
                self.cur.execute(
                    "UPDATE emby_user SET emby_line=? WHERE tg_id=?", (line, tg_id)
                )
            elif emby_id:
                self.cur.execute(
                    "UPDATE emby_user SET emby_line=? WHERE emby_id=?", (line, emby_id)
                )
            else:
                logger.error("设置 Emby 线路失败: 需要提供 tg_id 或 emby_id")
                return False
            self.con.commit()
            return True
        except sqlite3.OperationalError as e:
            logger.error(f"设置 Emby 线路时数据库操作错误: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"设置 Emby 线路时数据库错误: {e}")
            return False

    def get_emby_line(self, tg_id: int) -> Optional[str]:
        rslt = self.cur.execute(
            "SELECT emby_line FROM emby_user WHERE tg_id=?", (tg_id,)
        )
        res = rslt.fetchone()
        return res[0] if res else None

    def get_emby_user_with_binded_line(self) -> List[sqlite3.Row]:
        return self.cur.execute(
            "SELECT emby_username, emby_line FROM emby_user WHERE emby_line IS NOT NULL AND emby_line != ''"
        ).fetchall()

    def set_plex_line(self, line: str, tg_id: Optional[int] = None, plex_id: Optional[int] = None) -> bool:
        try:
            if tg_id:
                self.cur.execute(
                    "UPDATE user SET plex_line=? WHERE tg_id=?", (line, tg_id)
                )
            elif plex_id:
                self.cur.execute(
                    "UPDATE user SET plex_line=? WHERE plex_id=?", (line, plex_id)
                )
            else:
                logger.error("设置 Plex 线路失败: 需要提供 tg_id 或 plex_id")
                return False
            self.con.commit()
            return True
        except sqlite3.OperationalError as e:
            logger.error(f"设置 Plex 线路时数据库操作错误: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"设置 Plex 线路时数据库错误: {e}")
            return False

    def get_plex_line(self, tg_id: int) -> Optional[str]:
        rslt = self.cur.execute(
            "SELECT plex_line FROM user WHERE tg_id=?", (tg_id,)
        )
        res = rslt.fetchone()
        return res[0] if res else None

    def get_plex_user_with_binded_line(self) -> List[sqlite3.Row]:
        return self.cur.execute(
            "SELECT plex_username, plex_line FROM user WHERE plex_line IS NOT NULL AND plex_line != ''"
        ).fetchall()

    def record_line_switch(
        self, tg_id: int, username: str, service: str, old_line: str, new_line: str
    ) -> bool:
        """记录用户线路切换历史"""
        import time
        try:
            self.cur.execute(
                """INSERT INTO line_switch_history
                   (tg_id, username, service, old_line, new_line, switch_time)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (tg_id, username, service, old_line, new_line, int(time.time()))
            )
            self.con.commit()
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"记录线路切换时数据重复: {e}")
            return False
        except sqlite3.OperationalError as e:
            logger.error(f"记录线路切换时数据库操作错误: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"记录线路切换时数据库错误: {e}")
            return False

    def get_line_switch_history(self, tg_id: Optional[int] = None, limit: int = 10) -> List[sqlite3.Row]:
        """获取线路切换历史"""
        try:
            if tg_id:
                return self.cur.execute(
                    """SELECT * FROM line_switch_history
                       WHERE tg_id = ?
                       ORDER BY switch_time DESC
                       LIMIT ?""",
                    (tg_id, limit)
                ).fetchall()
            else:
                return self.cur.execute(
                    """SELECT * FROM line_switch_history
                       ORDER BY switch_time DESC
                       LIMIT ?""",
                    (limit,)
                ).fetchall()
        except sqlite3.OperationalError as e:
            logger.error(f"获取线路切换历史时数据库操作错误: {e}")
            return []
        except sqlite3.DatabaseError as e:
            logger.error(f"获取线路切换历史时数据库错误: {e}")
            return []
