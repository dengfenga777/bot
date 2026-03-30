#!/usr/bin/env python3
"""用户核心路由 - Dashboard、用户信息、活动记录"""

from datetime import datetime, timedelta
from time import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import settings
from app.db import DB
from app.emby import Emby
from app.log import uvicorn_logger as logger
from app.plex import Plex
from app.tautulli import Tautulli
from app.utils.utils import (
    get_user_name_from_tg_id,
    get_user_total_duration,
)
from app.webapp.auth import get_telegram_user
from app.webapp.middlewares import require_telegram_auth
from app.webapp.schemas import TelegramUser, UserInfo

router = APIRouter()


@router.get("/dashboard")
@require_telegram_auth
async def get_dashboard(
    request: Request, user: TelegramUser = Depends(get_telegram_user)
):
    """获取用户仪表盘数据（积分、观看时长、排名）"""
    user_id = user.id
    db = DB()

    try:
        # 获取用户积分
        credits = 0
        success, user_credits = db.get_user_credits(user_id)
        if success:
            credits = user_credits

        # 计算用户积分排名
        ranking = 0
        credits_rank = db.get_credits_rank()
        for idx, (tg_id, _) in enumerate(credits_rank, 1):
            if tg_id == user_id:
                ranking = idx
                break

        # 获取观看时长（Plex + Emby 总和，单位：分钟）
        watch_time = 0

        # Plex 观看时长
        plex_info = db.get_plex_info_by_tg_id(user_id)
        if plex_info and plex_info[7]:  # watched_time 字段
            watch_time += int(plex_info[7] * 60)  # 小时转分钟

        # Emby 观看时长
        emby_info = db.get_emby_info_by_tg_id(user_id)
        if emby_info and emby_info[5]:  # emby_watched_time 字段
            watch_time += int(emby_info[5] * 60)  # 小时转分钟

        logger.info(f"用户 {user.username or user.first_name or user_id} 获取仪表盘数据成功")

        return {
            "success": True,
            "data": {
                "credits": round(credits, 2),
                "watchTime": watch_time,
                "ranking": ranking if ranking > 0 else None,
            }
        }
    except Exception as e:
        logger.error(f"获取用户仪表盘数据失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "credits": 0,
                "watchTime": 0,
                "ranking": None,
            }
        }
    finally:
        db.close()


@router.get("/info")
@require_telegram_auth
async def get_user_info(
    request: Request, user: TelegramUser = Depends(get_telegram_user)
):
    """获取用户信息"""
    user_id = user.id
    user_name = user.username or user.first_name
    logger.info(f"开始获取用户 {user_name or user_id} 的详细信息")
    db = DB()
    try:
        tg_id = user_id
        is_admin = False
        if tg_id in settings.TG_ADMIN_CHAT_ID:
            is_admin = True
        user_info = UserInfo(tg_id=tg_id, is_admin=is_admin)

        # 获取Plex信息
        try:
            logger.debug(f"正在查询用户 {get_user_name_from_tg_id(tg_id)} 的Plex信息")
            plex_info = db.get_plex_info_by_tg_id(tg_id)
            if plex_info:
                user_info.plex_info = {
                    "username": plex_info[4],
                    "email": plex_info[3],
                    "watched_time": plex_info[7],
                    "all_lib": plex_info[5] == 1,
                }
                logger.debug(
                    f"用户 {get_user_name_from_tg_id(tg_id)} 的 Plex 信息获取成功"
                )
            else:
                logger.debug(
                    f"用户 {get_user_name_from_tg_id(tg_id)} 没有关联的 Plex 账户"
                )
        except Exception as e:
            logger.error(
                f"获取用户 {get_user_name_from_tg_id(tg_id)} 的 Plex 信息失败: {str(e)}"
            )

        # 获取Emby信息
        try:
            logger.debug(f"正在查询用户 {get_user_name_from_tg_id(tg_id)} 的 Emby 信息")
            emby_info = db.get_emby_info_by_tg_id(tg_id)
            if emby_info:
                user_info.emby_info = {
                    "username": emby_info[0],
                    "watched_time": emby_info[5],
                    "all_lib": emby_info[3] == 1,
                }
                created_at = (
                    Emby().get_user_info_from_username(emby_info[0]).get("date_created")
                )
                if created_at:
                    created_at = created_at.split("T")[0]
                user_info.emby_info["created_at"] = created_at
                logger.debug(
                    f"用户 {get_user_name_from_tg_id(tg_id)} 的 Emby 信息获取成功"
                )
            else:
                logger.debug(
                    f"用户 {get_user_name_from_tg_id(tg_id)} 没有关联的 Emby 账户"
                )
        except Exception as e:
            logger.error(
                f"获取用户 {get_user_name_from_tg_id(tg_id)} 的 Emby 信息失败: {str(e)}"
            )

        # 获取统计信息
        try:
            logger.debug(f"正在查询用户 {get_user_name_from_tg_id(tg_id)} 的统计信息")
            stats_info = db.get_stats_by_tg_id(tg_id)
            if stats_info:
                user_info.credits = stats_info[2]
                user_info.donation = stats_info[1]
                logger.debug(
                    f"用户 {get_user_name_from_tg_id(tg_id)} 的统计信息获取成功"
                )
            else:
                logger.debug(f"用户 {get_user_name_from_tg_id(tg_id)} 没有统计信息")
        except Exception as e:
            logger.error(
                f"获取用户 {get_user_name_from_tg_id(tg_id)} 的统计信息失败: {str(e)}"
            )

        # 获取Overseerr信息
        try:
            logger.debug(
                f"正在查询用户 {get_user_name_from_tg_id(tg_id)} 的Overseerr信息"
            )
            overseerr_info = db.get_overseerr_info_by_tg_id(tg_id)
            if overseerr_info:
                user_info.overseerr_info = {
                    "user_id": overseerr_info[0],
                    "email": overseerr_info[1],
                }
                logger.debug(
                    f"用户 {get_user_name_from_tg_id(tg_id)} 的Overseerr信息获取成功"
                )
            else:
                logger.debug(
                    f"用户 {get_user_name_from_tg_id(tg_id)} 没有关联的Overseerr账户"
                )
        except Exception as e:
            logger.error(
                f"获取用户 {get_user_name_from_tg_id(tg_id)} 的Overseerr信息失败: {str(e)}"
            )

        # 获取邀请码
        try:
            logger.debug(f"正在查询用户 {get_user_name_from_tg_id(tg_id)} 的邀请码")
            codes = db.get_invitation_code_by_owner(tg_id)
            if codes:
                user_info.invitation_codes = codes
                logger.debug(
                    f"用户 {get_user_name_from_tg_id(tg_id)} 的邀请码获取成功，共 {len(codes)} 个"
                )
            else:
                logger.debug(f"用户 {get_user_name_from_tg_id(tg_id)} 没有邀请码")
        except Exception as e:
            logger.error(
                f"获取用户 {get_user_name_from_tg_id(tg_id)} 的邀请码失败: {str(e)}"
            )

        # 获取邀请人数
        try:
            logger.debug(f"正在查询用户 {get_user_name_from_tg_id(tg_id)} 的邀请人数")
            invited_count = db.get_invited_count_by_owner(tg_id)
            user_info.invited_count = invited_count
            logger.debug(
                f"用户 {get_user_name_from_tg_id(tg_id)} 的邀请人数获取成功，共邀请 {invited_count} 人"
            )
        except Exception as e:
            logger.error(
                f"获取用户 {get_user_name_from_tg_id(tg_id)} 的邀请人数失败: {str(e)}"
            )

        logger.info(f"用户 {user_name or user_id} 的信息获取完成")
        return user_info
    except Exception as e:
        logger.error(f"获取用户信息时发生未预期的错误: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户信息失败")
    finally:
        db.close()
        logger.debug("数据库连接已关闭")


@router.get("/recent-activities")
@require_telegram_auth
async def get_recent_activities(
    request: Request,
    user: TelegramUser = Depends(get_telegram_user),
    limit: int = 10,
):
    """获取用户当天的活动记录（包含转盘、21点、竞拍等）"""
    user_id = user.id
    db = DB()

    # 计算当天零点的时间戳
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day).timestamp()
    today_start_int = int(today_start)

    try:
        activities = []

        # 获取转盘记录
        wheel_records = db.cur.execute(
            """SELECT item_name, credits_change, timestamp
               FROM wheel_stats
               WHERE tg_id = ? AND timestamp >= ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (user_id, today_start_int, limit),
        ).fetchall()

        for record in wheel_records:
            item_name, credits_change, timestamp = record
            activities.append({
                "type": "wheel",
                "icon": "mdi-ferris-wheel",
                "title": f"幸运转盘 - {item_name}",
                "time": timestamp,
                "value": credits_change,
                "valueClass": "value-positive" if credits_change >= 0 else "value-negative",
            })

        # 获取21点记录
        blackjack_records = db.cur.execute(
            """SELECT result, credits_change, timestamp
               FROM blackjack_stats
               WHERE tg_id = ? AND timestamp >= ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (user_id, today_start_int, limit),
        ).fetchall()

        result_names = {
            "win": "获胜",
            "blackjack": "黑杰克",
            "dealer_bust": "庄家爆牌",
            "lose": "失败",
            "bust": "爆牌",
            "push": "平局",
        }

        for record in blackjack_records:
            result, credits_change, timestamp = record
            result_text = result_names.get(result, result)
            activities.append({
                "type": "blackjack",
                "icon": "mdi-cards",
                "title": f"21点 - {result_text}",
                "time": timestamp,
                "value": credits_change,
                "valueClass": "value-positive" if credits_change >= 0 else "value-negative",
            })

        # 获取竞拍记录
        try:
            auction_records = db.cur.execute(
                """SELECT a.title, b.bid_amount, b.bid_time
                   FROM auction_bids b
                   JOIN auctions a ON b.auction_id = a.id
                   WHERE b.bidder_id = ? AND b.bid_time >= ?
                   ORDER BY b.bid_time DESC
                   LIMIT ?""",
                (user_id, today_start_int, limit),
            ).fetchall()

            for record in auction_records:
                title, amount, bid_time = record
                activities.append({
                    "type": "auction",
                    "icon": "mdi-gavel",
                    "title": f"竞拍出价 - {title}",
                    "time": bid_time,
                    "value": -amount,
                    "valueClass": "value-negative",
                })
        except Exception as e:
            logger.debug(f"获取竞拍记录失败（表可能不存在）: {e}")

        # 获取 Plex 当天观看时长
        try:
            plex_info = db.get_plex_info_by_tg_id(user_id)
            if plex_info:
                plex_id = plex_info[0]
                duration = get_user_total_duration(
                    Tautulli().get_home_stats(
                        1, "duration", len(Plex().users_by_id), "top_users"
                    )
                )
                play_duration = round(min(float(duration.get(plex_id, 0)), 24), 2)
                if play_duration > 0:
                    activities.append({
                        "type": "watch",
                        "icon": "mdi-play-circle",
                        "title": f"Plex 观看",
                        "time": today_start_int,
                        "value": f"{play_duration}h",
                        "valueClass": "value-positive",
                    })
        except Exception as e:
            logger.debug(f"获取 Plex 观看时长失败: {e}")

        # 获取 Emby 当天观看时长
        try:
            emby_info = db.get_emby_info_by_tg_id(user_id)
            if emby_info:
                emby_id = emby_info[1]
                emby_watched_time_init = emby_info[5]
                emby = Emby()
                duration = emby.get_user_total_play_time()
                playduration = round(float(duration.get(emby_id, 0)) / 3600, 2)
                today_watch = max(playduration - emby_watched_time_init, 0)
                if today_watch > 0:
                    activities.append({
                        "type": "watch",
                        "icon": "mdi-play-circle",
                        "title": f"Emby 观看",
                        "time": today_start_int,
                        "value": f"{round(today_watch, 2)}h",
                        "valueClass": "value-positive",
                    })
        except Exception as e:
            logger.debug(f"获取 Emby 观看时长失败: {e}")

        # 按时间排序并限制数量
        activities.sort(key=lambda x: x["time"], reverse=True)
        activities = activities[:limit]

        # 转换时间戳为相对时间
        now_ts = int(time())
        for activity in activities:
            timestamp = activity["time"]
            diff = now_ts - timestamp

            if diff < 60:
                activity["time"] = "刚刚"
            elif diff < 3600:
                activity["time"] = f"{diff // 60}分钟前"
            elif diff < 86400:
                activity["time"] = f"{diff // 3600}小时前"
            elif diff < 604800:
                activity["time"] = f"{diff // 86400}天前"
            else:
                activity["time"] = datetime.fromtimestamp(timestamp).strftime("%m-%d")

            value = activity["value"]
            if isinstance(value, (int, float)):
                activity["value"] = f"+{value}" if value >= 0 else str(value)

        return {"success": True, "activities": activities}

    except Exception as e:
        logger.error(f"获取用户最近活动记录失败: {e}")
        return {"success": False, "activities": [], "error": str(e)}
    finally:
        db.close()


@router.get("/recent-games")
@require_telegram_auth
async def get_recent_games(
    request: Request,
    user: TelegramUser = Depends(get_telegram_user),
    limit: int = 2,
):
    """获取用户最近玩过的游戏类型（最多2个）"""
    user_id = user.id
    db = DB()

    now = datetime.now()
    days_ago_30 = datetime(now.year, now.month, now.day) - timedelta(days=30)
    time_threshold = int(days_ago_30.timestamp())

    try:
        games_with_time = []

        # 检查转盘
        wheel_record = db.cur.execute(
            """SELECT MAX(timestamp) FROM wheel_stats
               WHERE tg_id = ? AND timestamp >= ?""",
            (user_id, time_threshold),
        ).fetchone()
        if wheel_record and wheel_record[0]:
            games_with_time.append(("wheel", wheel_record[0]))

        # 检查21点
        blackjack_record = db.cur.execute(
            """SELECT MAX(timestamp) FROM blackjack_stats
               WHERE tg_id = ? AND timestamp >= ?""",
            (user_id, time_threshold),
        ).fetchone()
        if blackjack_record and blackjack_record[0]:
            games_with_time.append(("blackjack", blackjack_record[0]))

        # 检查竞拍
        try:
            auction_record = db.cur.execute(
                """SELECT MAX(b.bid_time) FROM auction_bids b
                   WHERE b.bidder_id = ? AND b.bid_time >= ?""",
                (user_id, time_threshold),
            ).fetchone()
            if auction_record and auction_record[0]:
                games_with_time.append(("auction", auction_record[0]))
        except Exception as e:
            logger.debug(f"获取竞拍记录失败: {e}")

        # 按时间排序
        games_with_time.sort(key=lambda x: x[1], reverse=True)
        recent_games = games_with_time[:limit]

        game_info = {
            "wheel": {
                "id": "wheel",
                "name": "幸运转盘",
                "icon": "mdi-ferris-wheel",
                "description": "转动命运之轮，赢取大奖",
                "route": "wheel",
            },
            "blackjack": {
                "id": "blackjack",
                "name": "21点",
                "icon": "mdi-cards",
                "description": "经典21点游戏，考验运气与策略",
                "route": "blackjack",
            },
            "auction": {
                "id": "auction",
                "name": "竞拍活动",
                "icon": "mdi-gavel",
                "description": "珍稀物品竞拍，出价赢宝",
                "route": "auction",
            },
        }

        game_types = []
        for game_type, last_played in recent_games:
            if game_type in game_info:
                game_types.append(game_info[game_type])

        return {"success": True, "games": game_types}

    except Exception as e:
        logger.error(f"获取用户最近游戏记录失败: {e}")
        return {"success": False, "games": [], "error": str(e)}
    finally:
        db.close()


@router.get("/users")
@require_telegram_auth
async def get_all_users(
    request: Request, user: TelegramUser = Depends(get_telegram_user)
):
    """获取所有用户信息（用于用户选择）- 只返回有账号的用户"""
    db = DB()
    try:
        users = []

        # 获取所有有 statistics 记录的用户
        all_stats = db.cur.execute(
            "SELECT tg_id, credits FROM statistics"
        ).fetchall()

        for stats in all_stats:
            tg_id = stats[0]
            # 检查用户是否有 Plex 或 Emby 账号
            plex_info = db.get_plex_info_by_tg_id(tg_id)
            emby_info = db.get_emby_info_by_tg_id(tg_id)

            if plex_info or emby_info:
                username = None
                if plex_info:
                    username = plex_info[4]  # plex_username
                elif emby_info:
                    username = emby_info[0]  # emby_username

                users.append({
                    "tg_id": tg_id,
                    "username": username,
                    "display_name": get_user_name_from_tg_id(tg_id) or username,
                })

        return {"success": True, "users": users}
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        return {"success": False, "users": [], "error": str(e)}
    finally:
        db.close()
