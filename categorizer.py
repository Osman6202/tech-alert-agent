import json
from typing import List, Dict, Optional
from openai import OpenAI

from logger import get_logger
from config import LM_STUDIO_HOST, LM_STUDIO_MODEL

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a tech news editor. Categorize news items and return valid JSON only.
Never fabricate news. Only include items actually present in the input."""

CATEGORY_PROMPT = """Categorize these tech news items into the following JSON structure.
Only include real items from the input. Do not add items not in the input.

Categories:
- high_alerts: Major hacks/ransomware, big scandals, breakthroughs, massive product launches, major deals
- ai: AI model releases, partnerships, research breakthroughs
- cybersecurity: Hacks, breaches, vulnerabilities, incidents
- gaming: Game launches, platform updates, industry moves, gaming company news
- tech_startups: Funding rounds, acquisitions, product launches
- scandals: Legal disputes, policy conflicts, controversies
- quick_insight: (string, not array) One sharp trend or observation from the news

Return this exact JSON structure:
{{
  "high_alerts": [{{"title": "", "summary": "1 line", "url": "", "source": ""}}],
  "ai": [{{"title": "", "summary": "1 line", "url": "", "source": ""}}],
  "cybersecurity": [{{"title": "", "summary": "1 line", "url": "", "source": ""}}],
  "gaming": [{{"title": "", "summary": "1 line", "url": "", "source": ""}}],
  "tech_startups": [{{"title": "", "summary": "1 line", "url": "", "source": ""}}],
  "scandals": [{{"title": "", "summary": "1 line", "url": "", "source": ""}}],
  "quick_insight": "one trend observation"
}}

News items to categorize:
{items}"""

_EMPTY = {
    "high_alerts": [], "ai": [], "cybersecurity": [],
    "gaming": [], "tech_startups": [], "scandals": [],
    "quick_insight": "No news items found for this period."
}


def _build_messages(items_json: str) -> list:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": CATEGORY_PROMPT.format(items=items_json)},
    ]


def _parse_raw(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def _categorize_via_lm_studio(messages: list) -> dict:
    client   = OpenAI(base_url=LM_STUDIO_HOST, api_key="lm-studio")
    response = client.chat.completions.create(
        model=LM_STUDIO_MODEL,
        max_tokens=1024,
        temperature=0.1,
        messages=messages,
    )
    return _parse_raw(response.choices[0].message.content)


def categorize_items(items: List[Dict]) -> Optional[Dict]:
    """Send items to LM Studio for categorization. Raises on failure."""
    if not items:
        return _EMPTY

    items_json = json.dumps(
        [{"title": i["title"], "url": i["url"], "summary": i["summary"], "source": i["source"]}
         for i in items],
        indent=2
    )
    messages = _build_messages(items_json)

    try:
        result = _categorize_via_lm_studio(messages)
    except Exception as e:
        logger.error(f"LM Studio categorization failed: {e}", exc_info=True)
        raise

    logger.info(
        f"Categorized {len(items)} items — "
        f"{len(result.get('high_alerts', []))} alerts, "
        f"{len(result.get('ai', []))} AI, "
        f"{len(result.get('gaming', []))} gaming"
    )
    return result


def has_high_alerts(categorized: Dict) -> bool:
    return bool(categorized.get("high_alerts"))
