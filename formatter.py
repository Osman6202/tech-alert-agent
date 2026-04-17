import datetime
from typing import List, Dict


def _now_myt() -> str:
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    myt = utc_now + datetime.timedelta(hours=8)
    return myt.strftime("%I:%M %p MYT · %B %d, %Y")


def _item_line(item: Dict) -> str:
    title = item.get("title", "")
    summary = item.get("summary", "")
    url = item.get("url", "")
    return f'· <b>{title}</b> → {summary}\n  🔗 <a href="{url}">{item.get("source", "")}</a>'


def format_full_briefing(categorized: Dict, mode: str = "morning") -> List[str]:
    """Build full briefing message, split into ≤4096 char parts."""
    label = "Morning Briefing" if mode == "morning" else "Evening Briefing"
    lines = [
        f"📰 <b>TECH ALERT — {label}</b>",
        f"🕐 {_now_myt()}",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]

    alerts = categorized.get("high_alerts", [])
    if alerts:
        lines.append("")
        lines.append("🚨 <b>HIGH ALERT</b>")
        for a in alerts:
            lines.append(f'🚨 <b>{a["title"]}</b>')
            lines.append(f'· {a.get("summary", "")}')
            lines.append(f'🔗 <a href="{a["url"]}">{a.get("source", "")}</a>')

    lines += ["", "━━━━━━━━━━━━━━━━━━━━━━", "📰 <b>FULL TECH FEED</b>", ""]

    sections = [
        ("🤖 <b>AI Developments</b>", categorized.get("ai", [])),
        ("🔐 <b>Cybersecurity</b>", categorized.get("cybersecurity", [])),
        ("🎮 <b>Gaming</b>", categorized.get("gaming", [])),
        ("💻 <b>Tech / Startups</b>", categorized.get("tech_startups", [])),
        ("⚠️ <b>Scandals</b>", categorized.get("scandals", [])),
    ]
    for header, items in sections:
        if not items:
            continue
        lines.append(header)
        for item in items:
            lines.append(_item_line(item))
        lines.append("")

    insight = categorized.get("quick_insight", "")
    if insight:
        lines += ["━━━━━━━━━━━━━━━━━━━━━━", "📈 <b>QUICK INSIGHT</b>", f"→ {insight}"]

    full_text = "\n".join(lines)
    return split_message(full_text)


def format_alert_message(alert: Dict) -> str:
    """Build a breaking HIGH ALERT message."""
    now = _now_myt()
    return (
        f"🚨 <b>HIGH ALERT — BREAKING</b>\n\n"
        f'🚨 <b>{alert["title"]}</b>\n'
        f'· {alert.get("summary", "")}\n'
        f'🔗 <a href="{alert["url"]}">{alert.get("source", "")}</a>\n'
        f"⏱ Detected: {now}"
    )


def split_message(text: str, limit: int = 4096) -> List[str]:
    """Split text into chunks of at most `limit` characters."""
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return parts
