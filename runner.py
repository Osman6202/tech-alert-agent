import argparse
import datetime

from scraper import fetch_all_sources
from twitter import fetch_twitter
from categorizer import categorize_items, has_high_alerts
from formatter import format_full_briefing, format_alert_message
from sender import send_messages, send_message
from state import is_already_sent, mark_sent
from logger import get_logger

logger = get_logger(__name__)


def _briefing_mode() -> str:
    myt_hour = (datetime.datetime.now(datetime.timezone.utc).hour + 8) % 24
    return "morning" if myt_hour < 14 else "evening"


def run_full() -> None:
    """Scrape all sources, categorize, send full Telegram briefing."""
    logger.info("Starting FULL briefing run")
    articles = fetch_all_sources()
    tweets   = fetch_twitter()
    all_items = articles + tweets
    logger.info(f"Total items collected: {len(all_items)}")

    try:
        categorized = categorize_items(all_items)
    except Exception as e:
        send_message(f"⚠️ Tech Alert: Categorization failed — {type(e).__name__}: {e}")
        return

    mode  = _briefing_mode()
    parts = format_full_briefing(categorized, mode=mode)
    send_messages(parts)
    logger.info("FULL briefing sent")


def run_alert() -> None:
    """Scrape all sources, send to Telegram only if unseen HIGH ALERTs found."""
    logger.info("Starting ALERT scan")
    articles  = fetch_all_sources()
    tweets    = fetch_twitter()
    all_items = articles + tweets

    try:
        categorized = categorize_items(all_items)
    except Exception as e:
        logger.error(f"Alert scan: categorization failed — {type(e).__name__}: {e}")
        return

    if not has_high_alerts(categorized):
        logger.info("No HIGH ALERTs detected — silent run")
        return

    for alert in categorized["high_alerts"]:
        url = alert.get("url", "")
        if is_already_sent(url):
            logger.info(f"Alert already sent: {alert['title']}")
            continue
        msg  = format_alert_message(alert)
        sent = send_message(msg)
        if sent:
            mark_sent(url)
            logger.info(f"HIGH ALERT sent: {alert['title']}")


# Keep CLI entry point so bot_listener.py subprocess calls still work:
#   python runner.py --mode full
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tech Alert Runner")
    parser.add_argument("--mode", choices=["full", "alert"], required=True)
    args = parser.parse_args()
    if args.mode == "full":
        run_full()
    else:
        run_alert()
