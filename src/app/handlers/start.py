import textwrap

from app.config import settings
from app.utils import send_message
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    body_text = f"""
    欢迎来到 Misaya 小助手

    公共命令：
    /info - 查看个人信息
    /exchange - 生成邀请码，消耗 {settings.INVITATION_CREDITS} {settings.MONEY_NAME}
    /checkin - 每日签到，获得随机{settings.MONEY_NAME}
    /credits\_rank - 查看{settings.MONEY_NAME}榜
    /donation\_rank - 查看捐赠榜
    /play\_duration\_rank - 查看观看时长榜
    /play\_duration\_rank\_all - 查看观看时长榜（合并 Plex+Emby）
    /device\_rank - 查看设备榜
    /online - 查看实时在线（Plex + Emby）
    /register\_status - 查看 Plex/Emby 是否可注册


    Plex 命令:
    /redeem\_plex - 兑换邀请码，格式为 `/redeem_plex 邮箱 邀请码` (注意空格)
    /bind\_plex - 绑定 Plex 用户，格式为 `/bind_plex 邮箱` (注意空格)
    /unbind\_plex - 解绑当前绑定的 Plex 用户
    
    Emby 命令:
    /register\_emby - 自助注册 Emby 账户，格式 `/register_emby 用户名`
    /redeem\_emby - 兑换邀请码，格式为 `/redeem_emby 用户名 邀请码` (注意空格)
    /bind\_emby - 绑定 Emby 用户，格式为 `/bind_emby 用户名` (注意空格)
    /unbind\_emby - 解绑当前绑定的 Emby 用户

    Overseerr 命令:
    /create\_overseerr - 创建 Overseerr 账户，格式为 `/create_overseerr 邮箱 密码` (注意空格)
 
    管理员命令：
    /set\_donation - 设置捐赠金额
    /update\_database - 更新数据库
    /set\_register - 设置可注册状态
    """
    await send_message(
        chat_id=update.effective_chat.id,
        text=textwrap.dedent(body_text),
        context=context,
    )


start_handler = CommandHandler("start", start)

__all__ = ["start_handler"]
