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


def categorize_items(items: List[Dict]) -> Optional[Dict]:
    """Send items to LM Studio for categorization. Returns categorized dict or raises on error."""
    if not items:
        return {
            "high_alerts": [], "ai": [], "cybersecurity": [],
            "gaming": [], "tech_startups": [], "scandals": [],
            "quick_insight": "No news items found for this period."
        }
    try:
        client = OpenAI(base_url=LM_STUDIO_HOST, api_key="lm-studio")
        items_json = json.dumps(
            [{"title": i["title"], "url": i["url"], "summary": i["summary"], "source": i["source"]}
             for i in items],
            indent=2
        )
        response = client.chat.completions.create(
            model=LM_STUDIO_MODEL,
            max_tokens=1024,
            temperature=0.1,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": CATEGORY_PROMPT.format(items=items_json)},
            ],
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        logger.info(
            f"Categorized {len(items)} items — "
            f"{len(result.get('high_alerts', []))} alerts, "
            f"{len(result.get('ai', []))} AI, "
            f"{len(result.get('gaming', []))} gaming"
        )
        return result
    except Exception as e:
        logger.error(f"Categorization failed: {e}", exc_info=True)
        raise


def has_high_alerts(categorized: Dict) -> bool:
    """Return True if categorized result contains any HIGH ALERT items."""
    return bool(categorized.get("high_alerts"))
