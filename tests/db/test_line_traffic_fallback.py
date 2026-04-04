#!/usr/bin/env python3
"""流量排行榜兜底采集测试"""

from app import update_db


def test_parse_nginx_access_log_line_extracts_expected_fields():
    line = (
        '1.1.1.1 - - [04/Apr/2026:10:00:00 +0800] '
        '"GET /emby/videos/69755/hls1/main/0.ts?PlaySessionId=session-1 HTTP/2.0" '
        "206 123456"
    )

    parsed = update_db._parse_nginx_access_log_line(line, service="emby")

    assert parsed == {
        "@timestamp": "2026-04-04T10:00:00+08:00",
        "remote_addr": "1.1.1.1",
        "request_method": "GET",
        "request_uri": "/emby/videos/69755/hls1/main/0.ts?PlaySessionId=session-1",
        "status": 206,
        "bytes_sent": 123456,
        "service": "emby",
    }


def test_is_plex_stream_request_only_accepts_media_transfer_paths():
    assert update_db._is_plex_stream_request(
        "/library/parts/1/1700000000/file.mkv?X-Plex-Token=test-token"
    )
    assert update_db._is_plex_stream_request(
        "/video/:/transcode/universal/session/abc/base/index.m3u8?X-Plex-Token=test-token"
    )
    assert not update_db._is_plex_stream_request(
        "/myplex/account?X-Plex-Token=test-token"
    )
    assert not update_db._is_plex_stream_request(
        "/photo/:/transcode?X-Plex-Token=test-token"
    )


def test_extract_plex_metadata_id_from_transcode_request():
    assert update_db._extract_plex_metadata_id(
        "/video/:/transcode/universal/decision"
        "?path=%2Flibrary%2Fmetadata%2F37999&X-Plex-Token=test-token"
    ) == "37999"


async def test_update_line_traffic_stats_uses_nginx_fallback_when_redis_is_empty(
    monkeypatch,
):
    class DummyDB:
        def close(self):
            self.closed = True

    db = DummyDB()
    saved_state = {}
    processed_payloads = []

    async def fake_process_traffic_log_entry(_db, log_data, *, emby_play_sessions):
        processed_payloads.append((log_data, dict(emby_play_sessions)))
        return True

    monkeypatch.setattr(update_db.settings, "NGINX_TRAFFIC_FALLBACK_ENABLED", True)
    monkeypatch.setattr(
        update_db.stream_traffic_cache.redis_client,
        "lpop",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(update_db, "DB", lambda: db)
    monkeypatch.setattr(
        update_db,
        "_collect_fallback_traffic_logs",
        lambda max_records: (
            [
                {
                    "@timestamp": "2026-04-04T10:00:00+08:00",
                    "service": "plex",
                    "request_uri": "/library/parts/1/file.mkv?X-Plex-Token=test-token",
                    "status": 206,
                    "bytes_sent": 4096,
                }
            ],
            {
                "files": {"plex_json": {"offset": 128}},
                "emby_play_sessions": {},
            },
        ),
    )
    monkeypatch.setattr(
        update_db,
        "_process_traffic_log_entry",
        fake_process_traffic_log_entry,
    )
    monkeypatch.setattr(
        update_db,
        "_save_nginx_traffic_state",
        lambda state: saved_state.update(state),
    )

    processed = await update_db.update_line_traffic_stats(count=10)

    assert processed == 1
    assert len(processed_payloads) == 1
    assert processed_payloads[0][0]["service"] == "plex"
    assert saved_state["files"]["plex_json"]["offset"] == 128
    assert saved_state["emby_play_sessions"] == {}


async def test_process_traffic_log_entry_skips_non_stream_plex_request(monkeypatch, test_db):
    async def fake_resolve_plex_identity(_db, request_uri):
        raise AssertionError("non-stream plex request should not resolve identity")

    monkeypatch.setattr(update_db, "_resolve_plex_identity", fake_resolve_plex_identity)

    log_data = {
        "@timestamp": "2026-04-04T10:00:00+08:00",
        "service": "plex",
        "request_uri": "/myplex/account?X-Plex-Token=test-token",
        "status": 200,
        "bytes_sent": 4096,
    }

    assert not await update_db._process_traffic_log_entry(
        test_db,
        log_data,
        emby_play_sessions={},
    )

    count = test_db.cur.execute("SELECT COUNT(*) FROM line_traffic_stats").fetchone()[0]
    assert count == 0


async def test_resolve_plex_identity_uses_plex_tv_account_api(monkeypatch, test_db):
    test_db.add_plex_user(
        plex_id="plex-user-1",
        plex_username="plexuser",
        plex_email="plexuser@example.com",
        credits=0,
        all_lib=0,
        watched_time=0,
    )

    captured = {}

    class DummyResponse:
        status_code = 200
        text = '<user username="plexuser" />'

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return DummyResponse()

    monkeypatch.setattr(update_db.httpx, "get", fake_get)

    username, user_id = await update_db._resolve_plex_identity(
        test_db,
        "/library/parts/1/file.mkv?X-Plex-Token=test-token",
    )

    assert username == "plexuser"
    assert user_id == "plex-user-1"
    assert captured["url"] == "https://plex.tv/users/account.xml"
    assert captured["kwargs"]["params"] == {"X-Plex-Token": "test-token"}
    assert captured["kwargs"]["follow_redirects"] is True


async def test_resolve_plex_identity_falls_back_to_tautulli_history(monkeypatch, test_db):
    test_db.add_plex_user(
        plex_id="plex-user-2",
        plex_username="TT3301",
        plex_email="tt3301@example.com",
        credits=0,
        all_lib=0,
        watched_time=0,
    )
    update_db._plex_tautulli_history_cache.clear()

    class DummyResponse:
        status_code = 422
        text = ""

    def fake_get(url, **kwargs):
        return DummyResponse()

    class DummyTautulli:
        def _call_api(self, cmd, payload, method="GET"):
            assert cmd == "get_history"
            assert payload["start_date"] == "2026-04-03"
            return {
                "data": [
                    {
                        "ip_address": "152.69.207.125",
                        "rating_key": 3929,
                        "user": "TT3301",
                        "player": "SenPlayer",
                        "product": "SenPlayer",
                        "started": 1775223000,
                        "stopped": 1775223600,
                    }
                ]
            }

    monkeypatch.setattr(update_db.httpx, "get", fake_get)
    monkeypatch.setattr(update_db, "Tautulli", DummyTautulli)

    username, user_id = await update_db._resolve_plex_identity(
        test_db,
        "/library/parts/4145/1766579473/file.mp4?X-Plex-Token=test-token",
        timestamp="2026-04-03T21:30:43+08:00",
        remote_addr="152.69.207.125",
        user_agent="SenPlayer/5.9.3",
    )

    assert username == "TT3301"
    assert user_id == "plex-user-2"


async def test_process_traffic_log_entry_reuses_emby_play_session(monkeypatch, test_db):
    test_db.add_emby_user(
        emby_username="embyuser",
        emby_id="emby-user-1",
    )

    async def fake_get_emby_username_from_api_key(self, api_key):
        assert api_key == "emby-api-key"
        return "embyuser"

    monkeypatch.setattr(
        update_db.Emby,
        "get_emby_username_from_api_key",
        fake_get_emby_username_from_api_key,
    )

    play_sessions = {}
    session_log = {
        "@timestamp": "2026-04-04T10:00:00+08:00",
        "service": "emby",
        "request_uri": (
            "/emby/videos/69755/master.m3u8"
            "?PlaySessionId=session-1&api_key=emby-api-key"
        ),
        "status": 200,
        "bytes_sent": 2048,
    }
    segment_log = {
        "@timestamp": "2026-04-04T10:00:05+08:00",
        "service": "emby",
        "request_uri": "/emby/videos/69755/hls1/main/0.ts?PlaySessionId=session-1",
        "status": 206,
        "bytes_sent": 1048576,
    }

    assert await update_db._process_traffic_log_entry(
        test_db,
        session_log,
        emby_play_sessions=play_sessions,
    )
    assert await update_db._process_traffic_log_entry(
        test_db,
        segment_log,
        emby_play_sessions=play_sessions,
    )

    rows = [
        tuple(row)
        for row in test_db.cur.execute(
            """
            SELECT line, service, username, user_id, send_bytes
            FROM line_traffic_stats
            ORDER BY id
            """
        ).fetchall()
    ]

    assert rows == [
        ("http-emby", "emby", "embyuser", "emby-user-1", 2048),
        ("http-emby", "emby", "embyuser", "emby-user-1", 1048576),
    ]
    assert play_sessions["session-1"]["username"] == "embyuser"
    assert play_sessions["session-1"]["user_id"] == "emby-user-1"
