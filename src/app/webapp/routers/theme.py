"""主题配置管理路由"""

import json
from typing import Dict

from app.cache import RedisCache
from app.log import logger
from app.webapp.auth import get_telegram_user
from app.webapp.middlewares import require_telegram_auth
from app.webapp.routers.admin import check_admin_permission
from app.webapp.schemas import TelegramUser
from app.webapp.schemas.theme import (
    ThemeConfig,
    ThemeConfigResponse,
    ThemeConfigUpdate,
)
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/theme", tags=["主题配置"])

# 主题配置缓存
theme_config_cache = RedisCache(
    db=0, cache_key_prefix="theme_config:", ttl_seconds=None  # 持久化存储
)

DEFAULT_THEME_KEY = "default"


def get_theme_config() -> ThemeConfig:
    """获取主题配置"""
    try:
        config_str = theme_config_cache.get(DEFAULT_THEME_KEY)
        if config_str:
            config_data = json.loads(config_str)
            return ThemeConfig(**config_data)
        return ThemeConfig()
    except Exception as e:
        logger.error(f"获取主题配置失败: {e}")
        return ThemeConfig()


def save_theme_config(config: ThemeConfig) -> bool:
    """保存主题配置"""
    try:
        config_str = config.model_dump_json()
        theme_config_cache.put(DEFAULT_THEME_KEY, config_str)
        return True
    except Exception as e:
        logger.error(f"保存主题配置失败: {e}")
        return False


@router.get("/config", response_model=ThemeConfigResponse)
async def get_config(request: Request):
    """
    获取主题配置

    任何用户都可以获取主题配置
    """
    try:
        config = get_theme_config()
        return ThemeConfigResponse(config=config, message="主题配置获取成功")
    except Exception as e:
        logger.error(f"获取主题配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取主题配置失败",
        )


@router.post("/config")
@require_telegram_auth
async def update_config(
    request: Request,
    config_update: ThemeConfigUpdate,
    user: TelegramUser = Depends(get_telegram_user),
):
    """
    更新主题配置

    需要管理员权限
    """
    check_admin_permission(user)
    try:
        # 获取当前配置
        current_config = get_theme_config()

        # 更新配置
        update_data = config_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(current_config, key, value)

        # 保存配置
        if not save_theme_config(current_config):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="保存主题配置失败",
            )

        logger.info(f"主题配置已更新: {update_data}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "主题配置更新成功", "config": current_config.model_dump()},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新主题配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新主题配置失败",
        )


@router.post("/reset")
@require_telegram_auth
async def reset_config(request: Request, user: TelegramUser = Depends(get_telegram_user)):
    """
    重置主题配置为默认值

    需要管理员权限
    """
    check_admin_permission(user)
    try:
        default_config = ThemeConfig()
        if not save_theme_config(default_config):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="重置主题配置失败",
            )

        logger.info("主题配置已重置为默认值")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "主题配置已重置", "config": default_config.model_dump()},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重置主题配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重置主题配置失败",
        )
