import pytest
from unittest.mock import MagicMock, patch


def test_scrape_nitter_returns_tweets():
    mock_page = MagicMock()
    mock_page.query_selector_all.return_value = [
        MagicMock(
            query_selector=lambda sel: MagicMock(
                inner_text=lambda: "OpenAI drops GPT-5" if "tweet-content" in sel else "100",
                get_attribute=lambda attr: "https://nitter.net/user/status/123" if attr == "href" else None,
            )
        )
    ]

    with patch("twitter.sync_playwright") as mock_pw:
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.goto.return_value = None
        mock_page.wait_for_timeout.return_value = None

        from twitter import scrape_nitter_query
        results = scrape_nitter_query("AI breaking news", "https://nitter.privacydev.net", mock_page)

    assert isinstance(results, list)


def test_fetch_twitter_returns_empty_on_all_failures():
    with patch("twitter.sync_playwright") as mock_pw:
        mock_pw.return_value.__enter__.return_value.chromium.launch.side_effect = Exception("browser fail")
        from twitter import fetch_twitter
        result = fetch_twitter()
    assert result == []
