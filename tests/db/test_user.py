#!/usr/bin/env python3
"""用户数据库操作测试"""

import pytest


class TestUserOperations:
    """用户相关数据库操作测试"""

    def test_add_plex_user(self, test_db, sample_user_data):
        """测试添加 Plex 用户"""
        result = test_db.add_plex_user(
            plex_id=sample_user_data["plex_id"],
            tg_id=sample_user_data["tg_id"],
            plex_email=sample_user_data["plex_email"],
            plex_username=sample_user_data["plex_username"],
        )
        assert result is True

        # 验证用户已添加
        info = test_db.get_plex_info_by_tg_id(sample_user_data["tg_id"])
        assert info is not None
        assert info[0] == sample_user_data["plex_id"]
        assert info[4] == sample_user_data["plex_username"]

    def test_add_emby_user(self, test_db, sample_user_data):
        """测试添加 Emby 用户"""
        result = test_db.add_emby_user(
            emby_username=sample_user_data["emby_username"],
            emby_id=sample_user_data["emby_id"],
            tg_id=sample_user_data["tg_id"],
        )
        assert result is True

        # 验证用户已添加
        info = test_db.get_emby_info_by_tg_id(sample_user_data["tg_id"])
        assert info is not None
        assert info[0] == sample_user_data["emby_username"]
        assert info[1] == sample_user_data["emby_id"]

    def test_get_plex_info_by_plex_id(self, populated_db, sample_user_data):
        """测试通过 Plex ID 获取用户信息"""
        info = populated_db.get_plex_info_by_plex_id(sample_user_data["plex_id"])
        assert info is not None
        assert info[1] == sample_user_data["tg_id"]

    def test_get_plex_info_by_email(self, populated_db, sample_user_data):
        """测试通过邮箱获取用户信息"""
        info = populated_db.get_plex_info_by_plex_email(sample_user_data["plex_email"])
        assert info is not None
        assert info[4] == sample_user_data["plex_username"]

    def test_get_plex_info_by_username(self, populated_db, sample_user_data):
        """测试通过用户名获取用户信息"""
        info = populated_db.get_plex_info_by_plex_username(
            sample_user_data["plex_username"]
        )
        assert info is not None
        assert info[0] == sample_user_data["plex_id"]

    def test_get_nonexistent_user(self, test_db):
        """测试获取不存在的用户"""
        info = test_db.get_plex_info_by_tg_id(999999999)
        assert info is None

    def test_get_plex_users_num(self, populated_db):
        """测试获取 Plex 用户数量"""
        count = populated_db.get_plex_users_num()
        assert count >= 1

    def test_update_user_tg_id(self, test_db, sample_user_data):
        """测试更新用户 Telegram ID"""
        # 先添加用户
        test_db.add_plex_user(
            plex_id=sample_user_data["plex_id"],
            tg_id=None,
            plex_email=sample_user_data["plex_email"],
            plex_username=sample_user_data["plex_username"],
        )

        # 更新 tg_id
        new_tg_id = 987654321
        result = test_db.update_user_tg_id(new_tg_id, plex_id=sample_user_data["plex_id"])
        assert result is True

        # 验证更新成功
        info = test_db.get_plex_info_by_plex_id(sample_user_data["plex_id"])
        assert info[1] == new_tg_id

    def test_delete_plex_user(self, test_db, sample_user_data):
        """测试删除 Plex 用户"""
        # 先添加用户
        test_db.add_plex_user(
            plex_id=sample_user_data["plex_id"],
            tg_id=sample_user_data["tg_id"],
            plex_email=sample_user_data["plex_email"],
            plex_username=sample_user_data["plex_username"],
        )

        # 删除用户
        result = test_db.delete_plex_user(sample_user_data["tg_id"])
        assert result is True

        # 验证用户已删除
        info = test_db.get_plex_info_by_tg_id(sample_user_data["tg_id"])
        assert info is None
