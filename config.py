import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

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

# Claude model to use
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
