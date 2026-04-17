from formatter import format_full_briefing, format_alert_message, split_message

SAMPLE_CATEGORIZED = {
    "high_alerts": [
        {"title": "Major Ransomware Attack", "summary": "200 hospitals hit", "url": "https://bc.com/1", "source": "BleepingComputer"}
    ],
    "ai": [
        {"title": "GPT-5 Released", "summary": "Beats all benchmarks", "url": "https://tc.com/2", "source": "TechCrunch"}
    ],
    "cybersecurity": [],
    "gaming": [
        {"title": "GTA VI Delayed", "summary": "New date: Q1 2027", "url": "https://ign.com/3", "source": "IGN"}
    ],
    "tech_startups": [],
    "scandals": [],
    "quick_insight": "AI inference costs dropped 40% YoY"
}


def test_format_full_briefing_returns_list_of_strings():
    parts = format_full_briefing(SAMPLE_CATEGORIZED, mode="morning")
    assert isinstance(parts, list)
    assert all(isinstance(p, str) for p in parts)
    assert len(parts) >= 1


def test_format_full_briefing_contains_header():
    parts = format_full_briefing(SAMPLE_CATEGORIZED, mode="morning")
    full = "".join(parts)
    assert "TECH ALERT" in full
    assert "Morning Briefing" in full


def test_format_full_briefing_contains_high_alert():
    parts = format_full_briefing(SAMPLE_CATEGORIZED, mode="morning")
    full = "".join(parts)
    assert "HIGH ALERT" in full
    assert "Major Ransomware Attack" in full


def test_format_full_briefing_contains_gaming():
    parts = format_full_briefing(SAMPLE_CATEGORIZED, mode="morning")
    full = "".join(parts)
    assert "GTA VI Delayed" in full


def test_format_alert_message_contains_headline():
    alert = {"title": "Critical Zero-Day", "summary": "Affects 500M devices", "url": "https://ex.com", "source": "Ars"}
    msg = format_alert_message(alert)
    assert "Critical Zero-Day" in msg
    assert "HIGH ALERT" in msg


def test_split_message_respects_limit():
    long_text = "A" * 10000
    parts = split_message(long_text, limit=4096)
    assert all(len(p) <= 4096 for p in parts)
    assert "".join(parts) == long_text
