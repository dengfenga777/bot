"""Redis 线路同步工具。"""

from __future__ import annotations

from typing import Optional

from app.log import logger
from app.redis_client import Redis


class RedisLineSync:
    """同步 Plex / Emby 线路到 Redis，供 Nginx/Lua 动态路由读取。"""

    def __init__(self, db: int = 0):
        self.db = db
        self._redis_wrapper = None

    def _get_client(self):
        if self._redis_wrapper is None:
            self._redis_wrapper = Redis(db=self.db)
        return self._redis_wrapper.get_connection()

    def _sync_key(self, key: str, target: Optional[str]) -> bool:
        try:
            client = self._get_client()
            if target:
                client.set(key, str(target).strip())
            else:
                client.delete(key)
            return True
        except Exception as exc:
            self._redis_wrapper = None
            logger.error("Redis 线路同步失败 key=%s target=%s error=%s", key, target, exc)
            return False

    def sync_plex_line(self, plex_username: Optional[str], target: Optional[str]) -> bool:
        if not plex_username:
            logger.warning("同步 Plex 线路时缺少用户名")
            return False
        return self._sync_key(f"plex_email:{plex_username}", target)

    def sync_emby_line(self, emby_id: Optional[str], target: Optional[str]) -> bool:
        if not emby_id:
            logger.warning("同步 Emby 线路时缺少 emby_id")
            return False
        return self._sync_key(f"emby_line:{emby_id}", target)


redis_line_sync = RedisLineSync()
