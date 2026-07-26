"""
Step 1b: fetch frontier AI news from allowlisted RSS feeds.
No LLM here — just fetch + parse. Same "allowlist enforced by construction"
principle as fetch_tools.py: we only ever request URLs listed below.

Note: Anthropic and Meta have no official RSS feeds (verified — they
simply don't exist, unlike OpenAI/DeepMind/Google/Microsoft's). Frontier
updates from those two aren't covered by this script; that's a known
gap, not a bug, until we add another mechanism for them.

Note on Microsoft: their feed is general company news, not AI-only.
Items from it need the relevance filter (a later step) before they're
fit to send — don't assume everything from this feed is on-topic.
"""
import feedparser

# Allowlist: only official, first-party blogs. No aggregators, no mirrors.
# These are OFFICIAL ANNOUNCEMENTS — treat as fact-level source material.
FEEDS = {
    "openai": "https://openai.com/news/rss.xml",
    "deepmind": "https://deepmind.google/blog/rss.xml",
    "google_ai_blog": "https://blog.google/technology/ai/rss/",
    "microsoft": "https://news.microsoft.com/source/feed/",  # general feed, not AI-only
}

# Separate tier: reputable, named-expert ANALYSIS newsletters. Real editorial
# judgment behind them, but this is opinion/interpretation, not an official
# announcement — never blend these with FEEDS above. The curate/generate step
# must phrase these as "X's analysis notes..." not as plain fact.
# Add more here later using the same <name>.substack.com/feed pattern —
# verify each one is real before adding (same process used for this one).
ANALYSIS_FEEDS = {
    "import_ai": "https://importai.substack.com/feed",  # Jack Clark, Anthropic co-founder
}

# Only fetch items published in roughly the last N days, so old posts
# don't flood the first run.
def fetch_feed(name: str, url: str, max_items: int = 5) -> list[dict]:
    parsed = feedparser.parse(url)
    if parsed.bozo:  # feedparser's flag for malformed/unreachable feeds
        print(f"Warning: feed '{name}' may be malformed or unreachable: {parsed.bozo_exception}")

    items = []
    for entry in parsed.entries[:max_items]:
        items.append({
            "source": name,
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "summary": entry.get("summary", ""),
            "published": entry.get("published", ""),
        })
    return items


def fetch_all_news() -> list[dict]:
    results = []
    for name, url in FEEDS.items():
        try:
            items = fetch_feed(name, url)
            for item in items:
                item["kind"] = "official"
            results.extend(items)
        except Exception as e:
            print(f"Failed to fetch feed '{name}': {e}")

    for name, url in ANALYSIS_FEEDS.items():
        try:
            items = fetch_feed(name, url)
            for item in items:
                item["kind"] = "analysis"
            results.extend(items)
        except Exception as e:
            print(f"Failed to fetch analysis feed '{name}': {e}")

    return results


if __name__ == "__main__":
    for item in fetch_all_news():
        print(f"[{item['source']}] ({item['kind']}) {item['title']}")
        print(f"    {item['url']}")
        print(f"    published: {item['published']}")