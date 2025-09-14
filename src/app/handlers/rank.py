from app.config import settings
from app.db import DB
from app.emby import Emby
from app.log import logger
from app.utils import get_user_name_from_tg_id, send_message, is_admin
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes


# 花币榜
async def credits_rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update._effective_chat.id
    _db = DB()
    res = _db.get_credits_rank()
    rank = [
        f"{i}. {get_user_name_from_tg_id(info[0])}: {info[1]:.2f}"
        for i, info in enumerate(res, 1)
        if i <= 30
    ]

    body_text = """
<strong>{}榜</strong>
==================
{}
==================

⚠️只统计 TG 绑定用户
    """.format(settings.MONEY_NAME, "\n".join(rank))
    logger.info(body_text)
    await send_message(
        chat_id=chat_id, text=body_text, parse_mode="HTML", context=context
    )


# 捐赠榜
async def donation_rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update._effective_chat.id
    _db = DB()
    res = _db.get_donation_rank()
    rank = [
        f"{i}. {get_user_name_from_tg_id(info[0])}: {info[1]:.2f}"
        for i, info in enumerate(res, 1)
        if info[1] > 0
    ]

    body_text = """
<strong>捐赠榜</strong>
==================
{}
==================

衷心感谢各位的支持!
    """.format("\n".join(rank))
    logger.debug(body_text)
    await send_message(
        chat_id=chat_id, text=body_text, parse_mode="HTML", context=context
    )


# 观看时长榜
async def watched_time_rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update._effective_chat.id
    _db = DB()
    res = _db.get_plex_watched_time_rank()
    rank = [
        f"{i}. {info[2]}: {info[3]:.2f}" for i, info in enumerate(res, 1) if i <= 15
    ]
    emby_res = _db.get_emby_watched_time_rank()
    emby_rank = [
        f"{i}. {info[1]}: {info[2]:.2f}"
        for i, info in enumerate(emby_res, 1)
        if i <= 15
    ]
    body_text = """
<strong>观看时长榜 (Hour)</strong>
==================

------ Plex ------
{}

------ Emby ------
{}
    """.format("\n".join(rank), "\n".join(emby_rank))
    await send_message(
        chat_id=chat_id, text=body_text, parse_mode="HTML", context=context
    )


# 合并观看时长榜（Plex + Emby）
async def watched_time_rank_combined(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    chat_id = update._effective_chat.id
    _db = DB()

    # 拉取两端排行榜原始数据
    plex_rows = _db.get_plex_watched_time_rank()  # (plex_id,tg_id,plex_username,watched_time,is_premium)
    emby_rows = _db.get_emby_watched_time_rank()  # (emby_id,emby_username,emby_watched_time,is_premium,tg_id)

    # 聚合逻辑：优先按 tg_id 合并；无 tg 绑定时按平台+用户名单独统计
    totals = {}

    def add_total(key, name_hint, hours):
        if key not in totals:
            totals[key] = {"name_hint": name_hint, "hours": 0.0}
        totals[key]["hours"] += float(hours or 0)

    # Plex 聚合
    for row in plex_rows:
        plex_id, tg_id, plex_username, watched_time, _is_premium = row
        key = tg_id if tg_id is not None else f"plex::{plex_username}"
        add_total(key, plex_username, watched_time)

    # Emby 聚合
    for row in emby_rows:
        emby_id, emby_username, emby_watched_time, _is_premium, tg_id = row
        key = tg_id if tg_id is not None else f"emby::{emby_username}"
        add_total(key, emby_username, emby_watched_time)

    # 生成展示用排名（取前 15）
    combined = sorted(
        [
            (
                i_key,
                get_user_name_from_tg_id(i_key)
                if isinstance(i_key, int)
                else info["name_hint"],
                info["hours"],
            )
            for i_key, info in totals.items()
            if info["hours"] > 0
        ],
        key=lambda x: x[2],
        reverse=True,
    )[:15]

    rank_lines = [f"{i}. {name}: {hours:.2f}" for i, (key, name, hours) in enumerate(combined, 1)]

    body_text = """
<strong>观看时长榜 (Hour) - 合并</strong>
==================
{}
==================

⚠️优先按已绑定的 Telegram 用户合并统计；未绑定用户按平台用户名分别统计
    """.format("\n".join(rank_lines))
    await send_message(
        chat_id=chat_id, text=body_text, parse_mode="HTML", context=context
    )


# 设备榜
async def device_rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update._effective_chat.id
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await send_message(chat_id=chat_id, text="错误：越权操作", context=context)
        return
    emby = Emby()
    devices_data = sorted(
        emby.get_devices_per_user(), key=lambda x: len(x["devices"]), reverse=True
    )
    rank = [
        f"{i}. {user_devices.get('user_name')}: 设备 {len(user_devices.get('devices'))}, 客户端 {len(user_devices.get('clients'))}, IP {len(user_devices.get('ip'))}"
        for i, user_devices in enumerate(devices_data[:30], 1)
    ]

    body_text = """
<strong>设备榜</strong>
==================
{}
==================
""".format("\n".join(rank))
    logger.debug(body_text)
    await send_message(
        chat_id=chat_id, text=body_text, parse_mode="HTML", context=context
    )


credits_rank_handler = CommandHandler("credits_rank", credits_rank)
donation_rank_handler = CommandHandler("donation_rank", donation_rank)
watched_time_rank_handler = CommandHandler("play_duration_rank", watched_time_rank)
watched_time_rank_combined_handler = CommandHandler(
    "play_duration_rank_all", watched_time_rank_combined
)
device_rank_handler = CommandHandler("device_rank", device_rank)

__all__ = [
    "credits_rank_handler",
    "donation_rank_handler",
    "watched_time_rank_handler",
    "watched_time_rank_combined_handler",
    "device_rank_handler",
]
