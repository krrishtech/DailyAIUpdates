"""
Step 1c: fetch global remote roles from RemoteOK's public JSON API.
No LLM here — fetch + client-side keyword filter, no generation.

Important: RemoteOK's own ?tag=/?tags= query params were tested and did
NOT reliably filter results — a request for "dev" tagged jobs still
returned paralegals, caretakers, and clinical pharmacists. Don't trust
their server-side filter; this script filters client-side instead,
against keywords that actually match your profile.
"""
import re
import requests

REMOTEOK_API = "https://remoteok.com/api"

# Gate 1: the role itself must look like an engineering job by its TITLE.
# Without this, any role whose marketing description happens to mention
# "AI" (which is nearly all of them in 2026) gets through — paralegals,
# executive assistants, designers, all mention "AI" in their company's
# pitch without being engineering roles themselves.
ROLE_KEYWORDS = [
    "engineer", "developer", "backend", "software", "sde",
    "full stack", "fullstack", "devops",
]

# Gate 2: must also reference your actual stack/interests. Matched only
# against title + tags, NEVER the free-text description — description
# text is marketing copy and mentions "AI" constantly regardless of
# whether the role itself is technical.
TECH_KEYWORDS = [
    "backend", ".net", "dotnet", "c#", "csharp", "sql", "azure",
    "ai", "agentic", "llm", "machine learning", "python",
]


def _boundary_pattern(keyword: str) -> re.Pattern:
    # Keeps the earlier word-boundary fix (so "ai" doesn't match inside
    # "maintenance") — still needed even with the stricter gates below.
    escaped = re.escape(keyword)
    return re.compile(rf"(?<![a-zA-Z0-9]){escaped}(?![a-zA-Z0-9])", re.IGNORECASE)


ROLE_PATTERNS = [_boundary_pattern(k) for k in ROLE_KEYWORDS]
TECH_PATTERNS = [_boundary_pattern(k) for k in TECH_KEYWORDS]

# Gate 3: must actually be open globally, not tied to one country. RemoteOK
# lists plenty of "remote" jobs that are really local-hire-only (e.g. a
# Brazil-based DevOps role in Portuguese) — matching tech keywords alone
# doesn't catch this, since the role and stack can be a perfect fit while
# the job itself is legally/practically closed to you. A location field
# naming a specific country (not blank, not an explicit "worldwide"/
# "anywhere"/"global" marker) is treated as region-locked.
GLOBAL_MARKERS = ["remote", "worldwide", "anywhere", "global", ""]


def _is_globally_open(location: str) -> bool:
    loc = location.strip().lower().rstrip(",").strip()
    if loc in GLOBAL_MARKERS:
        return True
    return any(marker in loc for marker in GLOBAL_MARKERS if marker)


def matches_profile(job: dict) -> bool:
    title = job.get("position", "")
    tags_text = " ".join(job.get("tags", []))
    location = job.get("location", "")

    looks_like_engineering_role = any(p.search(title) for p in ROLE_PATTERNS)
    if not looks_like_engineering_role:
        return False

    tech_haystack = f"{title} {tags_text}"  # description deliberately excluded
    has_tech_match = any(p.search(tech_haystack) for p in TECH_PATTERNS)
    if not has_tech_match:
        return False

    return _is_globally_open(location)


def fetch_remote_jobs(max_items: int = 10) -> list[dict]:
    resp = requests.get(
        REMOTEOK_API,
        headers={"User-Agent": "daily-ai-feed/1.0"},  # RemoteOK blocks generic bots
        timeout=15,
    )
    resp.raise_for_status()
    raw = resp.json()

    # First element is always RemoteOK's legal/terms notice, not a job.
    jobs = raw[1:] if raw and "legal" in raw[0] else raw

    matched = [job for job in jobs if matches_profile(job)]

    return [
        {
            "title": job.get("position", ""),
            "company": job.get("company", ""),
            "url": job.get("url", ""),
            "salary_min": job.get("salary_min", 0),
            "salary_max": job.get("salary_max", 0),
            "tags": job.get("tags", []),
        }
        for job in matched[:max_items]
    ]


if __name__ == "__main__":
    for job in fetch_remote_jobs():
        salary = f"${job['salary_min']:,}-${job['salary_max']:,}" if job["salary_min"] else "not listed"
        print(f"{job['title']} @ {job['company']} ({salary})")
        print(f"    {job['url']}")
        print(f"    tags: {', '.join(job['tags'])}")