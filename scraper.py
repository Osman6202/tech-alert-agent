import feedparser
import httpx
from bs4 import BeautifulSoup
import datetime
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

from logger import get_logger
from config import FRESHNESS_HOURS

logger = get_logger(__name__)


def _is_fresh(entry) -> bool:
    """Return True if article was published within FRESHNESS_HOURS."""
    published = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not published:
        return True  # unknown time — include it
    pub_dt = datetime.datetime(*published[:6], tzinfo=datetime.timezone.utc)
    # Note: feedparser normalises most feeds to UTC, but naive timestamps
    # from feeds that omit timezone are assumed UTC here. This is acceptable
    # for the sources in use but may cause slight freshness drift for
    # non-UTC feeds.
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=FRESHNESS_HOURS)
    return pub_dt >= cutoff


def _scrape_html(source: dict) -> List[Dict]:
    """Fallback HTML scraper for sources without RSS (e.g. Bloomberg)."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TechAlertBot/1.0)"}
        resp = httpx.get(source["url"], headers=headers, timeout=10, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = []
        for tag in soup.find_all(["h2", "h3"], limit=20):
            a = tag.find("a", href=True)
            if not a:
                continue
            title = a.get_text(strip=True)
            href = urljoin(source["url"], a["href"])
            if title:
                articles.append({
                    "title": title,
                    "url": href,
                    "summary": "",
                    "source": source["name"],
                })
        return articles
    except Exception as e:
        logger.warning(f"HTML scrape failed for {source['name']}: {e}")
        return []


def fetch_feed(source: dict) -> List[Dict]:
    """Fetch a single RSS feed and return fresh articles."""
    if source.get("html"):
        return _scrape_html(source)
    try:
        feed = feedparser.parse(source["url"])
        articles = []
        for entry in feed.entries:
            if not _is_fresh(entry):
                continue
            articles.append({
                "title": getattr(entry, "title", "").strip(),
                "url": getattr(entry, "link", ""),
                "summary": getattr(entry, "summary", "")[:300].strip(),
                "source": source["name"],
            })
        logger.info(f"Scraped {len(articles)} fresh articles from {source['name']}")
        return articles
    except Exception as e:
        logger.warning(f"Feed fetch failed for {source['name']}: {e}")
        return []


def fetch_all_sources(sources: Optional[List[Dict]] = None) -> List[Dict]:
    """Fetch all sources concurrently. Returns combined list of articles."""
    from config import NEWS_SOURCES
    sources = sources or NEWS_SOURCES
    all_articles = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_feed, src): src for src in sources}
        for future in as_completed(futures):
            all_articles.extend(future.result())
    return all_articles
