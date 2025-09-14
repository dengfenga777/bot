from time import time

from app.config import settings
from app.db import DB
from app.emby import Emby
from app.utils import (
    get_user_name_from_tg_id,
    send_message,
)
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes


async def bind_emby(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = update.message.text
    text = text.split()
    if len(text) != 2:
        await send_message(
            chat_id=chat_id, text="错误：请按照格式填写", context=context
        )
        return
    emby_username = text[1]
    db = DB()
    info = db.get_emby_info_by_tg_id(chat_id)
    if info:
        db.close()
        await send_message(
            chat_id=chat_id,
            text="信息: 已绑定 Emby 账户, 请勿重复操作",
            context=context,
        )
        return
    emby = Emby()
    # 检查 emby 用户是否存在
    uid = emby.get_uid_from_username(emby_username)
    if not uid:
        db.close()
        await send_message(
            chat_id=chat_id, text=f"错误: {emby_username} 不存在", context=context
        )
        return
    emby_info = db.get_emby_info_by_emby_username(emby_username)
    # 更新 emby 用户表
    # todo: 更新观看时间等信息
    if emby_info:
        if emby_info[2]:
            db.close()
            await send_message(
                chat_id=chat_id, text="错误：该 Emby 账户已经绑定 TG", context=context
            )
            return
        emby_credits = emby_info[6]
        # 更新 tg id
        db.update_user_tg_id(chat_id, emby_id=uid)
        # 清空 emby 用户表中的花币信息
        db.update_user_credits(0, emby_id=uid)
    else:
        emby_credits = 0
        db.add_emby_user(emby_username, emby_id=uid, tg_id=chat_id)
    # 更新用户数据表
    stats_info = db.get_stats_by_tg_id(chat_id)
    if stats_info:
        tg_user_credits = stats_info[2] + emby_credits
        db.update_user_credits(tg_user_credits, tg_id=chat_id)
    else:
        db.add_user_data(chat_id, credits=emby_credits)

    db.close()
    await send_message(
        chat_id=chat_id,
        text=f"信息： 绑定 Emby 用户 {emby_username} 成功，请加入群组 {settings.TG_GROUP} 并仔细阅读群置顶",
        context=context,
    )


async def unbind_emby(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """解绑当前 Telegram 用户与其 Emby 账户的绑定"""
    chat_id = update.effective_chat.id
    db = DB()
    try:
        info = db.get_emby_info_by_tg_id(chat_id)
        if not info:
            await send_message(chat_id=chat_id, text="错误：未绑定 Emby 账户", context=context)
            return
        emby_id = info[1]
        emby_username = info[0]
        ok = db.update_user_tg_id(None, emby_id=emby_id)
        if not ok:
            await send_message(chat_id=chat_id, text="错误：数据库操作失败，请稍后重试", context=context)
            return
        await send_message(chat_id=chat_id, text=f"信息：已解绑 Emby 账户 {emby_username}", context=context)
    finally:
        db.close()

async def redeem_emby(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update._effective_chat.id
    text = update.message.text
    text_parts = text.split()
    if len(text_parts) != 3:
        await send_message(
            chat_id=chat_id, text="错误: 请按照格式填写", context=context
        )
        return
    if not settings.EMBY_REGISTER:
        await send_message(chat_id=chat_id, text="错误：Emby 暂停注册", context=context)
        return
    emby_username, redeem_code = text_parts[1:]
    _db = DB()
    # 检查邀请码有效性
    res = _db.verify_invitation_code_is_used(redeem_code)
    if not res:
        await send_message(
            chat_id=chat_id, text="错误：您输入的邀请码无效", context=context
        )
        _db.close()
        return
    if res[0]:
        await send_message(
            chat_id=chat_id, text="错误：您输入的邀请码已被使用", context=context
        )
        _db.close()
        return
    code_owner = res[1]
    # 检查该用户是否存在
    if _db.get_emby_info_by_emby_username(emby_username):
        await send_message(chat_id=chat_id, text="错误: 该用户已存在", context=context)
        _db.close()
        return
    # 创建用户
    emby = Emby()
    flag, msg = emby.add_user(username=emby_username)
    if flag:
        # 更新数据库
        _db.add_emby_user(emby_username, emby_id=msg)
    else:
        await send_message(
            chat_id=chat_id, text=f"错误: {msg}, 请联系 @WithdewHua", context=context
        )
        _db.close()
        return
    # 创建成功,更新邀请码状态
    res = _db.update_invitation_status(code=redeem_code, used_by=emby_username)
    if not res:
        await send_message(
            chat_id=chat_id,
            text="错误：更新邀请码状态失败，请联系管理员",
            context=context,
        )
        _db.close()
        return
    _db.close()
    await send_message(
        chat_id=chat_id,
        text=f"信息：兑换邀请码成功，用户名为 `{emby_username}`, 密码为空, 请及时登录 Emby 修改密码，"
        f"可使用 `/bind_emby {emby_username}`绑定机器人获取更多功能, 更多帮助请加入群组 {settings.TG_GROUP}",
        context=context,
    )
    for admin in settings.ADMIN_CHAT_ID:
        await send_message(
            chat_id=admin,
            text=f"信息：{get_user_name_from_tg_id(code_owner)} 成功邀请 {emby_username}",
            context=context,
        )




bind_emby_handler = CommandHandler("bind_emby", bind_emby)
redeem_emby_handler = CommandHandler("redeem_emby", redeem_emby)
unbind_emby_handler = CommandHandler("unbind_emby", unbind_emby)

__all__ = [
    "bind_emby_handler",
    "redeem_emby_handler",
    "unbind_emby_handler",
]
