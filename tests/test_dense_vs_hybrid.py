"""Phase 04: proof that hybrid search recovers exact identifiers dense-only misses.

Real Qdrant + real BM25 sparse model (same rationale as test_retrieval_integration.py).
Dense embedding is mocked, but deliberately NOT constant — two orthogonal unit vectors
so cosine similarity is fully deterministic:

- doc_generic: dense vector identical to the query vector (cosine = 1, wins on dense
  alone) — a generic sentence, no mention of the exact identifier.
- doc_identifier: dense vector orthogonal to the query vector (cosine = 0, loses on
  dense alone) — contains the exact identifier "zebra1234", which the query asks for.

This models a real failure mode: an out-of-vocabulary identifier can embed far from
the query in dense space even though it's the textually exact match, while BM25
rewards the exact token regardless of semantic embedding distance.

dense-only search still goes through FusionQuery(fusion=Fusion.RRF) with a single
prefetch list (see hybrid_search.py) so its scores are on the same 1/(k+rank) scale
as the hybrid scores — comparing rank order, not raw cosine vs RRF magnitude.
"""

import json
from unittest.mock import MagicMock

from ragdoll.ingestion.qdrant_collection import DENSE_VECTOR_SIZE, ensure_collection
from ragdoll.ingestion.qdrant_writer import build_point, upsert_chunks
from ragdoll.ingestion.sparse_embedding import embed_documents
from ragdoll.retrieval.hybrid_search import hybrid_search

TEST_COLLECTION = "ragdoll_test_dense_vs_hybrid"


def _unit_vector(hot_index: int) -> list[float]:
    vector = [0.0] * DENSE_VECTOR_SIZE
    vector[hot_index] = 1.0
    return vector


def _mock_bedrock_response(embedding: list[float]) -> dict:
    body = MagicMock()
    body.read.return_value = json.dumps({"embedding": embedding}).encode()
    return {"body": body}


async def test_hybrid_beats_dense_only_on_exact_identifier(qdrant_client, sparse_model):
    ensure_collection(qdrant_client, TEST_COLLECTION)

    query_dense_vector = _unit_vector(0)

    try:
        generic_text = "the quarterly report summarizes overall performance trends"
        identifier_text = "the zebra1234 identifier is unique in this document"

        generic_point = build_point(
            "generic.pdf",
            0,
            generic_text,
            dense_vector=query_dense_vector,  # cosine = 1 with the query
            sparse_vector=embed_documents(sparse_model, [generic_text])[0],
        )
        identifier_point = build_point(
            "identifier.pdf",
            0,
            identifier_text,
            dense_vector=_unit_vector(1),  # orthogonal to the query, cosine = 0
            sparse_vector=embed_documents(sparse_model, [identifier_text])[0],
        )
        upsert_chunks(qdrant_client, TEST_COLLECTION, [generic_point, identifier_point])

        bedrock_client = MagicMock()
        bedrock_client.invoke_model.return_value = _mock_bedrock_response(query_dense_vector)

        dense_only_results = await hybrid_search(
            bedrock_client=bedrock_client,
            sparse_model=sparse_model,
            qdrant_client=qdrant_client,
            collection_name=TEST_COLLECTION,
            query_text="zebra1234",
            limit=1,
            use_sparse=False,
        )
        hybrid_results = await hybrid_search(
            bedrock_client=bedrock_client,
            sparse_model=sparse_model,
            qdrant_client=qdrant_client,
            collection_name=TEST_COLLECTION,
            query_text="zebra1234",
            limit=1,
            use_sparse=True,
        )

        assert dense_only_results[0].payload["source"] == "generic.pdf"
        assert hybrid_results[0].payload["source"] == "identifier.pdf"
    finally:
        qdrant_client.delete_collection(TEST_COLLECTION)
