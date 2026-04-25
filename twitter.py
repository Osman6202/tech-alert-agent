from typing import List, Dict, Any
import re

from logger import get_logger
from config import NITTER_INSTANCES, TWITTER_QUERIES

logger = get_logger(__name__)

RESULTS_PER_QUERY = 20


def scrape_nitter_query(query: str, instance: str, page: Any) -> List[Dict]:
    """Scrape a search query from a single Nitter instance."""
    encoded = query.replace(" ", "+").replace("(", "%28").replace(")", "%29")
    url = f"{instance}/search?q={encoded}&f=tweets"
    try:
        page.goto(url, timeout=15000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        tweets = []
        items = page.query_selector_all(".timeline-item")
        for item in items[:RESULTS_PER_QUERY]:
            content_el = item.query_selector(".tweet-content")
            link_el = item.query_selector("a.tweet-link")
            if not content_el or not link_el:
                continue
            text = content_el.inner_text().strip()
            href = link_el.get_attribute("href") or ""
            tweet_url = "https://twitter.com" + href if href.startswith("/") else href
            stats = item.query_selector_all(".tweet-stat")
            score = 0
            for stat in stats:
                num_text = stat.inner_text().strip().replace(",", "")
                if re.match(r"^\d+$", num_text):
                    score += int(num_text)
            tweets.append({"text": text, "url": tweet_url, "score": score})
        return tweets
    except Exception as e:
        logger.warning(f"Nitter scrape failed ({instance}): {e}")
        return []


def fetch_twitter() -> List[Dict]:
    """
    Try each Nitter instance for each query.
    Returns top tweets sorted by engagement, formatted like news articles.
    """
    all_tweets = []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64)")
            page = context.new_page()
            for query in TWITTER_QUERIES:
                for instance in NITTER_INSTANCES:
                    results = scrape_nitter_query(query, instance, page)
                    if results:
                        all_tweets.extend(results)
                        logger.info(f"Got {len(results)} tweets from {instance} for query: {query[:50]}")
                        break
                else:
                    logger.warning(f"All Nitter instances failed for query: {query[:50]}")
            browser.close()
    except Exception as e:
        logger.error(f"Playwright failed entirely: {e}")
        return []

    seen = set()
    unique = []
    for t in all_tweets:
        if t["url"] not in seen:
            seen.add(t["url"])
            unique.append(t)
    top = sorted(unique, key=lambda x: x["score"], reverse=True)[:20]

    return [
        {
            "title": t["text"][:120] + ("..." if len(t["text"]) > 120 else ""),
            "url": t["url"],
            "summary": t["text"][:300],
            "source": "X/Twitter",
        }
        for t in top
    ]
