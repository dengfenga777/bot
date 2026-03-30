#!/usr/bin/env python3
"""邀请码数据库操作测试"""

from time import time

import pytest


class TestInvitationOperations:
    """邀请码相关数据库操作测试"""

    def test_add_invitation_code(self, test_db, sample_user_data):
        """测试添加邀请码"""
        code = "TEST-CODE-001"
        result = test_db.add_invitation_code(
            code=code,
            owner=sample_user_data["tg_id"],
        )
        assert result is True

        # 验证邀请码已添加
        codes = test_db.get_invitation_code_by_owner(sample_user_data["tg_id"])
        assert len(codes) == 1
        assert codes[0] == code

    def test_verify_invitation_code_unused(self, test_db, sample_user_data):
        """测试验证未使用的邀请码"""
        code = "UNUSED-CODE"
        test_db.add_invitation_code(code=code, owner=sample_user_data["tg_id"])

        result = test_db.verify_invitation_code_is_used(code)
        assert result is not None
        assert result[0] == 0  # is_used = 0
        assert result[1] == sample_user_data["tg_id"]  # owner

    def test_update_invitation_status(self, test_db, sample_user_data):
        """测试更新邀请码使用状态"""
        code = "TO-BE-USED"
        used_by_id = 987654321
        test_db.add_invitation_code(code=code, owner=sample_user_data["tg_id"])

        # 更新状态
        result = test_db.update_invitation_status(code, used_by_id)
        assert result is True

        # 验证状态已更新
        status = test_db.verify_invitation_code_is_used(code)
        assert status[0] == 1  # is_used = 1

    def test_get_invitation_codes_available(self, test_db, sample_user_data):
        """测试获取可用邀请码"""
        # 添加两个邀请码
        test_db.add_invitation_code(code="AVAIL-1", owner=sample_user_data["tg_id"])
        test_db.add_invitation_code(code="AVAIL-2", owner=sample_user_data["tg_id"])

        # 使用其中一个
        test_db.update_invitation_status("AVAIL-1", 111111111)

        # 获取可用邀请码
        codes = test_db.get_invitation_code_by_owner(
            sample_user_data["tg_id"], is_available=True
        )
        assert len(codes) == 1
        assert codes[0] == "AVAIL-2"

    def test_get_invitation_codes_all(self, test_db, sample_user_data):
        """测试获取所有邀请码（包括已使用的）"""
        test_db.add_invitation_code(code="ALL-1", owner=sample_user_data["tg_id"])
        test_db.add_invitation_code(code="ALL-2", owner=sample_user_data["tg_id"])
        test_db.update_invitation_status("ALL-1", 111111111)

        codes = test_db.get_invitation_code_by_owner(
            sample_user_data["tg_id"], is_available=False
        )
        assert len(codes) == 2

    def test_expired_invitation_code_not_available(self, test_db, sample_user_data):
        """测试过期邀请码不会出现在可用列表中"""
        now_ts = int(time())
        test_db.add_invitation_code(
            code="EXPIRED-1",
            owner=sample_user_data["tg_id"],
            created_at=now_ts - 100,
            expires_at=now_ts - 1,
        )
        test_db.add_invitation_code(
            code="VALID-1",
            owner=sample_user_data["tg_id"],
            created_at=now_ts,
            expires_at=now_ts + 3600,
        )

        codes = test_db.get_invitation_code_by_owner(
            sample_user_data["tg_id"], is_available=True
        )

        assert codes == ["VALID-1"]

    def test_verify_invitation_code_returns_expiry(self, test_db, sample_user_data):
        """测试校验邀请码时会返回过期时间"""
        now_ts = int(time())
        test_db.add_invitation_code(
            code="WITH-EXPIRY",
            owner=sample_user_data["tg_id"],
            created_at=now_ts,
            expires_at=now_ts + 3600,
        )

        result = test_db.verify_invitation_code_is_used("WITH-EXPIRY")

        assert result is not None
        assert result[2] == now_ts + 3600

    def test_get_invited_count(self, test_db, sample_user_data):
        """测试获取已邀请人数"""
        # 添加并使用多个邀请码
        for i in range(3):
            code = f"COUNT-{i}"
            test_db.add_invitation_code(code=code, owner=sample_user_data["tg_id"])
            test_db.update_invitation_status(code, 100000000 + i)

        count = test_db.get_invited_count_by_owner(sample_user_data["tg_id"])
        assert count == 3

    def test_verify_nonexistent_code(self, test_db):
        """测试验证不存在的邀请码"""
        result = test_db.verify_invitation_code_is_used("NONEXISTENT-CODE")
        assert result is None
