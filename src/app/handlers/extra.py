import random
from datetime import datetime

from app.config import settings
from app.db import DB
from app.emby import Emby
from app.log import logger
from app.utils import send_message
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes


async def register_emby(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """自助注册 Emby 账户: /register_emby 用户名

    创建用户并随机生成密码，发送给用户。随后可用 /bind_emby 绑定。
    """
    chat_id = update.effective_chat.id
    text = (update.message.text or "").split()

    if len(text) != 2:
        await send_message(chat_id=chat_id, text="错误：用法 /register_emby 用户名", context=context)
        return

    if not settings.EMBY_REGISTER:
        await send_message(chat_id=chat_id, text="错误：Emby 暂停注册", context=context)
        return

    username = text[1]
    db = DB()

    # 已存在则阻止
    if db.get_emby_info_by_emby_username(username):
        db.close()
        await send_message(chat_id=chat_id, text="错误：该用户名已存在", context=context)
        return

    emby = Emby()
    ok, uid_or_err = emby.add_user(username=username)
    if not ok:
        db.close()
        await send_message(chat_id=chat_id, text=f"错误：创建失败：{uid_or_err}", context=context)
        return

    user_id = uid_or_err
    # 生成随机密码并设置
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
    pwd = "".join(random.choice(alphabet) for _ in range(max(4, settings.EMBY_DEFAULT_PASSWORD_LEN)))
    ok, msg = emby.set_user_password(user_id, pwd)
    if not ok:
        logger.warning(f"设置密码失败: {msg}")

    # 写入本地数据库（先不绑定 tg，等待用户自助 /bind_emby）
    db.add_emby_user(emby_username=username, emby_id=user_id, tg_id=chat_id)
    db.close()

    await send_message(
        chat_id=chat_id,
        text=(
            f"🎉 注册成功\n\n"
            f"• 用户名: {username}\n"
            f"• 密码: {pwd}\n"
            f"• 提示: 请尽快登录 Emby 修改密码，然后使用 /bind_emby {username} 绑定机器人"
        ),
        context=context,
    )


async def checkin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """每日签到，获得随机奖励到花币。"""
    chat_id = update.effective_chat.id
    if not settings.CHECKIN_ENABLED:
        await send_message(chat_id=chat_id, text="签到未开启", context=context)
        return

    today = datetime.now(settings.TZ).strftime("%Y-%m-%d")
    db = DB()
    last = db.get_last_checkin_date(chat_id)

    if last == today:
        db.close()
        await send_message(chat_id=chat_id, text="您今天已经签过到了，明天再来~", context=context)
        return

    # 奖励随机范围
    reward = random.randint(settings.CHECKIN_REWARD_MIN, settings.CHECKIN_REWARD_MAX)

    # 确保统计记录存在
    stats = db.get_stats_by_tg_id(chat_id)
    if not stats:
        db.add_user_data(chat_id, credits=0, donation=0)
        stats = db.get_stats_by_tg_id(chat_id)

    current = stats[2]
    new_credits = (current or 0) + reward
    db.update_user_credits(new_credits, tg_id=chat_id)
    db.set_last_checkin_date(chat_id, today)
    db.close()

    await send_message(
        chat_id=chat_id,
        text=f"🎯 签到成功：+{reward} {settings.MONEY_NAME}，当前共 {new_credits} {settings.MONEY_NAME}",
        context=context,
    )


register_emby_handler = CommandHandler("register_emby", register_emby)
checkin_handler = CommandHandler("checkin", checkin)

__all__ = [
    "register_emby_handler",
    "checkin_handler",
]
