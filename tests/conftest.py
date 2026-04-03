#!/usr/bin/env python3
"""
pytest 配置和通用 fixtures

提供测试所需的基础设施：
- 临时数据库
- 模拟配置
- API 测试客户端
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

# 确保 src 目录在 Python 路径中
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def temp_dir() -> Generator[Path, None, None]:
    """创建临时目录用于测试"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_settings(temp_dir: Path):
    """模拟配置设置"""
    mock_config = MagicMock()
    mock_config.DATA_PATH = temp_dir
    mock_config.TG_ADMIN_CHAT_ID = [123456789]
    mock_config.UNLOCK_CREDITS = 100
    mock_config.CREDITS_TRANSFER_ENABLED = True
    mock_config.STREAM_BACKEND = ["line1.example.com", "line2.example.com"]
    mock_config.PREMIUM_STREAM_BACKEND = ["premium1.example.com"]
    mock_config.PREMIUM_FREE = False
    mock_config.NSFW_LIBS = ["NSFW"]
    mock_config.PLEX_BASE_URL = "https://plex.example.com"
    mock_config.EMBY_BASE_URL = "https://emby.example.com"
    mock_config.EMBY_ENTRY_URL = "https://emby.example.com"
    mock_config.WEBAPP_URL = "https://webapp.example.com"
    mock_config.LOG_LEVEL = "INFO"

    with patch("app.config.settings", mock_config):
        yield mock_config


@pytest.fixture
def test_db(temp_dir: Path, mock_settings):
    """创建测试用的临时数据库"""
    from app.db import DB

    db_path = temp_dir / "test_data.db"
    if db_path.exists():
        db_path.unlink()
    db = DB(db=db_path)
    yield db
    db.close()


@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        "tg_id": 123456789,
        "plex_id": 1001,
        "plex_email": "test@example.com",
        "plex_username": "testuser",
        "emby_id": "emby-uuid-1234",
        "emby_username": "embyuser",
        "credits": 100.0,
        "donation": 50.0,
    }


@pytest.fixture
def populated_db(test_db, sample_user_data):
    """包含示例数据的测试数据库"""
    # 添加 Plex 用户
    test_db.add_plex_user(
        plex_id=sample_user_data["plex_id"],
        tg_id=sample_user_data["tg_id"],
        plex_email=sample_user_data["plex_email"],
        plex_username=sample_user_data["plex_username"],
        credits=0,
    )

    # 添加用户统计数据
    test_db.add_user_data(
        tg_id=sample_user_data["tg_id"],
        credits=sample_user_data["credits"],
        donation=sample_user_data["donation"],
    )

    yield test_db


# 标记需要异步执行的测试
pytest_plugins = ["pytest_asyncio"]
