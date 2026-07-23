"""Unit tests for the context-gate + prompt construction (Phase 03 Step 02).

No mocking needed here — has_sufficient_context and build_prompt are pure functions
over ScoredPoint objects, no network/AWS/Qdrant involved.
"""

from qdrant_client.models import ScoredPoint

from ragdoll.generation.prompt_builder import build_prompt, has_sufficient_context


def _point(
    score: float, source: str = "doc.pdf", chunk_index: int = 0, text: str = "chunk text"
) -> ScoredPoint:
    return ScoredPoint(
        id="11111111-1111-1111-1111-111111111111",
        version=0,
        score=score,
        payload={"source": source, "chunk_index": chunk_index, "text": text},
    )


def test_has_sufficient_context_true_above_threshold():
    assert has_sufficient_context([_point(0.5)]) is True


def test_has_sufficient_context_false_below_threshold():
    # 0.001 is below the default MIN_RRF_SCORE (0.01) — best match is still too weak.
    assert has_sufficient_context([_point(0.001)]) is False


def test_has_sufficient_context_false_when_empty():
    assert has_sufficient_context([]) is False


def test_build_prompt_includes_query_and_chunk_text():
    points = [_point(0.5, source="manual.pdf", chunk_index=3, text="the widget spins clockwise")]

    prompt = build_prompt("how does the widget spin?", points)

    assert "how does the widget spin?" in prompt
    assert "the widget spins clockwise" in prompt
    assert "manual.pdf" in prompt
    assert "#3" in prompt


def test_build_prompt_skips_points_without_payload():
    point_without_payload = ScoredPoint(
        id="22222222-2222-2222-2222-222222222222", version=0, score=0.5, payload=None
    )

    prompt = build_prompt("q", [point_without_payload])

    assert prompt == "Context:\n\n\nQuestion: q"
