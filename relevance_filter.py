"""
Step 3: relevance filter. No LLM here — same embedding technique as
dedup_filter.py, applied to a different question: not "have I seen this
before" but "does this actually belong in the digest."

This is exactly what would have cleaned up the noise seen in real
testing — Google's "AI blog" returning Galaxy Unpacked phone news and
Xbox backward-compatibility posts, none of which are AI-relevant despite
coming from an "AI" feed URL. Keyword filtering can't fix that (the
Microsoft/Google problem was never about missing keywords, it's about
topic drift) — this is a job for semantic similarity, not string matching.

Threshold note: relevance similarity scores run on a DIFFERENT, LOWER
scale than dedup's duplicate-detection threshold (0.87). Topically
related-but-distinct text typically scores 0.3-0.6 with this model,
while near-duplicates score 0.85+. Don't reuse the dedup threshold here.
"""
import numpy as np
from dedup_filter import embed_texts, cosine_similarity

# Contrastive scoring, not an absolute threshold. Real testing showed why:
# short titles + a small embedding model don't separate "new AI model" from
# "search feature" or "phone launch" cleanly on absolute similarity alone —
# everything reads as generic "Google/Microsoft product news" at a shallow
# level. Scoring relevant-similarity MINUS irrelevant-similarity cancels out
# that shared baseline pull and gives real separation instead.
# Tuned from real output: relevant items scored -0.063 to +0.119, irrelevant
# items scored -0.119 to -0.156 — a real gap exists, just not centered on
# zero like the initial guess assumed. -0.09 sits in that gap. This is
# based on 6 real examples, not a large sample — expect to keep adjusting
# as more real daily output comes through, same as every threshold so far.
RELEVANCE_MARGIN = -0.09

POSITIVE_ANCHORS = [
    "New AI model release, pricing change, or API feature from a major AI lab like OpenAI, Anthropic, Google, or Microsoft",
    "Agentic AI framework, tool, or automation for software developers",
    "Backend software engineering with .NET, C#, SQL Server, Azure, or Kafka",
    "AI applied to banking, fraud detection, or financial crime prevention",
]

# What should get REJECTED — added because absolute-threshold scoring
# couldn't tell "AI model launch" apart from "search feature" or "phone
# launch" using only short titles. This is the fix for that.
NEGATIVE_ANCHORS = [
    "Consumer hardware, phone, or gaming console news",
    "General search engine, video, or productivity product feature update",
    "Company announcement unrelated to AI models or software engineering",
]

_positive_embeddings = None
_negative_embeddings = None


def _get_positive_embeddings() -> np.ndarray:
    global _positive_embeddings
    if _positive_embeddings is None:
        _positive_embeddings = embed_texts(POSITIVE_ANCHORS)
    return _positive_embeddings


def _get_negative_embeddings() -> np.ndarray:
    global _negative_embeddings
    if _negative_embeddings is None:
        _negative_embeddings = embed_texts(NEGATIVE_ANCHORS)
    return _negative_embeddings


def relevance_score(item_vector: np.ndarray) -> float:
    pos_sim = max(cosine_similarity(item_vector, a) for a in _get_positive_embeddings())
    neg_sim = max(cosine_similarity(item_vector, a) for a in _get_negative_embeddings())
    return pos_sim - neg_sim


def filter_relevant(
    items: list[dict],
    text_key: str = "title",
    threshold: float = RELEVANCE_MARGIN,
    show_scores: bool = False,
) -> list[dict]:
    if not items:
        return []

    texts = [item.get(text_key, "") for item in items]
    vectors = embed_texts(texts)

    kept = []
    for item, vector in zip(items, vectors):
        score = relevance_score(vector)
        if show_scores:
            print(f"  {score:+.3f}  {item.get(text_key, '')}")
        if score >= threshold:
            kept.append(item)

    return kept


if __name__ == "__main__":
    # Real titles pulled directly from your actual fetch_news.py output —
    # a mix of items that SHOULD pass and ones that SHOULDN'T, so you can
    # see real scores and tune RELEVANCE_THRESHOLD against them.
    real_test_items = [
        {"title": "Introducing MAI-Image-2.5-Pro and MAI-Voice-2-Flash"},
        {"title": "Expanding Managed Agents in Gemini API: background tasks, remote MCP and more"},
        {"title": "Introducing Gemini 3.6 Flash, 3.5 Flash-Lite, and 3.5 Flash Cyber"},
        {"title": "3 Google updates from Galaxy Unpacked 2026"},
        {"title": "XBOX brings classic games to PC and handhelds"},
        {"title": "Celebrating 25 years of visual search innovation"},
    ]
    print("Contrastive scores (want: first 3 positive, last 3 negative or near-zero):")
    kept = filter_relevant(real_test_items, show_scores=True)
    print(f"\nKept {len(kept)} of {len(real_test_items)}:")
    for item in kept:
        print(f"  - {item['title']}")