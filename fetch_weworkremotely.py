"""
Step 1d: fetch backend roles from We Work Remotely's official category RSS.
No LLM here — fetch + filter, no generation.

Why this source in addition to RemoteOK: WWR pre-curates listings into a
"Back-End Programming" category themselves, so the role-relevance gate is
partly done by their own editorial process before we even filter — a
different (and often better) signal than RemoteOK's tag-based firehose.
This matters on days RemoteOK's recent batch is thin on engineering roles
(as happened in testing) — a second, differently-curated source reduces
the chance of "no update" being about source coverage rather than an
actually quiet day.

Still applying our own tech-keyword and region-lock checks below — WWR's
"remote" categorization doesn't guarantee global-open (some listings are
US-only, EU-only, etc.), same lesson learned from RemoteOK's Brazil case.
"""
import re
import feedparser

FEEDS = {
    "backend": "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "fullstack": "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
}

# Same tech list as fetch_remote_jobs.py — kept separate rather than shared
# import since these are independent scripts by design (each fetch step
# stands alone, no cross-file coupling yet).
TECH_KEYWORDS = [
    "backend", ".net", "dotnet", "c#", "csharp", "sql", "azure",
    "ai", "agentic", "llm", "machine learning", "python",
]

# Phrases that signal a listing is region-locked despite being posted as
# "remote" — WWR's own definition of remote doesn't guarantee this the
# way we need it to. This is a heuristic, not exhaustive; widen it as you
# spot real cases slipping through, same as the RemoteOK fix.
REGION_LOCK_MARKERS = [
    "must be based in", "must reside in", "must be located in",
    "only applicants from", "residents of", "must be a resident",
    "candidates must be located",
]


def _boundary_pattern(keyword: str) -> re.Pattern:
    escaped = re.escape(keyword)
    return re.compile(rf"(?<![a-zA-Z0-9]){escaped}(?![a-zA-Z0-9])", re.IGNORECASE)


TECH_PATTERNS = [_boundary_pattern(k) for k in TECH_KEYWORDS]

# Gate: title must look like a real engineering role. Note "engineering"
# is listed separately from "engineer" — the boundary-aware match treats
# them as different words (e.g. "Engineering Manager" wouldn't match a
# plain "engineer" pattern since "ing" glues onto it).
ROLE_KEYWORDS = ["engineer", "engineering", "developer", "backend", "software", "devops"]
ROLE_PATTERNS = [_boundary_pattern(k) for k in ROLE_KEYWORDS]

# Titles containing "engineer" that are NOT software engineering roles —
# found by testing against real output (JetBrains' "Backend Customer
# Success Engineer" is support, not engineering, despite the title).
# Checked before the role gate can wrongly let them through.
NON_ENGINEERING_TITLE_MARKERS = [
    "customer success", "support engineer", "sales engineer",
    "solutions engineer", "consultant", "designer",
]


def _is_region_locked(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in REGION_LOCK_MARKERS)


def matches_profile(entry: dict) -> bool:
    title = entry.get("title", "")
    summary = entry.get("summary", "")
    title_lower = title.lower()

    if any(marker in title_lower for marker in NON_ENGINEERING_TITLE_MARKERS):
        return False

    looks_like_engineering_role = any(p.search(title) for p in ROLE_PATTERNS)
    if not looks_like_engineering_role:
        return False

    has_tech_match = any(p.search(title) for p in TECH_PATTERNS)
    if not has_tech_match:
        return False

    if _is_region_locked(summary):
        return False

    return True


def fetch_weworkremotely_jobs(max_per_feed: int = 15) -> list[dict]:
    results = []
    for category, url in FEEDS.items():
        parsed = feedparser.parse(url)
        if parsed.bozo:
            print(f"Warning: WWR feed '{category}' may be malformed: {parsed.bozo_exception}")

        for entry in parsed.entries[:max_per_feed]:
            item = {
                "title": entry.get("title", ""),
                "summary": entry.get("summary", ""),
                "url": entry.get("link", ""),
                "published": entry.get("published", ""),
                "category": category,
            }
            if matches_profile(item):
                results.append(item)

    return results


if __name__ == "__main__":
    for job in fetch_weworkremotely_jobs():
        print(f"[{job['category']}] {job['title']}")
        print(f"    {job['url']}")