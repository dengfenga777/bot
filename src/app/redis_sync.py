"""Stub module - redis line sync removed."""

class _NoOpRedisLineSync:
    def sync_plex_line(self, *args, **kwargs):
        pass
    def sync_emby_line(self, *args, **kwargs):
        pass

redis_line_sync = _NoOpRedisLineSync()
