"""群组成员变化监听Handler"""

import time

from app.config import settings
from app.db import DB
from app.log import logger
from telegram import ChatMember, ChatMemberUpdated, Update
from telegram.ext import ChatMemberHandler, ContextTypes


def extract_status_change(
    chat_member_update: ChatMemberUpdated,
) -> tuple[bool, bool]:
    """判断群组成员状态变化

    Returns:
        tuple: (是否离开, 是否加入)
    """
    status_change = chat_member_update.difference().get("status")
    if status_change is None:
        return False, False

    old_status, new_status = status_change
    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ]
    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ]

    # 离开群组：从成员状态变为非成员状态
    has_left = was_member and not is_member
    # 加入群组：从非成员状态变为成员状态
    has_joined = not was_member and is_member

    return has_left, has_joined


async def track_group_member_changes(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """监听群组成员变化"""
    result = extract_status_change(update.chat_member)
    has_left, has_joined = result

    if not (has_left or has_joined):
        return

    user = update.chat_member.new_chat_member.user
    chat = update.chat_member.chat
    tg_id = user.id
    group_id = chat.id

    # 仅处理配置的群组
    if str(group_id) != settings.TG_GROUP and settings.TG_GROUP:
        logger.debug(f"忽略非监控群组的成员变化: group_id={group_id}")
        return

    db = DB()
    try:
        if has_left:
            # 用户离开群组，记录离开时间
            left_time = int(time.time())
            success = db.add_group_member_left_record(
                tg_id=tg_id, left_time=left_time, group_id=group_id
            )
            if success:
                logger.info(
                    f"用户 {user.username or user.first_name} (ID: {tg_id}) 离开群组 {chat.title} (ID: {group_id})，已记录离开时间"
                )
            else:
                logger.error(f"记录用户 {tg_id} 离开群组失败")

        elif has_joined:
            # 用户加入群组，删除离开记录（如果存在）
            success = db.remove_group_member_left_record(tg_id=tg_id)
            if success:
                logger.info(
                    f"用户 {user.username or user.first_name} (ID: {tg_id}) 重新加入群组 {chat.title} (ID: {group_id})，已清除离开记录"
                )
    finally:
        db.close()


# 注册handler
group_member_handler = ChatMemberHandler(
    track_group_member_changes, ChatMemberHandler.CHAT_MEMBER
)
