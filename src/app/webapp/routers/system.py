import time
from datetime import datetime

from app.config import settings
from app.db import DB
from app.log import uvicorn_logger as logger
from app.redis_client import Redis
from app.utils.utils import get_user_name_from_tg_id
from app.webapp.auth import get_telegram_user
from app.webapp.middlewares import require_telegram_auth
from app.webapp.schemas import TelegramUser
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health")
async def health_check():
    """健康检查端点 - 用于负载均衡和监控"""
    start_time = time.time()
    
    # 检查数据库连接
    db_healthy = False
    db_info = None
    try:
        db = DB()
        db_healthy = db.health_check()
        db_info = db.get_db_info()
        db.close()
    except Exception as e:
        logger.error(f"健康检查 - 数据库检查失败: {e}")
        db_info = {"error": str(e)}
    
    # 检查Redis连接
    redis_healthy = False
    redis_info = None
    try:
        redis_client = Redis()
        redis_healthy = redis_client.health_check()
        if redis_healthy:
            info = redis_client.get_info()
            if info:
                redis_info = {
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human"),
                    "uptime_in_seconds": info.get("uptime_in_seconds"),
                }
    except Exception as e:
        logger.error(f"健康检查 - Redis检查失败: {e}")
        redis_info = {"error": str(e)}
    
    # 计算响应时间
    response_time_ms = round((time.time() - start_time) * 1000, 2)
    
    # 确定整体健康状态
    overall_healthy = db_healthy and redis_healthy
    
    health_status = {
        "status": "healthy" if overall_healthy else "unhealthy",
        "timestamp": datetime.now(settings.TZ).isoformat(),
        "response_time_ms": response_time_ms,
        "components": {
            "database": {
                "status": "healthy" if db_healthy else "unhealthy",
                "details": db_info
            },
            "redis": {
                "status": "healthy" if redis_healthy else "unhealthy",
                "details": redis_info
            }
        },
        "version": "0.4.1"
    }
    
    if not overall_healthy:
        logger.warning(f"健康检查失败: {health_status}")
    
    return health_status


@router.get("/health/live")
async def liveness_check():
    """存活检查端点 - Kubernetes liveness probe"""
    return {"status": "alive", "timestamp": datetime.now(settings.TZ).isoformat()}


@router.get("/health/ready")
async def readiness_check():
    """就绪检查端点 - Kubernetes readiness probe"""
    try:
        # 快速检查关键服务
        db = DB()
        db_ok = db.health_check()
        db.close()
        
        redis_client = Redis()
        redis_ok = redis_client.health_check()
        
        if db_ok and redis_ok:
            return {"status": "ready", "timestamp": datetime.now(settings.TZ).isoformat()}
        else:
            raise HTTPException(status_code=503, detail="Service not ready")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"就绪检查失败: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/stats")
@require_telegram_auth
async def get_system_stats(
    request: Request, user: TelegramUser = Depends(get_telegram_user)
):
    """获取系统统计信息（不需要管理员权限）"""
    logger.info(f"{user.username or user.first_name or user.id} 获取系统统计信息")

    db = DB()
    try:
        # 获取所有Plex用户数量
        plex_users_count = db.get_plex_users_num()

        # 获取所有Emby用户数量
        emby_users_count = db.get_emby_users_num()

        # 获取总用户数量（去重，避免同时绑定两个服务的用户被重复计算）
        # 1. 先统计有 tg_id 的用户（通过 tg_id 去重）
        # 2. 再统计没有 tg_id 的用户（这些用户无法去重，按账户数量计算）
        total_users_query = """
        SELECT 
            (SELECT COUNT(DISTINCT tg_id) FROM (
                SELECT tg_id FROM user WHERE tg_id IS NOT NULL
                UNION
                SELECT tg_id FROM emby_user WHERE tg_id IS NOT NULL
            )) +
            (SELECT COUNT(*) FROM user WHERE tg_id IS NULL) +
            (SELECT COUNT(*) FROM emby_user WHERE tg_id IS NULL)
        """
        rslt = db.cur.execute(total_users_query)
        total_users_count = rslt.fetchone()[0]

        stats = {
            "plex_users": plex_users_count,
            "emby_users": emby_users_count,
            "total_users": total_users_count,
        }

        logger.info(f"系统统计信息: {stats}")
        return stats

    except Exception as e:
        logger.error(f"获取系统统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取系统统计信息失败")
    finally:
        db.close()
        logger.debug("数据库连接已关闭")


@router.get("/status")
async def get_system_status():
    """获取系统状态信息（公开接口，不需要登录）"""
    try:
        status_data = {
            "site_name": settings.SITE_NAME,
            "emby_entry_url": settings.EMBY_ENTRY_URL or settings.EMBY_BASE_URL,
            "plex_register": settings.PLEX_REGISTER,
            "emby_register": settings.EMBY_REGISTER,
            "premium_unlock_enabled": settings.PREMIUM_UNLOCK_ENABLED,
            "premium_daily_credits": settings.PREMIUM_DAILY_CREDITS,
            "credits_transfer_enabled": settings.CREDITS_TRANSFER_ENABLED,
            "community_links": {
                "group": getattr(settings, "TG_GROUP", ""),
                "channel": getattr(
                    settings, "TG_CHANNEL", getattr(settings, "TG_GROUP", "")
                ),  # 如果没有单独的频道，使用群组链接
            },
        }

        logger.info("获取系统状态信息")
        return status_data
    except Exception as e:
        logger.error(f"获取系统状态信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取系统状态信息失败")


@router.get("/traffic-overview")
@require_telegram_auth
async def get_traffic_overview(
    request: Request, user: TelegramUser = Depends(get_telegram_user)
):
    """获取流量统计概览数据（不需要管理员权限）"""
    logger.info(f"{user.username or user.first_name or user.id} 获取流量统计概览")

    db = DB()
    try:
        traffic_stats = db.get_traffic_statistics()
        logger.info("流量统计概览数据获取成功")

        return {
            "success": True,
            "message": "获取成功",
            "data": traffic_stats,
        }
    except Exception as e:
        logger.error(f"获取流量统计概览失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取流量统计失败")
    finally:
        db.close()
        logger.debug("数据库连接已关闭")


@router.get("/all-lines-traffic-stats")
@require_telegram_auth
async def get_all_lines_traffic_stats(
    request: Request, user: TelegramUser = Depends(get_telegram_user)
):
    """获取所有线路（普通+高级）的流量统计信息（需要管理员权限）"""
    # 检查管理员权限
    if user.id not in settings.TG_ADMIN_CHAT_ID:
        raise HTTPException(status_code=403, detail="权限不足，需要管理员权限")

    logger.info(
        f"{user.username or user.first_name or user.id} 获取所有线路流量统计信息"
    )

    db = DB()
    try:
        stats = db.get_all_lines_traffic_statistics()
        logger.info("所有线路流量统计信息获取成功")
        return {"success": True, "message": "获取成功", "data": stats}
    except Exception as e:
        logger.error(f"获取所有线路流量统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取流量统计失败")
    finally:
        db.close()


@router.get("/line-switch-history")
@require_telegram_auth
async def get_line_switch_history(
    request: Request,
    user: TelegramUser = Depends(get_telegram_user),
    limit: int = 10,
):
    """获取线路切换历史记录"""
    logger.info(
        f"{user.username or user.first_name or user.id} 获取线路切换历史记录"
    )

    db = DB()
    try:
        # 普通用户只能查看自己的历史
        # 管理员可以查看所有用户的历史
        if user.id in settings.TG_ADMIN_CHAT_ID:
            history = db.get_line_switch_history(tg_id=None, limit=limit)
        else:
            history = db.get_line_switch_history(tg_id=user.id, limit=limit)

        return {"success": True, "message": "获取成功", "data": history}
    except Exception as e:
        logger.error(f"获取线路切换历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取历史记录失败")
    finally:
        db.close()


# 请求模型
class PrivilegedUserRequest(BaseModel):
    tg_id: int


@router.get("/privileged-users")
@require_telegram_auth
async def get_privileged_users(
    request: Request, user: TelegramUser = Depends(get_telegram_user)
):
    """获取特权用户列表（需要管理员权限）"""
    # 检查管理员权限
    if user.id not in settings.TG_ADMIN_CHAT_ID:
        raise HTTPException(status_code=403, detail="权限不足")

    logger.info(f"{user.username or user.first_name or user.id} 获取特权用户列表")

    try:
        # 获取特权用户列表，并获取用户名
        privileged_users = []
        for tg_id in settings.TG_PRIVILEGED_USERS:
            username = await get_user_name_from_tg_id(tg_id)
            privileged_users.append({"tg_id": tg_id, "username": username})

        return {
            "success": True,
            "data": privileged_users,
        }
    except Exception as e:
        logger.error(f"获取特权用户列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取特权用户列表失败")


@router.post("/privileged-users")
@require_telegram_auth
async def add_privileged_user(
    request: Request,
    data: PrivilegedUserRequest,
    user: TelegramUser = Depends(get_telegram_user),
):
    """添加特权用户（需要管理员权限）"""
    # 检查管理员权限
    if user.id not in settings.TG_ADMIN_CHAT_ID:
        raise HTTPException(status_code=403, detail="权限不足")

    logger.info(
        f"{user.username or user.first_name or user.id} 添加特权用户: {data.tg_id}"
    )

    try:
        # 检查是否已存在
        if data.tg_id in settings.TG_PRIVILEGED_USERS:
            return {
                "success": False,
                "message": f"用户 {data.tg_id} 已经是特权用户",
            }

        # 添加到特权用户列表
        settings.TG_PRIVILEGED_USERS.append(data.tg_id)

        # 保存到配置文件
        config_data = {
            "TG_PRIVILEGED_USERS": ",".join(map(str, settings.TG_PRIVILEGED_USERS))
        }
        settings.save_config_to_env_file(config_data)

        username = await get_user_name_from_tg_id(data.tg_id)
        logger.info(f"成功添加特权用户: {username} (ID: {data.tg_id})")

        return {
            "success": True,
            "message": f"成功添加特权用户: {username}",
            "data": {"tg_id": data.tg_id, "username": username},
        }
    except Exception as e:
        logger.error(f"添加特权用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加特权用户失败: {str(e)}")


@router.delete("/privileged-users/{tg_id}")
@require_telegram_auth
async def remove_privileged_user(
    request: Request,
    tg_id: int,
    user: TelegramUser = Depends(get_telegram_user),
):
    """删除特权用户（需要管理员权限）"""
    # 检查管理员权限
    if user.id not in settings.TG_ADMIN_CHAT_ID:
        raise HTTPException(status_code=403, detail="权限不足")

    logger.info(
        f"{user.username or user.first_name or user.id} 删除特权用户: {tg_id}"
    )

    try:
        # 检查是否存在
        if tg_id not in settings.TG_PRIVILEGED_USERS:
            return {
                "success": False,
                "message": f"用户 {tg_id} 不是特权用户",
            }

        # 从特权用户列表移除
        settings.TG_PRIVILEGED_USERS.remove(tg_id)

        # 保存到配置文件
        config_data = {
            "TG_PRIVILEGED_USERS": ",".join(map(str, settings.TG_PRIVILEGED_USERS))
        }
        settings.save_config_to_env_file(config_data)

        username = await get_user_name_from_tg_id(tg_id)
        logger.info(f"成功删除特权用户: {username} (ID: {tg_id})")

        return {
            "success": True,
            "message": f"成功删除特权用户: {username}",
        }
    except Exception as e:
        logger.error(f"删除特权用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除特权用户失败: {str(e)}")
