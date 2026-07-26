"""
Step 2: dedup filter. No LLM here — embeddings + cosine similarity, no
generation call. Uses fastembed (ONNX-based, no PyTorch) to keep this
step lightweight and fully free/offline after the one-time model download.

Two kinds of duplicates this catches, both seen in real testing:
1. Within-batch duplicates (e.g. "Sezzle: AI Engineer II (Remote)" showing
   up twice from WeWorkRemotely's own feed in one pull).
2. Cross-day duplicates (the same story/job sent yesterday, still present
   today) — this needs a persistent history file, since each GitHub
   Actions run starts from a clean machine with no memory of past runs.

History storage: a capped JSON file (default: last 14 days) committed
back to the repo by the workflow after each run. Capped deliberately —
an ever-growing file is exactly the "mess" we're trying to avoid.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import numpy as np
from fastembed import TextEmbedding

SIMILARITY_THRESHOLD = 0.87  # tune this after seeing real output
HISTORY_MAX_DAYS = 14

_embedder = None


def _get_embedder() -> TextEmbedding:
    # Loaded once per run, not once per item — model init has a fixed
    # cost, so this avoids paying it repeatedly in a loop.
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding()  # default model: BAAI/bge-small-en-v1.5
    return _embedder


def embed_texts(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, 384))
    embedder = _get_embedder()
    return np.array(list(embedder.embed(texts)))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def load_history(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(path: str, history: list[dict]) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=HISTORY_MAX_DAYS)
    trimmed = [
        h for h in history
        if datetime.fromisoformat(h["date"]) >= cutoff
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(trimmed, f, ensure_ascii=False, indent=2)


def dedup_items(
    items: list[dict],
    history_path: str,
    text_key: str = "title",
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict]:
    """
    Returns only the items NOT similar to anything already kept today
    or found in history. Updates and saves the history file as a
    side effect — this function is the whole Step 2 pipeline stage.
    """
    if not items:
        return []

    history = load_history(history_path)
    history_vectors = [np.array(h["embedding"]) for h in history]

    texts = [item.get(text_key, "") for item in items]
    new_vectors = embed_texts(texts)

    kept_items = []
    kept_vectors: list[np.ndarray] = []

    for item, vector in zip(items, new_vectors):
        is_duplicate = False

        # Check against everything already kept THIS run (within-batch dupes)
        for kept_vec in kept_vectors:
            if cosine_similarity(vector, kept_vec) >= threshold:
                is_duplicate = True
                break

        # Check against history (cross-day dupes), only if not already flagged
        if not is_duplicate:
            for hist_vec in history_vectors:
                if cosine_similarity(vector, hist_vec) >= threshold:
                    is_duplicate = True
                    break

        if not is_duplicate:
            kept_items.append(item)
            kept_vectors.append(vector)

    today = datetime.now(timezone.utc).isoformat()
    new_history_entries = [
        {"text": item.get(text_key, ""), "embedding": vec.tolist(), "date": today}
        for item, vec in zip(kept_items, kept_vectors)
    ]
    save_history(history_path, history + new_history_entries)

    return kept_items


if __name__ == "__main__":
    sample_items = [
        {"title": "Sezzle: AI Engineer II (Remote)"},
        {"title": "Sezzle: AI Engineer II (Remote)"},  # exact within-batch dupe
        {"title": "LaunchDarkly: Backend Engineer, Flag Delivery"},
    ]
    kept = dedup_items(sample_items, history_path="dedup_history.json")
    print(f"Kept {len(kept)} of {len(sample_items)} items:")
    for item in kept:
        print(f"  - {item['title']}")