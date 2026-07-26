"""
Step 4: the ONE real LLM call in the whole pipeline. Everything upstream
(fetch, dedup, relevance filter) is deterministic code — no tokens spent.
This is the single point where a model reads what survived filtering and
writes the final message.

Core rule, non-negotiable in the prompt: the model may ONLY reference
facts present in the data it's given. No outside knowledge, no invented
company names, no invented salaries, no filling gaps with plausible-
sounding details. If a section has no surviving items, it must say so
plainly rather than stretch something thin to fill space — this was the
whole point of building the fetch/dedup/relevance layers first.
"""
import json
import os

from google import genai

MODEL_NAME = "gemini-3.1-flash-lite"  # confirmed free-tier as of July 2026 via
                                        # two independent official Google docs.
                                        # Model naming changes over time on
                                        # Google's end — if this ever 404s again,
                                        # check ai.google.dev/gemini-api/docs/models
                                        # for the current free-tier model ID.


def _format_section(name: str, items: list[dict], fields: list[str]) -> str:
    if not items:
        return f"### {name}\n(no items survived filtering — say 'No update today' for this section)\n"

    lines = [f"### {name}"]
    for item in items:
        row = " | ".join(f"{f}: {item.get(f, '')}" for f in fields if item.get(f))
        lines.append(f"- {row}")
    return "\n".join(lines) + "\n"


def build_prompt(sections: dict, profile: dict) -> str:
    frontier_official = _format_section(
        "Frontier AI news (official)", sections.get("frontier_official", []),
        ["title", "source", "url"],
    )
    frontier_analysis = _format_section(
        "Frontier AI analysis (opinion, not fact)", sections.get("frontier_analysis", []),
        ["title", "source", "url"],
    )
    tools = _format_section(
        "Agentic AI tools/repos", sections.get("tools", []),
        ["name", "description", "stars", "url"],
    )
    gcc_jobs = _format_section(
        "Indian GCC jobs", sections.get("gcc_jobs", []),
        ["title", "company", "url"],
    )
    remote_jobs = _format_section(
        "Global remote jobs", sections.get("remote_jobs", []),
        ["title", "company", "url"],
    )

    stack = ", ".join(profile.get("primary_stack", []))
    interests = ", ".join(profile.get("interests", []))

    return f"""You are writing a daily Telegram briefing for a backend engineer
whose stack is: {stack}. Interests: {interests}.

STRICT RULES:
- Use ONLY the facts given below in each section. Never use outside knowledge,
  never invent a company name, salary, statistic, or detail not present here.
- The "analysis" section is opinion/commentary, not fact — phrase it as
  "X's analysis suggests..." not as a plain factual claim.
- If a section says "(no items survived filtering...)", write exactly
  "No update today." for that section. Do not stretch a weak item to fill it.
- Keep it mobile-scannable: short bullets, no long paragraphs.
- FORMATTING — this is for Telegram, not standard Markdown. Telegram's
  Markdown only supports single *asterisks* for bold (never **double**),
  and has NO header syntax at all (## does nothing — it would show up
  as literal ## characters). Follow this exactly:
  - Section titles: bold plain text, e.g. *1. 🚀 The Frontier* — not ##.
  - Bold emphasis: single asterisks, e.g. *Backend Engineer* — not **word**.
  - Bullets: plain dashes, e.g. "- item text", not markdown list syntax.
- Use this exact 5-section order with these titles (as bold text, not headers):

*1. 🚀 The Frontier*
*2. 🛠️ The Automation Tool Radar*
*3. 🇮🇳 Indian GCC & IT Job Pulse*
*4. 🌍 Global Remote Opportunities*
*5. 💡 Monetization & Micro-Business*

For section 5 ONLY: this one is NOT fact-grounded — generate one plausible,
concrete micro-business idea suited to the stack/interests above. Do not
invent specific named companies or people; keep it general and actionable.

--- DATA ---

{frontier_official}
{frontier_analysis}
{tools}
{gcc_jobs}
{remote_jobs}
"""


def curate_daily_feed(sections: dict, profile_path: str = "profile.json") -> str:
    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    prompt = build_prompt(sections, profile)

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config={"temperature": 0.3, "max_output_tokens": 1200},
    )
    return response.text


if __name__ == "__main__":
    # Sample data shaped like real fetch output, no network call — lets
    # you check the prompt/section assembly logic before spending a real
    # token on it. Run this first; only call curate_daily_feed for real
    # once this looks right.
    sample_sections = {
        "frontier_official": [
            {"title": "Introducing Gemini 3.6 Flash", "source": "deepmind", "url": "https://deepmind.google/blog/x"},
        ],
        "frontier_analysis": [
            {"title": "Import AI 465: Open vs closed gaps", "source": "import_ai", "url": "https://importai.substack.com/x"},
        ],
        "tools": [],  # empty on purpose, to check the "no update" path
        "gcc_jobs": [],  # never built — should always show "No update today."
        "remote_jobs": [
            {"title": ".NET Backend Developer", "company": "FinTechCo", "url": "https://example.com/job"},
        ],
    }
    sample_profile = {"primary_stack": [".NET", "C#", "Azure"], "interests": ["agentic AI"]}
    prompt = build_prompt(sample_sections, sample_profile)
    print(prompt)