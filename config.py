import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

# LM Studio local server (OpenAI-compatible REST API)
LM_STUDIO_HOST  = os.environ.get("LM_STUDIO_HOST",  "http://localhost:1234/v1")
LM_STUDIO_MODEL = os.environ.get("LM_STUDIO_MODEL", "phi-3.5-mini-instruct")

# Scheduler timezone — briefings fire at 08:00 and 20:00 in this zone
SCHEDULE_TZ = os.environ.get("SCHEDULE_TZ", "Asia/Kuala_Lumpur")

# RSS sources
NEWS_SOURCES = [
    {"name": "Reuters Technology",    "url": "https://feeds.reuters.com/reuters/technologyNews"},
    {"name": "TechCrunch",            "url": "https://techcrunch.com/feed/"},
    {"name": "Ars Technica",          "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"name": "The Verge",             "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Wired",                 "url": "https://www.wired.com/feed/rss"},
    {"name": "VentureBeat",           "url": "https://venturebeat.com/feed/"},
    {"name": "Hacker News",           "url": "https://news.ycombinator.com/rss"},
    {"name": "Engadget",              "url": "https://www.engadget.com/rss.xml"},
    {"name": "ZDNet",                 "url": "https://www.zdnet.com/news/rss.xml"},
    {"name": "BleepingComputer",      "url": "https://www.bleepingcomputer.com/feed/"},
    {"name": "The Register",          "url": "https://www.theregister.com/headlines.atom"},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/"},
    {"name": "PC Gamer",              "url": "https://www.pcgamer.com/rss/"},
    {"name": "IGN",                   "url": "https://feeds.feedburner.com/ign/all"},
    {"name": "Kotaku",                "url": "https://kotaku.com/rss"},
    {"name": "Eurogamer",             "url": "https://www.eurogamer.net/?format=rss"},
    {"name": "GamesIndustry.biz",     "url": "https://www.gamesindustry.biz/feed/rss"},
    {"name": "9to5Google",            "url": "https://9to5google.com/feed/"},
    # Bloomberg has no public RSS — scraped via HTML fallback
    {"name": "Bloomberg Technology",  "url": "https://www.bloomberg.com/technology", "html": True},
]

NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.1d4.us",
    "https://nitter.kavin.rocks",
]

TWITTER_QUERIES = [
    "(tech OR AI OR cybersecurity OR hack OR startup OR gaming) (announcement OR launch OR breaking OR major)",
    "(OpenAI OR Anthropic OR Google AI OR major hack OR data breach OR ransomware)",
]

# Hours window for article freshness filter
FRESHNESS_HOURS = 13


def validate_config() -> list[str]:
    """Return list of warning strings for missing/placeholder config values."""
    warnings = []
    if "your_telegram" in TELEGRAM_BOT_TOKEN.lower():
        warnings.append("TELEGRAM_BOT_TOKEN is still the placeholder — edit .env")
    if "your_telegram" in str(TELEGRAM_CHAT_ID).lower():
        warnings.append("TELEGRAM_CHAT_ID is still the placeholder — edit .env")
    return warnings
