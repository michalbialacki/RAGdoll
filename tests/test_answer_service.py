"""Unit tests for answer_service orchestration (Phase 03 Step 02/03).

generate_answer is mocked (its own behavior is covered by test_llm_client.py) — this
test is only about the branch: skip the LLM call entirely when context is too weak,
call it when context is sufficient.
"""

from unittest.mock import AsyncMock

import pytest
from qdrant_client.models import ScoredPoint

import ragdoll.generation.answer_service as answer_service_module
from ragdoll.generation.answer_service import NO_CONTEXT_ANSWER, answer_query


def _point(score: float) -> ScoredPoint:
    return ScoredPoint(
        id="11111111-1111-1111-1111-111111111111",
        version=0,
        score=score,
        payload={"source": "doc.pdf", "chunk_index": 0, "text": "chunk text"},
    )


@pytest.mark.asyncio
async def test_answer_query_skips_llm_when_context_too_weak(monkeypatch):
    mock_generate_answer = AsyncMock(return_value="should not be called")
    monkeypatch.setattr(answer_service_module, "generate_answer", mock_generate_answer)

    result = await answer_query(bedrock_client=object(), query_text="q", points=[])

    assert result == NO_CONTEXT_ANSWER
    mock_generate_answer.assert_not_called()


@pytest.mark.asyncio
async def test_answer_query_calls_llm_when_context_sufficient(monkeypatch):
    mock_generate_answer = AsyncMock(return_value="the answer")
    monkeypatch.setattr(answer_service_module, "generate_answer", mock_generate_answer)
    client = object()

    result = await answer_query(bedrock_client=client, query_text="q", points=[_point(0.5)])

    assert result == "the answer"
    mock_generate_answer.assert_called_once()
    args, _ = mock_generate_answer.call_args
    assert args[0] is client
