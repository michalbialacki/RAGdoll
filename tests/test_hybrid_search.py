"""Unit tests for hybrid_search: correct Query API call shape, mocked clients."""

import json
from unittest.mock import MagicMock

from qdrant_client.models import Fusion, FusionQuery, Prefetch, ScoredPoint

from ragdoll.ingestion.qdrant_collection import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
from ragdoll.retrieval.hybrid_search import PREFETCH_LIMIT, hybrid_search


def _mock_bedrock_response(embedding: list[float]) -> dict:
    body = MagicMock()
    body.read.return_value = json.dumps({"embedding": embedding}).encode()
    return {"body": body}


async def test_hybrid_search_calls_query_points_with_dense_and_sparse_prefetch(sparse_model):
    bedrock_client = MagicMock()
    bedrock_client.invoke_model.return_value = _mock_bedrock_response([0.1, 0.2, 0.3])

    fake_point = ScoredPoint(
        id="11111111-1111-1111-1111-111111111111",
        version=0,
        score=0.9,
        payload={"source": "doc.pdf", "chunk_index": 0, "text": "hello world"},
    )
    qdrant_client = MagicMock()
    qdrant_client.query_points.return_value = MagicMock(points=[fake_point])

    result = await hybrid_search(
        bedrock_client=bedrock_client,
        sparse_model=sparse_model,
        qdrant_client=qdrant_client,
        collection_name="ragdoll_chunks",
        query_text="hello world",
        limit=5,
    )

    assert result == [fake_point]

    qdrant_client.query_points.assert_called_once()
    _, kwargs = qdrant_client.query_points.call_args
    assert kwargs["collection_name"] == "ragdoll_chunks"
    assert kwargs["limit"] == 5
    assert kwargs["query"] == FusionQuery(fusion=Fusion.RRF)

    prefetches = kwargs["prefetch"]
    assert len(prefetches) == 2
    dense_prefetch = next(p for p in prefetches if p.using == DENSE_VECTOR_NAME)
    sparse_prefetch = next(p for p in prefetches if p.using == SPARSE_VECTOR_NAME)
    assert isinstance(dense_prefetch, Prefetch)
    assert dense_prefetch.query == [0.1, 0.2, 0.3]
    assert dense_prefetch.limit == PREFETCH_LIMIT
    assert isinstance(sparse_prefetch, Prefetch)
    assert sparse_prefetch.limit == PREFETCH_LIMIT


async def test_hybrid_search_dense_only_skips_sparse_prefetch_but_keeps_rrf_fusion(sparse_model):
    bedrock_client = MagicMock()
    bedrock_client.invoke_model.return_value = _mock_bedrock_response([0.1, 0.2, 0.3])
    qdrant_client = MagicMock()
    qdrant_client.query_points.return_value = MagicMock(points=[])

    await hybrid_search(
        bedrock_client=bedrock_client,
        sparse_model=sparse_model,
        qdrant_client=qdrant_client,
        collection_name="ragdoll_chunks",
        query_text="hello world",
        limit=5,
        use_sparse=False,
    )

    _, kwargs = qdrant_client.query_points.call_args
    # still fused via RRF (not a plain vector search) so scores stay on the same
    # 1/(k+rank) scale as the hybrid mode — see hybrid_search.py docstring.
    assert kwargs["query"] == FusionQuery(fusion=Fusion.RRF)
    prefetches = kwargs["prefetch"]
    assert len(prefetches) == 1
    assert prefetches[0].using == DENSE_VECTOR_NAME


async def test_hybrid_search_embeds_query_not_document(sparse_model, monkeypatch):
    """query_embed (presence weights) must be used, not embed_documents (TF weights) —
    see the asymmetry documented in sparse_embedding.py. Using the wrong one wouldn't
    raise an error, it would just silently degrade sparse retrieval quality, so this
    is asserted explicitly rather than left to be caught by chance."""
    import ragdoll.retrieval.hybrid_search as hybrid_search_module

    calls = []
    original_embed_query = hybrid_search_module.embed_query

    def spy_embed_query(model, text):
        calls.append(text)
        return original_embed_query(model, text)

    monkeypatch.setattr(hybrid_search_module, "embed_query", spy_embed_query)

    bedrock_client = MagicMock()
    bedrock_client.invoke_model.return_value = _mock_bedrock_response([0.1])
    qdrant_client = MagicMock()
    qdrant_client.query_points.return_value = MagicMock(points=[])

    await hybrid_search(
        bedrock_client=bedrock_client,
        sparse_model=sparse_model,
        qdrant_client=qdrant_client,
        collection_name="ragdoll_chunks",
        query_text="zebra123",
        limit=5,
    )

    assert calls == ["zebra123"]
