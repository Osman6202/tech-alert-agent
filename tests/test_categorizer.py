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
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps(SAMPLE_RESPONSE)
    with patch("categorizer.OpenAI") as MockClient:
        MockClient.return_value.chat.completions.create.return_value = mock_resp
        from categorizer import categorize_items
        result = categorize_items(SAMPLE_ITEMS)

    assert "high_alerts" in result
    assert "ai" in result
    assert result["ai"][0]["title"] == "OpenAI releases GPT-5"
    assert result["quick_insight"] == "AI model releases are accelerating in 2026"


def test_categorize_raises_on_lm_studio_failure():
    with patch("categorizer.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.chat.completions.create.side_effect = Exception("Connection refused")
        from categorizer import categorize_items
        with pytest.raises(Exception, match="Connection refused"):
            categorize_items(SAMPLE_ITEMS)


def test_categorize_returns_empty_for_no_items():
    from categorizer import categorize_items
    result = categorize_items([])
    assert result["high_alerts"] == []
    assert result["ai"] == []
    assert "quick_insight" in result


def test_has_high_alerts_true():
    from categorizer import has_high_alerts
    assert has_high_alerts(SAMPLE_RESPONSE) is True


def test_has_high_alerts_false():
    from categorizer import has_high_alerts
    no_alerts = {**SAMPLE_RESPONSE, "high_alerts": []}
    assert has_high_alerts(no_alerts) is False
