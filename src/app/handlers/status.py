from app.config import settings
from app.utils import send_message, is_admin
from app.emby import Emby
from app.tautulli import Tautulli
import requests
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes


# 获取当前注册状态
async def get_register_status(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    chat_id = update._effective_chat.id
    text = f"""
Plex: {"可注册" if settings.PLEX_REGISTER else "注册关闭"}
Emby: {"可注册" if settings.EMBY_REGISTER else "注册关闭"}
    """
    await send_message(chat_id=chat_id, text=text, parse_mode="HTML", context=context)


# 管理员命令: 设置注册状态
async def set_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await send_message(chat_id=chat_id, text="错误：越权操作", context=context)
        return
    text = update.message.text
    text = text.split()
    if len(text) != 3:
        await send_message(
            chat_id=chat_id, text="错误：请按照格式填写", context=context
        )
        return
    server, flag = text[1:]
    if server.lower() not in {"plex", "emby"}:
        await send_message(
            chat_id=chat_id, text="错误: 请指定正确的媒体服务器", context=context
        )
        return
    if server.lower() == "plex":
        settings.PLEX_REGISTER = True if flag != "0" else False
    elif server.lower() == "emby":
        settings.EMBY_REGISTER = True if flag != "0" else False
    await send_message(
        chat_id=chat_id,
        text=f"信息: 设置 {server} 注册状态为 {'开启' if flag != '0' else '关闭'}",
        context=context,
    )


get_register_status_handler = CommandHandler("register_status", get_register_status)
set_register_handler = CommandHandler("set_register", set_register)

__all__ = ["get_register_status_handler", "set_register_handler"]


# 实时在线人数（Plex + Emby）
async def online_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update._effective_chat.id

    lines = []

    # Plex 在线（通过 Tautulli）
    try:
        plex_online = 0
        plex_lines = []
        if settings.TAUTULLI_URL and settings.TAUTULLI_APIKEY:
            data = Tautulli().get_activity() or {}
            sessions = data.get("sessions", []) or []
            # 仅统计正在播放（排除暂停/空闲）
            playing = [
                s
                for s in sessions
                if str(s.get("state", "")).lower() in {"playing", "buffering"}
                and str(s.get("media_type", "")).lower() in {"movie", "episode", "track"}
            ]
            plex_online = len(playing)
            for s in playing[:10]:
                user = s.get("user") or s.get("friendly_name") or s.get("username") or "用户"
                title = s.get("full_title") or s.get("title") or s.get("grandparent_title") or "播放中"
                player = s.get("player") or {}
                device = player.get("product") or player.get("platform") or s.get("player") or "客户端"
                plex_lines.append(f"- {user} | {title} | {device}")
        lines.append(
            """
<strong>Plex 在线</strong>
{}
            """.format(
                f"当前 {plex_online} 人在播\n" + ("\n".join(plex_lines) if plex_lines else "")
            )
        )
    except Exception as e:
        lines.append(f"Plex 在线信息获取失败: {e}")

    # Emby 在线（直接查询 Sessions）
    try:
        emby_online = 0
        emby_lines = []
        if settings.EMBY_BASE_URL and settings.EMBY_API_TOKEN:
            emby = Emby()
            resp = requests.get(
                f"{emby.base_url.rstrip('/')}/Sessions",
                params={"api_key": emby.api_token, "ActiveWithinSeconds": 600},
                timeout=8,
            )
            if resp.ok:
                sessions = resp.json() or []
                # 仅统计正在播放的视频/音频，排除暂停与空闲
                def is_playing(sess):
                    now = sess.get("NowPlayingItem") or {}
                    media_type = str(now.get("MediaType", "")).lower()
                    if media_type not in {"video", "audio"}:
                        return False
                    ps = sess.get("PlayState") or {}
                    # 有些版本没有 IsPlaying 字段，保守地用 IsPaused 判断
                    if ps.get("IsPaused") is True:
                        return False
                    return True

                playing = [s for s in sessions if is_playing(s)]
                emby_online = len(playing)
                for s in playing[:10]:
                    user = s.get("UserName") or s.get("UserId") or "用户"
                    now = s.get("NowPlayingItem") or {}
                    title = now.get("Name") or now.get("SeriesName") or "播放中"
                    device = s.get("Client") or s.get("DeviceName") or "客户端"
                    emby_lines.append(f"- {user} | {title} | {device}")
        lines.append(
            """
<strong>Emby 在线</strong>
{}
            """.format(
                f"当前 {emby_online} 人在播\n" + ("\n".join(emby_lines) if emby_lines else "")
            )
        )
    except Exception as e:
        lines.append(f"Emby 在线信息获取失败: {e}")

    body = "\n".join(lines).strip()
    if not body:
        body = "暂无在线信息"
    await send_message(chat_id=chat_id, text=body, parse_mode="HTML", context=context)


online_status_handler = CommandHandler("online", online_status)

__all__.append("online_status_handler")
