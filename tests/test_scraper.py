import datetime
import pytest
from unittest.mock import MagicMock, patch


def make_entry(title, link, summary, hours_ago=1):
    t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours_ago)
    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.summary = summary
    entry.published_parsed = t.timetuple()
    return entry


def test_fetch_feed_returns_articles():
    with patch("scraper.feedparser.parse") as mock_parse:
        mock_parse.return_value = MagicMock(
            entries=[make_entry("AI Model Launched", "https://ex.com/1", "Summary here")]
        )
        from scraper import fetch_feed
        result = fetch_feed({"name": "Test Source", "url": "https://ex.com/feed"})
    assert len(result) == 1
    assert result[0]["title"] == "AI Model Launched"
    assert result[0]["source"] == "Test Source"
    assert result[0]["url"] == "https://ex.com/1"


def test_fetch_feed_skips_old_articles():
    with patch("scraper.feedparser.parse") as mock_parse:
        mock_parse.return_value = MagicMock(
            entries=[make_entry("Old News", "https://ex.com/2", "Old", hours_ago=25)]
        )
        from scraper import fetch_feed
        result = fetch_feed({"name": "Test Source", "url": "https://ex.com/feed"})
    assert result == []


def test_fetch_feed_handles_failure():
    with patch("scraper.feedparser.parse", side_effect=Exception("network error")):
        from scraper import fetch_feed
        result = fetch_feed({"name": "Bad Source", "url": "https://bad.url/feed"})
    assert result == []


def test_fetch_all_sources_combines_results():
    with patch("scraper.fetch_feed") as mock_fetch:
        mock_fetch.side_effect = [
            [{"title": "A", "url": "https://a.com", "source": "S1", "summary": ""}],
            [{"title": "B", "url": "https://b.com", "source": "S2", "summary": ""}],
        ]
        from scraper import fetch_all_sources
        result = fetch_all_sources([{"name": "S1", "url": "u1"}, {"name": "S2", "url": "u2"}])
    assert len(result) == 2
    assert {r["title"] for r in result} == {"A", "B"}
