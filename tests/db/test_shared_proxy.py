#!/usr/bin/env python3
"""共享反代功能测试"""

import socket

import pytest

from app.shared_proxy import (
    SharedProxyValidationError,
    build_shared_proxy_profile,
    normalize_shared_proxy_domain,
    _resolve_bound_line_target,
    sync_user_media_routes,
)


def test_normalize_shared_proxy_domain_rejects_reserved_host(monkeypatch):
    monkeypatch.setattr("app.shared_proxy.settings.PLEX_BASE_URL", "https://plex.example.com", raising=False)
    monkeypatch.setattr("app.shared_proxy.settings.EMBY_BASE_URL", "https://emby.example.com", raising=False)
    monkeypatch.setattr("app.shared_proxy.settings.EMBY_ENTRY_URL", "https://emby.example.com", raising=False)
    monkeypatch.setattr("app.shared_proxy.settings.WEBAPP_URL", "https://webapp.example.com", raising=False)
    monkeypatch.setattr("app.shared_proxy.settings.PLEX_ORIGIN_HOST", "plex-origin.example.com", raising=False)
    monkeypatch.setattr("app.shared_proxy.settings.EMBY_ORIGIN_HOST", "emby-origin.example.com", raising=False)
    monkeypatch.setattr("app.shared_proxy.settings.STREAM_BACKEND", ["stream.example.com"], raising=False)
    monkeypatch.setattr("app.shared_proxy.settings.PREMIUM_STREAM_BACKEND", ["premium.example.com"], raising=False)

    with pytest.raises(SharedProxyValidationError, match="官方线路冲突"):
        normalize_shared_proxy_domain("https://plex.example.com")

    with pytest.raises(SharedProxyValidationError, match="官方线路冲突"):
        normalize_shared_proxy_domain("https://plex-origin.example.com")


def test_normalize_shared_proxy_domain_accepts_https_domain(monkeypatch, mock_settings):
    def fake_getaddrinfo(host, port, type=None):  # noqa: A002
        assert host == "proxy.example.net"
        assert port == 443
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    host, port = normalize_shared_proxy_domain("proxy.example.net")

    assert host == "proxy.example.net"
    assert port == 443


def test_shared_proxy_profile_save_and_enable(test_db):
    assert test_db.save_shared_proxy_profile(
        tg_id=10001,
        domain="proxy.example.net",
        port=443,
        verification_status="verified",
        verified_at=1234567890,
        last_error=None,
    )

    row = test_db.get_shared_proxy_profile(10001)
    profile = build_shared_proxy_profile(row)

    assert profile["domain"] == "proxy.example.net"
    assert profile["enabled"] is False
    assert profile["verification_status"] == "verified"

    assert test_db.set_shared_proxy_enabled(
        10001,
        True,
        verification_status="verified",
        verified_at=1234567899,
        last_error=None,
    )

    enabled_profile = build_shared_proxy_profile(test_db.get_shared_proxy_profile(10001))
    assert enabled_profile["enabled"] is True
    assert enabled_profile["verified_at"] == 1234567899


def test_sync_user_media_routes_prefers_shared_proxy(test_db, monkeypatch):
    tg_id = 123456
    test_db.add_plex_user(
        plex_id=9001,
        tg_id=tg_id,
        plex_email="plex@example.com",
        plex_username="plexuser",
        plex_line="hk.stream.example.com",
    )
    test_db.add_emby_user(
        "embyuser",
        emby_id="emby-9001",
        tg_id=tg_id,
        emby_line="sg.stream.example.com",
    )
    test_db.save_shared_proxy_profile(
        tg_id=tg_id,
        domain="proxy.example.net",
        port=443,
        enabled=True,
        verification_status="verified",
        verified_at=1234567890,
        last_error=None,
    )

    calls = []

    def fake_sync_plex_line(username, target):
        calls.append(("plex", username, target))
        return True

    def fake_sync_emby_line(emby_id, target):
        calls.append(("emby", emby_id, target))
        return True

    monkeypatch.setattr("app.shared_proxy.redis_line_sync.sync_plex_line", fake_sync_plex_line)
    monkeypatch.setattr("app.shared_proxy.redis_line_sync.sync_emby_line", fake_sync_emby_line)

    success, errors = sync_user_media_routes(test_db, tg_id)

    assert success is True
    assert errors == []
    assert ("plex", "plexuser", "proxy.example.net:443") in calls
    assert ("emby", "emby-9001", "proxy.example.net:443") in calls


def test_transfer_tg_binding_assets_moves_shared_proxy(test_db):
    old_tg_id = 60001
    new_tg_id = 60002
    plex_id = 9901

    test_db.add_plex_user(
        plex_id=plex_id,
        tg_id=old_tg_id,
        plex_email="old@example.com",
        plex_username="olduser",
    )
    test_db.save_shared_proxy_profile(
        tg_id=old_tg_id,
        domain="proxy.example.net",
        port=443,
        enabled=True,
        verification_status="verified",
        verified_at=1234567890,
        last_error=None,
    )

    test_db.transfer_tg_binding_assets(
        old_tg_id,
        new_tg_id,
        fee=0,
        plex_id=plex_id,
    )

    assert test_db.get_shared_proxy_profile(old_tg_id) is None

    profile = build_shared_proxy_profile(test_db.get_shared_proxy_profile(new_tg_id))
    assert profile["domain"] == "proxy.example.net"
    assert profile["enabled"] is True


def test_resolve_bound_line_target_rejects_legacy_alias(monkeypatch):
    monkeypatch.setattr("app.shared_proxy.LineMapping.get_url", lambda value: "")

    assert _resolve_bound_line_target("Infinity") is None
    assert _resolve_bound_line_target("1") is None


def test_resolve_bound_line_target_accepts_domain(monkeypatch):
    monkeypatch.setattr("app.shared_proxy.LineMapping.get_url", lambda value: "")

    assert _resolve_bound_line_target("hk.stream.example.com") == "hk.stream.example.com:443"
