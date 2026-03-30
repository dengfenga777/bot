"""每日签到 API 路由"""
import logging
from datetime import datetime, timedelta

from app.config import settings
from app.db import DB
from app.utils.utils import get_user_name_from_tg_id
from app.webapp.auth import get_telegram_user
from app.webapp.middlewares import require_telegram_auth
from app.webapp.schemas import TelegramUser
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/checkin", tags=["checkin"])


def _calc_reward(streak: int) -> float:
    """根据连续签到天数计算积分奖励"""
    if streak > 0 and streak % 30 == 0:
        return 10.0
    if streak > 0 and streak % 14 == 0:
        return 5.0
    if streak > 0 and streak % 7 == 0:
        return 3.0
    return 1.0


def _today_in_tz():
    """返回北京时间下的今天日期。"""
    return datetime.now(settings.TZ).date()


def _get_checkin_availability(db: DB, tg_id: int) -> tuple[bool, str]:
    """返回当前用户是否可签到以及禁用原因。"""
    if not settings.CHECKIN_ENABLED:
        return False, "签到功能未开启"

    plex_info = db.get_plex_info_by_tg_id(tg_id)
    emby_info = db.get_emby_info_by_tg_id(tg_id)
    if not plex_info and not emby_info:
        return False, "请先在 Bot 中绑定 Plex 或 Emby 账号后再签到"

    return True, ""


@require_telegram_auth
@router.post("")
async def do_checkin(user: TelegramUser = Depends(get_telegram_user)):
    """执行每日签到"""
    db = DB()
    today_date = _today_in_tz()
    today = today_date.strftime("%Y-%m-%d")
    month = today[:7]

    try:
        db.sync_checkin_total_rank_medals()
        can_checkin, disabled_reason = _get_checkin_availability(db, user.id)
        if not can_checkin:
            raise HTTPException(status_code=403, detail=disabled_reason)

        # 检查今日是否已签到
        if db.get_checkin_today(user.id, today):
            return {"success": False, "message": "今日已签到，明天再来吧 ✨"}

        # 计算连续签到天数
        last = db.get_checkin_last(user.id)
        if last:
            last_date = datetime.fromisoformat(last["checkin_date"]).date()
            yesterday = today_date - timedelta(days=1)
            streak = last["streak"] + 1 if last_date == yesterday else 1
        else:
            streak = 1

        reward = _calc_reward(streak)

        # 记录签到 + 发放积分
        if not db.add_checkin(user.id, today, streak, month, reward):
            raise HTTPException(status_code=500, detail="签到记录写入失败，请稍后重试")
        stats = db.get_stats_by_tg_id(user.id)
        if stats:
            new_credits = round((stats["credits"] or 0) + reward, 2)
            db.update_user_credits(new_credits, tg_id=user.id)
        else:
            new_credits = reward
            db.cur.execute(
                "INSERT INTO statistics (tg_id, credits, donation) VALUES (?, ?, 0)",
                (user.id, new_credits),
            )
            db.con.commit()

        db.sync_checkin_total_rank_medals()
        month_count = db.get_checkin_month_count(user.id, month)

        # 构建奖励消息
        milestone_msg = ""
        if streak % 30 == 0:
            milestone_msg = f"🏆 连续签到 {streak} 天！超级里程碑！"
        elif streak % 14 == 0:
            milestone_msg = f"🎉 连续签到 {streak} 天！双周里程碑！"
        elif streak % 7 == 0:
            milestone_msg = f"🌟 连续签到 {streak} 天！周签里程碑！"

        return {
            "success": True,
            "message": "签到成功！",
            "data": {
                "streak": streak,
                "reward": reward,
                "new_credits": new_credits,
                "month_count": month_count,
                "milestone_msg": milestone_msg,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"签到失败 user={user.id}: {e}")
        raise HTTPException(status_code=500, detail="签到失败，请稍后重试")
    finally:
        db.close()


@require_telegram_auth
@router.get("/status")
async def get_checkin_status(user: TelegramUser = Depends(get_telegram_user)):
    """获取当前用户签到状态"""
    db = DB()
    today = _today_in_tz().strftime("%Y-%m-%d")
    try:
        db.sync_checkin_total_rank_medals()
        status = db.get_checkin_status(user.id, today)
        can_checkin, disabled_reason = _get_checkin_availability(db, user.id)
        next_reward = _calc_reward(status["streak"] + 1)
        return {
            "success": True,
            "data": {
                **status,
                "next_reward": next_reward,
                "today": today,
                "can_checkin": can_checkin,
                "disabled_reason": disabled_reason,
            },
        }
    finally:
        db.close()


@router.get("/leaderboard")
async def get_checkin_leaderboard():
    """本月签到排行榜（公开，无需登录，仅展示前三）"""
    month = _today_in_tz().strftime("%Y-%m")
    db = DB()
    try:
        db.sync_checkin_total_rank_medals()
        rows = db.get_checkin_monthly_leaderboard(month)[:3]
        medal_map = db.get_users_medals_map([row["tg_id"] for row in rows]) if rows else {}
        result = []
        for rank, row in enumerate(rows, start=1):
            tg_id = row["tg_id"]
            name = get_user_name_from_tg_id(tg_id) or f"用户{tg_id}"
            result.append({
                "rank": rank,
                "tg_id": tg_id,
                "name": name,
                "days": row["days"],
                "total_credits": round(row["total_credits"] or 0, 2),
                "medals": medal_map.get(tg_id, []),
            })
        return {"success": True, "data": result, "month": month}
    finally:
        db.close()
