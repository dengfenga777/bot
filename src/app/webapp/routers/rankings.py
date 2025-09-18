from datetime import datetime

from app.config import settings
from app.db import DB
from app.emby import Emby
from app.log import uvicorn_logger as logger
from app.plex import Plex
from app.utils import get_user_avatar_from_tg_id, get_user_name_from_tg_id
from app.webapp.auth import get_telegram_user
from app.webapp.middlewares import require_telegram_auth
from app.webapp.schemas import TelegramUser
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter(prefix="/api", tags=["rankings"])


@router.get("/rankings/credits")
@require_telegram_auth
async def get_credits_rankings(
    request: Request, user: TelegramUser = Depends(get_telegram_user)
):
    """获取花币排行榜数据"""
    logger.info(f"{user.username or user.first_name or user.id} 开始获取花币排行榜数据")

    db = DB()
    try:
        credits_rankings = []
        try:
            logger.debug("正在查询花币排行")
            credits_data = db.get_credits_rank()
            if credits_data:
                credits_rankings = [
                    {
                        "name": get_user_name_from_tg_id(info[0]),
                        "credits": info[1],
                        "avatar": get_user_avatar_from_tg_id(info[0]),
                        "is_self": info[0] == user.id,  # tg_id 比较
                    }
                    for info in credits_data
                    if info[1] > 0 and info[0] not in settings.ADMIN_CHAT_ID
                ]
        except Exception as e:
            logger.error(f"获取花币排行失败: {str(e)}")

        logger.info(
            f"{user.username or user.first_name or user.id} 获取花币排行榜数据成功"
        )
        return {"credits_rank": credits_rankings}
    except Exception as e:
        logger.error(f"获取花币排行榜数据时发生未预期的错误: {str(e)}")
        raise HTTPException(status_code=500, detail="获取花币排行榜数据失败")
    finally:
        db.close()
        logger.debug("数据库连接已关闭")


@router.get("/rankings/donation")
@require_telegram_auth
async def get_donation_rankings(
    request: Request, user: TelegramUser = Depends(get_telegram_user)
):
    """获取捐赠排行榜数据"""
    logger.info(f"{user.username or user.first_name or user.id} 开始获取捐赠排行榜数据")

    db = DB()
    try:
        donation_rankings = []
        try:
            logger.debug("正在查询捐赠排行")
            donation_data = db.get_donation_rank()
            if donation_data:
                donation_rankings = [
                    {
                        "name": get_user_name_from_tg_id(info[0]),
                        "donation": info[1],
                        "avatar": get_user_avatar_from_tg_id(info[0]),
                        "is_self": info[0] == user.id,  # tg_id 比较
                    }
                    for info in donation_data
                    if info[1] > 0
                ]
        except Exception as e:
            logger.error(f"获取捐赠排行失败: {str(e)}")

        logger.info(
            f"{user.username or user.first_name or user.id} 获取捐赠排行榜数据成功"
        )
        return {"donation_rank": donation_rankings}
    except Exception as e:
        logger.error(f"获取捐赠排行榜数据时发生未预期的错误: {str(e)}")
        raise HTTPException(status_code=500, detail="获取捐赠排行榜数据失败")
    finally:
        db.close()
        logger.debug("数据库连接已关闭")


@router.get("/rankings/watched-time/plex")
@require_telegram_auth
async def get_plex_watched_time_rankings(
    request: Request, user: TelegramUser = Depends(get_telegram_user)
):
    """获取Plex观看时长排行榜数据"""
    logger.info(
        f"{user.username or user.first_name or user.id} 开始获取Plex观看时长排行榜数据"
    )

    db = DB()
    try:
        watched_time_rank_plex = []
        try:
            logger.debug("正在查询Plex播放时长排行")
            plex_watch_time_data = db.get_plex_watched_time_rank()
            if plex_watch_time_data:
                watched_time_rank_plex = [
                    {
                        "name": info[2],
                        "watched_time": info[3],
                        "avatar": Plex.get_user_avatar_by_username(info[2]),
                        "is_premium": bool(info[4])
                        if len(info) > 4 and info[4] is not None
                        else False,
                        "is_self": info[1] == user.id,  # tg_id 比较
                    }
                    for info in plex_watch_time_data
                    if info[3] > 0
                ]
        except Exception as e:
            logger.error(f"获取Plex播放时长排行失败: {str(e)}")

        logger.info(
            f"{user.username or user.first_name or user.id} 获取Plex观看时长排行榜数据成功"
        )
        return {"watched_time_rank_plex": watched_time_rank_plex}
    except Exception as e:
        logger.error(f"获取Plex观看时长排行榜数据时发生未预期的错误: {str(e)}")
        raise HTTPException(status_code=500, detail="获取Plex观看时长排行榜数据失败")
    finally:
        db.close()
        logger.debug("数据库连接已关闭")


@router.get("/rankings/watched-time/emby")
@require_telegram_auth
async def get_emby_watched_time_rankings(
    request: Request, user: TelegramUser = Depends(get_telegram_user)
):
    """获取Emby观看时长排行榜数据"""
    logger.info(
        f"{user.username or user.first_name or user.id} 开始获取Emby观看时长排行榜数据"
    )

    db = DB()
    try:
        watched_time_rank_emby = []
        emby = Emby()
        try:
            logger.debug("正在查询Emby播放时长排行")
            emby_watch_time_data = db.get_emby_watched_time_rank()
            if emby_watch_time_data:
                watched_time_rank_emby = [
                    {
                        "name": info[1],
                        "watched_time": info[2],
                        "avatar": emby.get_user_avatar_by_username(
                            info[1], from_emby=False
                        ),
                        "is_premium": bool(info[3])
                        if len(info) > 3 and info[3] is not None
                        else False,
                        "is_self": info[4] == user.id
                        if len(info) > 4
                        else False,  # tg_id 比较
                    }
                    for info in emby_watch_time_data
                    if info[2] > 0
                ]
        except Exception as e:
            logger.error(f"获取Emby播放时长排行失败: {str(e)}")

        logger.info(
            f"{user.username or user.first_name or user.id} 获取Emby观看时长排行榜数据成功"
        )
        return {"watched_time_rank_emby": watched_time_rank_emby}
    except Exception as e:
        logger.error(f"获取Emby观看时长排行榜数据时发生未预期的错误: {str(e)}")
        raise HTTPException(status_code=500, detail="获取Emby观看时长排行榜数据失败")
    finally:
        db.close()
        logger.debug("数据库连接已关闭")


@router.get("/rankings/watched-time/combined")
@require_telegram_auth
async def get_combined_watched_time_rankings(
    request: Request, user: TelegramUser = Depends(get_telegram_user)
):
    """获取 Plex+Emby 合并观看时长排行榜数据"""
    logger.info(
        f"{user.username or user.first_name or user.id} 开始获取合并观看时长排行榜数据"
    )

    db = DB()
    try:
        watched_time_rank_combined = []
        emby = Emby()
        try:
            logger.debug("正在查询 Plex 与 Emby 播放时长并进行合并")
            plex_rows = db.get_plex_watched_time_rank()
            emby_rows = db.get_emby_watched_time_rank()

            totals = {}

            def add_total(key, payload):
                if key not in totals:
                    totals[key] = {"hours": 0.0, **payload}
                totals[key]["hours"] += float(payload.get("hours") or 0)

            # 聚合 Plex
            for row in plex_rows:
                plex_id, tg_id, plex_username, watched_time, _is_premium = row
                key = tg_id if tg_id is not None else f"plex::{plex_username}"
                add_total(
                    key,
                    {
                        "tg_id": tg_id,
                        "platform": "plex" if tg_id is None else "telegram",
                        "name_hint": plex_username,
                        "hours": watched_time,
                    },
                )

            # 聚合 Emby
            for row in emby_rows:
                emby_id, emby_username, emby_watched_time, _is_premium, tg_id = row
                key = tg_id if tg_id is not None else f"emby::{emby_username}"
                add_total(
                    key,
                    {
                        "tg_id": tg_id,
                        "platform": "emby" if tg_id is None else "telegram",
                        "name_hint": emby_username,
                        "hours": emby_watched_time,
                    },
                )

            # 生成输出
            for key, info in totals.items():
                if info["hours"] <= 0:
                    continue
                if isinstance(key, int):
                    name = get_user_name_from_tg_id(key)
                    avatar = get_user_avatar_from_tg_id(key)
                    is_self = key == user.id
                else:
                    name = info.get("name_hint")
                    # 根据来源选择头像
                    if str(key).startswith("plex::"):
                        avatar = Plex.get_user_avatar_by_username(name)
                    else:
                        avatar = emby.get_user_avatar_by_username(name, from_emby=False)
                    is_self = False

                watched_time_rank_combined.append(
                    {
                        "name": name,
                        "watched_time": info["hours"],
                        "avatar": avatar,
                        "is_self": is_self,
                    }
                )

            watched_time_rank_combined = sorted(
                watched_time_rank_combined, key=lambda x: x["watched_time"], reverse=True
            )

        except Exception as e:
            logger.error(f"获取合并观看时长排行失败: {str(e)}")

        logger.info(
            f"{user.username or user.first_name or user.id} 获取合并观看时长排行榜数据成功"
        )
        return {"watched_time_rank_combined": watched_time_rank_combined}
    except Exception as e:
        logger.error(f"获取合并观看时长排行榜数据时发生未预期的错误: {str(e)}")
        raise HTTPException(status_code=500, detail="获取合并观看时长排行榜数据失败")
    finally:
        db.close()
        logger.debug("数据库连接已关闭")


    # 流量排行榜相关接口已移除


@router.get("/rankings/traffic/plex")
@require_telegram_auth
async def get_plex_traffic_rankings(
    request: Request,
    user: TelegramUser = Depends(get_telegram_user),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
):
    """获取 Plex 流量排行榜数据（按用户名聚合）"""
    try:
        tz = settings.TZ
        now = datetime.now(tz)
        # 解析时间范围
        if start_date and end_date:
            try:
                start_dt = datetime.fromisoformat(start_date).replace(tzinfo=tz, hour=0, minute=0, second=0, microsecond=0)
                end_dt = datetime.fromisoformat(end_date).replace(tzinfo=tz, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            except Exception:
                raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")
        else:
            start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = start_dt + timedelta(days=1)

        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()

        db = DB()
        results = []
        try:
            rows = db.cur.execute(
                """
                SELECT username, COALESCE(SUM(send_bytes), 0) AS total_traffic
                FROM line_traffic_stats
                WHERE LOWER(service) = 'plex' AND timestamp >= ? AND timestamp < ?
                GROUP BY username
                ORDER BY total_traffic DESC
                LIMIT 100
                """,
                (start_iso, end_iso),
            ).fetchall()

            for username, total in rows:
                info = db.get_plex_info_by_plex_username(username)
                tg_id = info[1] if info else None
                is_premium = bool(info[9]) if info and len(info) > 9 and info[9] is not None else False
                avatar = Plex.get_user_avatar_by_username(username)
                results.append(
                    {
                        "name": username,
                        "traffic": int(total or 0),
                        "avatar": avatar,
                        "is_premium": is_premium,
                        "is_self": bool(tg_id == user.id) if tg_id is not None else False,
                    }
                )

            logger.info(
                f"{user.username or user.first_name or user.id} 获取Plex流量排行榜数据成功"
            )
            return {"traffic_rank_plex": results}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Plex流量排行榜数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取Plex流量排行榜失败")


@router.get("/rankings/traffic/emby")
@require_telegram_auth
async def get_emby_traffic_rankings(
    request: Request,
    user: TelegramUser = Depends(get_telegram_user),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
):
    """获取 Emby 流量排行榜数据（按用户名聚合）"""
    try:
        tz = settings.TZ
        now = datetime.now(tz)
        # 解析时间范围
        if start_date and end_date:
            try:
                start_dt = datetime.fromisoformat(start_date).replace(tzinfo=tz, hour=0, minute=0, second=0, microsecond=0)
                end_dt = datetime.fromisoformat(end_date).replace(tzinfo=tz, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            except Exception:
                raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")
        else:
            start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = start_dt + timedelta(days=1)

        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()

        db = DB()
        results = []
        try:
            rows = db.cur.execute(
                """
                SELECT username, COALESCE(SUM(send_bytes), 0) AS total_traffic
                FROM line_traffic_stats
                WHERE LOWER(service) = 'emby' AND timestamp >= ? AND timestamp < ?
                GROUP BY username
                ORDER BY total_traffic DESC
                LIMIT 100
                """,
                (start_iso, end_iso),
            ).fetchall()

            emby = Emby()
            for username, total in rows:
                info = db.get_emby_info_by_emby_username(username)
                tg_id = info[2] if info else None
                is_premium = bool(info[8]) if info and len(info) > 8 and info[8] is not None else False
                avatar = emby.get_user_avatar_by_username(username, from_emby=False)
                results.append(
                    {
                        "name": username,
                        "traffic": int(total or 0),
                        "avatar": avatar,
                        "is_premium": is_premium,
                        "is_self": bool(tg_id == user.id) if tg_id is not None else False,
                    }
                )

            logger.info(
                f"{user.username or user.first_name or user.id} 获取Emby流量排行榜数据成功"
            )
            return {"traffic_rank_emby": results}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Emby流量排行榜数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取Emby流量排行榜失败")
