"""Context injection: filter retrieved chunks by relevance, build the LLM prompt.

RRF fusion scores are rank-based (sum of 1/(k+rank) across the fused lists), not a
cosine similarity in [0, 1] — a "good" score depends on Qdrant's RRF k (default 60)
and how many prefetch lists are fused, not on some universal cutoff like 0.7. The
threshold below is a starting point for k=60 / two-list fusion, not a derived
constant — it needs empirical calibration against real queries (Phase 04 territory).
"""

from qdrant_client.models import ScoredPoint

SYSTEM_PROMPT = (
    "You are a support assistant. Answer the question using ONLY the context "
    "provided below. If the context does not contain enough information to "
    "answer, say you don't know instead of guessing — do not use outside "
    "knowledge."
)

MIN_RRF_SCORE = 0.01


def has_sufficient_context(points: list[ScoredPoint], min_score: float = MIN_RRF_SCORE) -> bool:
    """Cheap, deterministic gate before spending a token on the LLM call.

    Defense in depth with SYSTEM_PROMPT's instruction, not a replacement for it —
    this catches the case up front (no LLM call at all), the prompt instruction
    catches whatever slips past the threshold.
    """
    return bool(points) and points[0].score >= min_score


def build_prompt(query_text: str, points: list[ScoredPoint]) -> str:
    context = "\n\n".join(
        f"[{point.payload['source']} #{point.payload['chunk_index']}]\n{point.payload['text']}"
        for point in points
        if point.payload is not None
    )
    return f"Context:\n{context}\n\nQuestion: {query_text}"
