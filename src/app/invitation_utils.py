#!/usr/bin/env python3
"""邀请码生成与有效期工具。"""

from __future__ import annotations

import secrets
from time import time
from typing import Callable

INVITATION_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
INVITATION_CODE_LENGTH = 8
INVITATION_EXPIRE_DAYS = 3
INVITATION_EXPIRE_SECONDS = INVITATION_EXPIRE_DAYS * 24 * 60 * 60


def generate_unique_invitation_code(
    code_exists: Callable[[str], bool],
    length: int = INVITATION_CODE_LENGTH,
    max_attempts: int = 32,
) -> str:
    """生成短邀请码，并通过回调确保唯一。"""
    for _ in range(max_attempts):
        code = "".join(
            secrets.choice(INVITATION_CODE_ALPHABET) for _ in range(length)
        )
        if not code_exists(code):
            return code
    raise RuntimeError("邀请码生成失败，请稍后重试")


def get_invitation_timestamps(now_ts: int | None = None) -> tuple[int, int]:
    """返回邀请码创建时间和过期时间戳。"""
    created_at = int(now_ts or time())
    return created_at, created_at + INVITATION_EXPIRE_SECONDS


def is_invitation_expired(expires_at: int | None, now_ts: int | None = None) -> bool:
    """判断邀请码是否已过期。"""
    if expires_at in (None, "", 0):
        return False
    return int(expires_at) <= int(now_ts or time())

