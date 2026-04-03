#!/usr/bin/env python3
"""共享反代线路工具。

提供：
- 用户自定义反代域名的规范化与校验
- 共享反代配置的统一展示结构
- 根据用户当前配置同步 Plex / Emby 的实际路由
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
import ssl
from typing import Any, Optional
from urllib.parse import urlparse

from app.config import settings
from app.log import logger
from app.line_mapping import LineMapping
from app.redis_sync import redis_line_sync


DEFAULT_SHARED_PROXY_PORT = 443


class SharedProxyValidationError(ValueError):
    """共享反代域名校验错误。"""


def _build_parse_target(raw_target: str) -> str:
    target = str(raw_target or "").strip()
    if not target:
        raise SharedProxyValidationError("反代域名不能为空")
    if "://" not in target:
        target = f"https://{target}"
    return target


def _normalize_host(host: Optional[str]) -> str:
    normalized = (host or "").strip().rstrip(".").lower()
    if not normalized:
        raise SharedProxyValidationError("无法识别有效的域名")
    return normalized


def _validate_host_common(host: str) -> None:
    if host in {"localhost", "localhost.localdomain"}:
        raise SharedProxyValidationError("不允许使用本机地址作为反代域名")
    if " " in host:
        raise SharedProxyValidationError("域名中不能包含空格")


def _extract_host_port(
    raw_target: str,
    *,
    allow_ip: bool,
    require_https: bool,
) -> tuple[str, int]:
    target = _build_parse_target(raw_target)
    parsed = urlparse(target)

    if parsed.scheme not in {"https", "http"}:
        raise SharedProxyValidationError("仅支持 http 或 https 协议")
    if require_https and parsed.scheme != "https":
        raise SharedProxyValidationError("共享反代域名仅支持 https")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise SharedProxyValidationError("请只填写域名或域名加端口，不要包含路径或参数")
    if parsed.username or parsed.password:
        raise SharedProxyValidationError("反代域名中不允许包含账号信息")

    host = _normalize_host(parsed.hostname)
    _validate_host_common(host)

    try:
        ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False

    if is_ip and not allow_ip:
        raise SharedProxyValidationError("共享反代请填写域名，不支持直接填写 IP")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port <= 0 or port > 65535:
        raise SharedProxyValidationError("端口范围无效")

    return host, port


def extract_upstream_host(target: Optional[str]) -> Optional[str]:
    """从 host[:port] 形式的目标中提取 host。"""
    if not target:
        return None
    host, _ = _extract_host_port(target, allow_ip=True, require_https=False)
    return host


def build_upstream_target(
    raw_target: Optional[str],
    *,
    allow_ip: bool = True,
    require_https: bool = False,
) -> Optional[str]:
    """规范化任意路由目标为 host:port。"""
    if raw_target is None:
        return None

    text = str(raw_target).strip()
    if not text:
        return None

    host, port = _extract_host_port(
        text,
        allow_ip=allow_ip,
        require_https=require_https,
    )
    return f"{host}:{port}"


def _resolve_bound_line_target(raw_target: Optional[str]) -> Optional[str]:
    """将已绑定的线路值解析为可用于网关的 host:port。

    历史数据里可能保存的是类似 `Infinity`、`1` 这样的显示别名。
    这类值在当前环境下无法直接作为上游地址使用，应该回退到默认入口，
    否则会被错误地写入 Redis，导致媒体网关返回 502。
    """
    if raw_target is None:
        return None

    text = str(raw_target).strip()
    if not text:
        return None

    mapped_target = LineMapping.get_url(text) or text
    candidate = str(mapped_target).strip()
    if not candidate:
        return None

    if "://" in candidate or ":" in candidate:
        return build_upstream_target(candidate, allow_ip=True)

    try:
        ipaddress.ip_address(candidate)
        return build_upstream_target(candidate, allow_ip=True)
    except ValueError:
        pass

    if "." not in candidate:
        logger.info("忽略无法解析的历史线路别名: %s", text)
        return None

    return build_upstream_target(candidate, allow_ip=True)


def _iter_reserved_hosts() -> set[str]:
    reserved = set()
    urls = [
        settings.PLEX_BASE_URL,
        settings.EMBY_BASE_URL,
        settings.EMBY_ENTRY_URL,
        settings.WEBAPP_URL,
    ]
    for url in urls:
        if not url:
            continue
        try:
            host, _ = _extract_host_port(url, allow_ip=True, require_https=False)
            reserved.add(host)
        except SharedProxyValidationError:
            continue

    for line in list(settings.STREAM_BACKEND) + list(settings.PREMIUM_STREAM_BACKEND):
        if not line:
            continue
        try:
            host, _ = _extract_host_port(line, allow_ip=True, require_https=False)
            reserved.add(host)
        except SharedProxyValidationError:
            continue

    return reserved


def normalize_shared_proxy_domain(raw_target: str) -> tuple[str, int]:
    """规范化并校验用户填写的共享反代域名。"""
    host, port = _extract_host_port(
        raw_target,
        allow_ip=False,
        require_https=True,
    )

    if host in _iter_reserved_hosts():
        raise SharedProxyValidationError("该域名与系统官方线路冲突，请填写你自己的反代域名")

    try:
        addr_info = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SharedProxyValidationError("域名解析失败，请检查 DNS 是否已生效") from exc

    public_addresses = []
    for item in addr_info:
        ip_str = item[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if any(
            [
                ip_obj.is_loopback,
                ip_obj.is_private,
                ip_obj.is_link_local,
                ip_obj.is_unspecified,
                ip_obj.is_reserved,
                ip_obj.is_multicast,
            ]
        ):
            continue
        public_addresses.append(ip_obj)

    if not public_addresses:
        raise SharedProxyValidationError("反代域名不能解析到内网、本机或保留地址")

    return host, port


async def verify_shared_proxy_target(host: str, port: int) -> tuple[bool, Optional[str]]:
    """验证共享反代域名是否可从服务器访问。"""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                host=host,
                port=port,
                ssl=ssl_context,
                server_hostname=host,
            ),
            timeout=5,
        )
        writer.close()
        await writer.wait_closed()
        return True, None
    except Exception as exc:  # pragma: no cover - 依赖网络环境
        logger.warning("共享反代校验失败 %s:%s, error=%s", host, port, exc)
        return False, f"无法连接到 {host}:{port}，请确认 HTTPS 反代已就绪"


def build_shared_proxy_profile(row: Optional[Any]) -> Optional[dict[str, Any]]:
    """将数据库行转换为前端可直接消费的共享反代配置。"""
    if not row:
        return None

    domain = row["custom_domain"] if "custom_domain" in row.keys() else row[1]
    port = row["custom_port"] if "custom_port" in row.keys() else row[2]
    enabled = bool(row["is_enabled"] if "is_enabled" in row.keys() else row[3])
    verification_status = (
        row["verification_status"]
        if "verification_status" in row.keys()
        else row[4]
    )
    verified_at = row["verified_at"] if "verified_at" in row.keys() else row[5]
    last_error = row["last_error"] if "last_error" in row.keys() else row[6]
    updated_at = row["updated_at"] if "updated_at" in row.keys() else row[8]
    target = f"{domain}:{port}" if domain else None

    return {
        "domain": domain,
        "port": int(port or DEFAULT_SHARED_PROXY_PORT),
        "enabled": enabled,
        "verification_status": verification_status or "unknown",
        "verified_at": verified_at,
        "last_error": last_error,
        "updated_at": updated_at,
        "target": target,
        "url": f"https://{target}" if target else None,
    }


def is_shared_proxy_enabled(profile: Optional[dict[str, Any]]) -> bool:
    return bool(profile and profile.get("enabled") and profile.get("target"))


def sync_user_media_routes(db: Any, tg_id: int) -> tuple[bool, list[str]]:
    """根据用户当前设置同步 Emby / Plex 的实际路由。"""
    errors: list[str] = []

    shared_profile = build_shared_proxy_profile(db.get_shared_proxy_profile(tg_id))
    shared_target = shared_profile.get("target") if is_shared_proxy_enabled(shared_profile) else None

    plex_info = db.get_plex_info_by_tg_id(tg_id)
    if plex_info and plex_info[4]:
        plex_target = shared_target or _resolve_bound_line_target(plex_info[8])
        if not redis_line_sync.sync_plex_line(plex_info[4], plex_target):
            errors.append("Plex")

    emby_info = db.get_emby_info_by_tg_id(tg_id)
    if emby_info and emby_info[1]:
        emby_target = shared_target or _resolve_bound_line_target(emby_info[7])
        if not redis_line_sync.sync_emby_line(emby_info[1], emby_target):
            errors.append("Emby")

    return not errors, errors
