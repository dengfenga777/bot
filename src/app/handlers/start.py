import textwrap

from app.utils.utils import send_message
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    body_text = """
    欢迎使用MisayaMedia助手！

    小助手没有公共命令，请点击左下角"MisayaMedia"进入并使用！
    """
    await send_message(
        chat_id=update.effective_chat.id,
        text=textwrap.dedent(body_text),
        parse_mode="markdown",
        context=context,
    )


start_handler = CommandHandler("start", start)

__all__ = ["start_handler"]
