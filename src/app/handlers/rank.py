from app.config import settings
from app.db import DB
from app.emby import Emby
from app.log import logger
from app.utils import get_user_name_from_tg_id, send_message, is_admin
from app.update_db import push_emby_watch_rank
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import requests
from datetime import datetime, timedelta


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


# 手动触发 Emby 观看时长日榜/周榜
async def emby_day_rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_emby_rank_inline(update, context, days=1, top_n=10)


async def emby_week_rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_emby_rank_inline(update, context, days=7, top_n=20)


emby_day_rank_handler = CommandHandler("emby_day_rank", emby_day_rank)
emby_week_rank_handler = CommandHandler("emby_week_rank", emby_week_rank)

__all__.extend([
    "emby_day_rank_handler",
    "emby_week_rank_handler",
])


async def _send_emby_rank_inline(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int, top_n: int) -> None:
    chat_id = update.effective_chat.id
    try:
        db = DB()
        # 优先使用与 debug 一致的查询组合（delta + ReplaceUserId=True）
        lines = []
        rows = _query_emby_rank_via_plugin(days)
        if rows:
            for idx, (uid_or_name, hours) in enumerate(rows[:top_n], start=1):
                name = str(uid_or_name)
                info = db.get_emby_info_by_emby_id(name)
                if info and info[2] is not None:
                    name = get_user_name_from_tg_id(info[2]) or info[0] or name
                lines.append(f"{idx}. {name}: {hours:.2f} 小时")
        else:
            # 回退到本地聚合
            aggregated = db.get_emby_watch_rank_last_days(days=days, limit=top_n)
            for idx, (emby_user_id, username, hours) in enumerate(aggregated, start=1):
                name = username or emby_user_id
                info = db.get_emby_info_by_emby_id(emby_user_id)
                if info and info[2] is not None:
                    name = get_user_name_from_tg_id(info[2]) or info[0] or name
                lines.append(f"{idx}. {name}: {hours:.2f} 小时")

        if not lines:
            await send_message(chat_id, f"Emby 观看时长榜通知：近{days}天无数据（可用 /emby_rank_debug 排查）", context)
            return

        title = "【Emby 观看时长榜 - 日榜】\n\n" if days == 1 else f"【Emby 观看时长榜 - 近{days}天】\n\n"
        text = title + "\n".join(lines)
        await send_message(chat_id, text, context)
    except Exception as e:
        await send_message(chat_id, f"生成榜单失败: {e}", context)


def _query_emby_rank_via_plugin(days: int) -> list[tuple[str, float]]:
    """与 /emby_rank_debug 一致的查询组合，返回 [(uid_or_name, hours), ...]"""
    if days <= 0:
        days = 1
    try:
        emby = Emby()
        end = datetime.now(settings.TZ)
        start = end - timedelta(days=days)
        start_time = start.strftime("%Y-%m-%d %H:%M:%S")
        end_time = end.strftime("%Y-%m-%d %H:%M:%S")

        sql = (
            "SELECT UserId, SUM(PlayDuration - PauseDuration) AS WatchTime "
            "FROM PlaybackActivity "
            f"WHERE DateCreated >= '{start_time}' AND DateCreated < '{end_time}' "
            "GROUP BY UserId ORDER BY WatchTime DESC"
        )
        headers = {"accept": "application/json", "Content-Type": "application/json"}
        paths = [
            "/user_usage_stats/submit_custom_query",
            "/emby/user_usage_stats/submit_custom_query",
        ]
        rows = []
        for path in paths:
            try:
                resp = requests.post(
                    url=emby.base_url.rstrip("/") + path,
                    params={"api_key": emby.api_token},
                    headers=headers,
                    json={"CustomQueryString": sql, "ReplaceUserId": True},
                    timeout=8,
                )
                if resp.ok:
                    js = resp.json() or {}
                    rows = js.get("results", []) or []
                    if rows:
                        break
            except Exception:
                continue
        results: list[tuple[str, float]] = []
        for r in rows:
            try:
                uid_or_name, secs = r
                hours = float(secs or 0) / 3600.0
                results.append((str(uid_or_name), hours))
            except Exception:
                continue
        return results
    except Exception:
        return []


# 调试命令：检查 Emby user_usage_stats 聚合可用性
async def emby_rank_debug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    try:
        if not (settings.EMBY_BASE_URL and settings.EMBY_API_TOKEN):
            await send_message(chat_id, "错误：未配置 EMBY_BASE_URL/EMBY_API_TOKEN", context)
            return

        days = 1
        emby = Emby()
        end = datetime.now(settings.TZ)
        start = end - timedelta(days=days)
        start_time = start.strftime("%Y-%m-%d %H:%M:%S")
        end_time = end.strftime("%Y-%m-%d %H:%M:%S")

        attempts = [
            (
                "delta",
                (
                    "SELECT UserId, SUM(PlayDuration - PauseDuration) AS WatchTime "
                    "FROM PlaybackActivity "
                    f"WHERE DateCreated >= '{start_time}' AND DateCreated < '{end_time}' "
                    "GROUP BY UserId ORDER BY WatchTime DESC"
                ),
                True,
            ),
            (
                "sum",
                (
                    "SELECT UserId, SUM(PlayDuration) AS WatchTime "
                    "FROM PlaybackActivity "
                    f"WHERE DateCreated >= '{start_time}' AND DateCreated < '{end_time}' "
                    "GROUP BY UserId ORDER BY WatchTime DESC"
                ),
                True,
            ),
            (
                "utc",
                (
                    "SELECT UserId, SUM(PlayDuration) AS WatchTime "
                    "FROM PlaybackActivity "
                    f"WHERE DateCreatedUtc >= '{start_time}' AND DateCreatedUtc < '{end_time}' "
                    "GROUP BY UserId ORDER BY WatchTime DESC"
                ),
                False,
            ),
        ]
        paths = [
            "/user_usage_stats/submit_custom_query",
            "/emby/user_usage_stats/submit_custom_query",
        ]

        headers = {"accept": "application/json", "Content-Type": "application/json"}
        results_lines = []
        any_rows = False
        for tag, sql, replace_flag in attempts:
            for path in paths:
                try:
                    resp = requests.post(
                        url=emby.base_url.rstrip("/") + path,
                        params={"api_key": emby.api_token},
                        headers=headers,
                        json={
                            "CustomQueryString": sql,
                            "ReplaceUserId": bool(replace_flag),
                        },
                        timeout=8,
                    )
                    if resp.ok:
                        js = resp.json() or {}
                        rows = js.get("results", []) or []
                        results_lines.append(
                            f"[{tag}] path={path} replace={replace_flag} -> rows={len(rows)}"
                        )
                        if rows and not any_rows:
                            any_rows = True
                            sample = []
                            for r in rows[:3]:
                                try:
                                    uid, secs = r
                                    sample.append(f"- {uid}: {round(float(secs)/3600,2)}h")
                                except Exception:
                                    continue
                            if sample:
                                results_lines.append("示例:\n" + "\n".join(sample))
                    else:
                        results_lines.append(
                            f"[{tag}] path={path} replace={replace_flag} -> HTTP {resp.status_code}"
                        )
                except Exception as e:
                    results_lines.append(
                        f"[{tag}] path={path} replace={replace_flag} -> error: {e}"
                    )

        # 本地聚合的可用性
        db = DB()
        local_rows = db.get_emby_watch_rank_last_days(days=1, limit=3)
        if local_rows:
            local_preview = [
                f"- {row[1] or row[0]}: {round(row[2],2)}h" for row in local_rows
            ]
            results_lines.append("本地聚合(近1天)示例:\n" + "\n".join(local_preview))

        title = f"Emby Rank Debug (days={days})\n时间窗口: {start_time} ~ {end_time}"
        body = title + "\n\n" + ("\n".join(results_lines) if results_lines else "无返回")
        await send_message(chat_id, body[:3500], context)
    except Exception as e:
        await send_message(chat_id, f"调试失败: {e}", context)


emby_rank_debug_handler = CommandHandler("emby_rank_debug", emby_rank_debug)
__all__.append("emby_rank_debug_handler")


# 强制使用与 Debug 一致的查询组合输出榜单（备用）
async def emby_day_rank_force(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    try:
        if not (settings.EMBY_BASE_URL and settings.EMBY_API_TOKEN):
            await send_message(chat_id, "错误：未配置 EMBY_BASE_URL/EMBY_API_TOKEN", context)
            return

        emby = Emby()
        end = datetime.now(settings.TZ)
        start = end - timedelta(days=1)
        start_time = start.strftime("%Y-%m-%d %H:%M:%S")
        end_time = end.strftime("%Y-%m-%d %H:%M:%S")

        sql = (
            "SELECT UserId, SUM(PlayDuration - PauseDuration) AS WatchTime "
            "FROM PlaybackActivity "
            f"WHERE DateCreated >= '{start_time}' AND DateCreated < '{end_time}' "
            "GROUP BY UserId ORDER BY WatchTime DESC"
        )
        headers = {"accept": "application/json", "Content-Type": "application/json"}
        paths = [
            "/user_usage_stats/submit_custom_query",
            "/emby/user_usage_stats/submit_custom_query",
        ]

        rows = []
        for path in paths:
            try:
                resp = requests.post(
                    url=emby.base_url.rstrip("/") + path,
                    params={"api_key": emby.api_token},
                    headers=headers,
                    json={"CustomQueryString": sql, "ReplaceUserId": True},
                    timeout=8,
                )
                if resp.ok:
                    js = resp.json() or {}
                    rows = js.get("results", []) or []
                    if rows:
                        break
            except Exception:
                continue

        if not rows:
            await send_message(chat_id, "强制榜单：无数据（请用 /emby_rank_debug 排查）", context)
            return

        # 构建前 20 名
        top_n = min(20, len(rows))
        db = DB()
        lines = []
        for idx, r in enumerate(rows[:top_n], start=1):
            try:
                uid_or_name, secs = r
                hours = float(secs or 0) / 3600.0
                name = str(uid_or_name)
                info = db.get_emby_info_by_emby_id(name)
                if info and info[2] is not None:
                    # 若匹配到 emby_id，则用TG名
                    name = get_user_name_from_tg_id(info[2]) or info[0] or name
                lines.append(f"{idx}. {name}: {hours:.2f} 小时")
            except Exception:
                continue

        text = "【Emby 观看时长榜 - 日榜(强制)】\n\n" + "\n".join(lines)
        await send_message(chat_id, text, context)
    except Exception as e:
        await send_message(chat_id, f"强制榜单失败: {e}", context)


emby_day_rank_force_handler = CommandHandler("emby_day_rank_force", emby_day_rank_force)
__all__.append("emby_day_rank_force_handler")
