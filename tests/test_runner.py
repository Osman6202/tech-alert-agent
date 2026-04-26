import pytest
from unittest.mock import patch, MagicMock

MOCK_ARTICLES = [
    {"title": "AI News", "url": "https://tc.com/1", "summary": "Big news", "source": "TechCrunch"}
]
MOCK_CATEGORIZED = {
    "high_alerts": [],
    "ai": [{"title": "AI News", "summary": "Big news", "url": "https://tc.com/1", "source": "TechCrunch"}],
    "cybersecurity": [], "gaming": [], "tech_startups": [], "scandals": [],
    "quick_insight": "AI is everywhere"
}


def test_run_full_sends_briefing():
    with patch("runner.fetch_all_sources", return_value=MOCK_ARTICLES), \
         patch("runner.fetch_twitter",     return_value=[]), \
         patch("runner.categorize_items",  return_value=MOCK_CATEGORIZED), \
         patch("runner.format_full_briefing", return_value=["message"]), \
         patch("runner.send_messages") as mock_send:
        from runner import run_full
        run_full()
    assert mock_send.called


def test_run_alert_sends_nothing_when_no_alerts():
    no_alerts = {**MOCK_CATEGORIZED, "high_alerts": []}
    with patch("runner.fetch_all_sources", return_value=MOCK_ARTICLES), \
         patch("runner.fetch_twitter",     return_value=[]), \
         patch("runner.categorize_items",  return_value=no_alerts), \
         patch("runner.send_messages")  as mock_send, \
         patch("runner.send_message")   as mock_send_single:
        from runner import run_alert
        run_alert()
    assert not mock_send.called
    assert not mock_send_single.called


def test_run_alert_sends_when_high_alert_found():
    alert     = {"title": "Ransomware", "summary": "Bad", "url": "https://bc.com/1", "source": "BC"}
    with_alert = {**MOCK_CATEGORIZED, "high_alerts": [alert]}
    with patch("runner.fetch_all_sources",   return_value=MOCK_ARTICLES), \
         patch("runner.fetch_twitter",        return_value=[]), \
         patch("runner.categorize_items",     return_value=with_alert), \
         patch("runner.is_already_sent",      return_value=False), \
         patch("runner.mark_sent"), \
         patch("runner.format_alert_message", return_value="🚨 Alert"), \
         patch("runner.send_message") as mock_send:
        from runner import run_alert
        run_alert()
    assert mock_send.called
