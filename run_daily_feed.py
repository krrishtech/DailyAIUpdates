"""
The real daily pipeline. Replaces the two placeholder steps in daily.yml
(send_hello.py and the dedup_filter.py demo call) with the actual thing:

fetch (4 sources, no LLM) -> dedup (embeddings, no LLM) ->
relevance filter (embeddings, no LLM) -> curate & generate (the one LLM call)
-> deliver (Telegram, no LLM)

Only one step in this entire script calls an LLM. Everything else is
deterministic code — this is the design principle the whole project was
built around, not an afterthought.
"""
from fetch_tools import fetch_all_tools
from fetch_news import fetch_all_news
from fetch_remote_jobs import fetch_remote_jobs
from fetch_weworkremotely import fetch_weworkremotely_jobs
from dedup_filter import dedup_items
from relevance_filter import filter_relevant
from curate_agent import curate_daily_feed
from send_hello import send_telegram_message

HISTORY_PATH = "dedup_history.json"


def run() -> None:
    # --- Fetch (no LLM, no tokens) ---
    tools = fetch_all_tools()
    news = fetch_all_news()
    remote_jobs = fetch_remote_jobs() + fetch_weworkremotely_jobs()
    gcc_jobs: list[dict] = []  # never built — GCC career-page scraping deferred

    # --- Dedup (embeddings, no LLM) — shared history file across categories ---
    tools = dedup_items(tools, HISTORY_PATH, text_key="name")
    news = dedup_items(news, HISTORY_PATH, text_key="title")
    remote_jobs = dedup_items(remote_jobs, HISTORY_PATH, text_key="title")

    # --- Relevance filter (embeddings, no LLM) — only news needs this;
    # tools/jobs already have their own keyword+structure gates built
    # into their fetch scripts, proven in earlier testing ---
    news = filter_relevant(news, text_key="title")

    frontier_official = [n for n in news if n.get("kind") == "official"]
    frontier_analysis = [n for n in news if n.get("kind") == "analysis"]

    sections = {
        "frontier_official": frontier_official,
        "frontier_analysis": frontier_analysis,
        "tools": tools,
        "gcc_jobs": gcc_jobs,
        "remote_jobs": remote_jobs,
    }

    # --- Curate & generate (the ONE LLM call) ---
    message = curate_daily_feed(sections)

    # --- Deliver (no LLM) ---
    send_telegram_message(message)


if __name__ == "__main__":
    run()