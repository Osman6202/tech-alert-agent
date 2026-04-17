import subprocess
import sys
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from logger import get_logger
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = get_logger(__name__)

PYTHON = sys.executable
MAIN_SCRIPT = os.path.join(os.path.dirname(__file__), "main.py")
AUTHORIZED_CHAT_ID = str(TELEGRAM_CHAT_ID)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages — trigger runs on RUN NEWS / RUN ALERT."""
    if str(update.effective_chat.id) != AUTHORIZED_CHAT_ID:
        return

    text = (update.message.text or "").strip().upper()

    if text == "RUN NEWS":
        await update.message.reply_text("⏳ Running full scan...")
        logger.info("Manual trigger: RUN NEWS")
        subprocess.Popen([PYTHON, MAIN_SCRIPT, "--mode", "full"])

    elif text == "RUN ALERT":
        await update.message.reply_text("⏳ Scanning for HIGH ALERTs...")
        logger.info("Manual trigger: RUN ALERT")
        subprocess.Popen([PYTHON, MAIN_SCRIPT, "--mode", "alert"])


def run_bot() -> None:
    """Start the bot polling loop."""
    logger.info("Bot listener starting...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(poll_interval=2)


if __name__ == "__main__":
    run_bot()
