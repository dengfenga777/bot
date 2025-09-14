from telegram.ext import CommandHandler, ContextTypes
from telegram import Update


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_chat.send_message("Hello from example integration!")


hello_handler = CommandHandler("hello_example", hello)

