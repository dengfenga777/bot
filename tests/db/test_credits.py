#!/usr/bin/env python3
"""积分数据库操作测试"""

import pytest


class TestCreditsOperations:
    """积分相关数据库操作测试"""

    def test_add_user_data(self, test_db, sample_user_data):
        """测试添加用户统计数据"""
        result = test_db.add_user_data(
            tg_id=sample_user_data["tg_id"],
            credits=sample_user_data["credits"],
            donation=sample_user_data["donation"],
        )
        assert result is True

        # 验证数据已添加
        stats = test_db.get_stats_by_tg_id(sample_user_data["tg_id"])
        assert stats is not None
        assert stats[2] == sample_user_data["credits"]
        assert stats[1] == sample_user_data["donation"]

    def test_get_user_credits(self, populated_db, sample_user_data):
        """测试获取用户积分"""
        success, credits = populated_db.get_user_credits(sample_user_data["tg_id"])
        assert success is True
        assert credits == sample_user_data["credits"]

    def test_get_user_credits_not_found(self, test_db):
        """测试获取不存在用户的积分"""
        success, result = test_db.get_user_credits(999999999)
        assert success is False
        assert "未找到" in result

    def test_update_user_credits(self, populated_db, sample_user_data):
        """测试更新用户积分"""
        new_credits = 200.0
        result = populated_db.update_user_credits(
            new_credits, tg_id=sample_user_data["tg_id"]
        )
        assert result is True

        # 验证更新成功
        success, credits = populated_db.get_user_credits(sample_user_data["tg_id"])
        assert success is True
        assert credits == new_credits

    def test_update_user_donation(self, populated_db, sample_user_data):
        """测试更新用户捐赠金额"""
        new_donation = 100
        result = populated_db.update_user_donation(
            new_donation, sample_user_data["tg_id"]
        )
        assert result is True

        # 验证更新成功
        stats = populated_db.get_stats_by_tg_id(sample_user_data["tg_id"])
        assert stats[1] == new_donation

    def test_get_credits_rank(self, populated_db):
        """测试获取积分排行榜"""
        rank = populated_db.get_credits_rank()
        assert isinstance(rank, list)
        # 应该至少有一个用户（来自 populated_db fixture）
        assert len(rank) >= 1

    def test_get_donation_rank(self, populated_db):
        """测试获取捐赠排行榜"""
        rank = populated_db.get_donation_rank()
        assert isinstance(rank, list)
        assert len(rank) >= 1


class TestCreditsEdgeCases:
    """积分操作边界情况测试"""

    def test_update_credits_with_zero(self, populated_db, sample_user_data):
        """测试将积分更新为零"""
        result = populated_db.update_user_credits(0, tg_id=sample_user_data["tg_id"])
        assert result is True

        success, credits = populated_db.get_user_credits(sample_user_data["tg_id"])
        assert credits == 0

    def test_update_credits_with_negative(self, populated_db, sample_user_data):
        """测试负数积分（虽然不推荐，但数据库应该允许）"""
        result = populated_db.update_user_credits(-50.0, tg_id=sample_user_data["tg_id"])
        assert result is True

        success, credits = populated_db.get_user_credits(sample_user_data["tg_id"])
        assert credits == -50.0

    def test_update_credits_with_decimal(self, populated_db, sample_user_data):
        """测试小数积分"""
        result = populated_db.update_user_credits(
            123.456, tg_id=sample_user_data["tg_id"]
        )
        assert result is True

        success, credits = populated_db.get_user_credits(sample_user_data["tg_id"])
        assert abs(credits - 123.456) < 0.001  # 浮点数比较
