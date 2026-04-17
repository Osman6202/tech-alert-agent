import httpx
import time
from typing import List

from logger import get_logger
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = get_logger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_message(text: str, retries: int = 1) -> bool:
    """Send a single message to Telegram. Returns True on success."""
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    for attempt in range(retries + 1):
        try:
            resp = httpx.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
            if resp.is_success:
                logger.info(f"Telegram message sent ({len(text)} chars)")
                return True
            logger.warning(f"Telegram API error: {resp.text}")
        except Exception as e:
            logger.warning(f"Telegram send attempt {attempt + 1} failed: {e}")
            if attempt < retries:
                time.sleep(5)
    logger.error("Failed to send Telegram message after retries")
    return False


def send_messages(parts: List[str]) -> None:
    """Send a list of message parts sequentially."""
    for part in parts:
        send_message(part)
