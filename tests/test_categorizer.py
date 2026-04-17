import json
import pytest
from unittest.mock import MagicMock, patch

SAMPLE_ITEMS = [
    {"title": "OpenAI releases GPT-5", "url": "https://tc.com/1", "summary": "New model", "source": "TechCrunch"},
    {"title": "Massive hospital ransomware attack", "url": "https://bc.com/2", "summary": "200 hospitals hit", "source": "BleepingComputer"},
]

SAMPLE_RESPONSE = {
    "high_alerts": [
        {"title": "Massive hospital ransomware attack", "summary": "200 hospitals offline", "url": "https://bc.com/2", "source": "BleepingComputer"}
    ],
    "ai": [
        {"title": "OpenAI releases GPT-5", "summary": "New model released", "url": "https://tc.com/1", "source": "TechCrunch"}
    ],
    "cybersecurity": [],
    "gaming": [],
    "tech_startups": [],
    "scandals": [],
    "quick_insight": "AI model releases are accelerating in 2026"
}


def test_categorize_items_returns_all_categories():
    with patch("categorizer.Anthropic") as MockClient:
        mock_resp = MagicMock()
        mock_resp.content[0].text = json.dumps(SAMPLE_RESPONSE)
        MockClient.return_value.messages.create.return_value = mock_resp

        from categorizer import categorize_items
        result = categorize_items(SAMPLE_ITEMS)

    assert "high_alerts" in result
    assert "ai" in result
    assert result["ai"][0]["title"] == "OpenAI releases GPT-5"
    assert result["quick_insight"] == "AI model releases are accelerating in 2026"


def test_categorize_returns_empty_on_api_error():
    with patch("categorizer.Anthropic") as MockClient:
        MockClient.return_value.messages.create.side_effect = Exception("API error")
        from categorizer import categorize_items
        result = categorize_items(SAMPLE_ITEMS)

    assert result is None


def test_has_high_alerts_true():
    from categorizer import has_high_alerts
    assert has_high_alerts(SAMPLE_RESPONSE) is True


def test_has_high_alerts_false():
    from categorizer import has_high_alerts
    no_alerts = {**SAMPLE_RESPONSE, "high_alerts": []}
    assert has_high_alerts(no_alerts) is False
