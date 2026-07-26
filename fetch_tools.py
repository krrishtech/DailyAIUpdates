"""
Step 1: fetch candidate items from an allowlisted source.
This one hits GitHub's Search API for recently-updated repos tagged with
agentic-AI related topics. No LLM here — just fetch + light shaping,
so this step costs zero tokens.
"""
import os
import requests

GITHUB_API = "https://api.github.com/search/repositories"

# Allowlist: only these topic tags are ever queried. Nothing outside this
# list gets fetched — this is what "allowlisted source" means in practice.
TOPICS = ["agentic-ai", "llm-agent", "mcp-server", "ai-agent-framework"]


def fetch_topic(topic: str, per_page: int = 5) -> list[dict]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")  # optional, raises rate limit
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params = {
        "q": f"topic:{topic} pushed:>2026-06-01",  # only recently active repos
        "sort": "updated",
        "order": "desc",
        "per_page": per_page,
    }
    resp = requests.get(GITHUB_API, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    items = resp.json().get("items", [])

    return [
        {
            "name": item["full_name"],
            "url": item["html_url"],
            "description": item.get("description") or "",
            "stars": item["stargazers_count"],
            "updated_at": item["updated_at"],
            "topic": topic,
        }
        for item in items
    ]


def fetch_all_tools() -> list[dict]:
    results = []
    for topic in TOPICS:
        try:
            results.extend(fetch_topic(topic))
        except Exception as e:
            print(f"Failed to fetch topic '{topic}': {e}")
    return results


if __name__ == "__main__":
    for tool in fetch_all_tools():
        print(f"[{tool['topic']}] {tool['name']} ({tool['stars']}⭐) — {tool['url']}")
        print(f"    {tool['description']}")