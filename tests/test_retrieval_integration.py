"""Integration test: real Qdrant Query API + real RRF fusion.

Dense embedding is mocked (no real Bedrock call) — same rationale as
test_ingestion_integration.py: this test proves the Qdrant round trip
(prefetch + RRF fusion actually returns the point we wrote), not AWS
connectivity. Sparse uses the real local BM25 model so the exact-token-match
retrieval path is genuine, not simulated.
"""

import json
from unittest.mock import MagicMock

from ragdoll.ingestion.qdrant_collection import DENSE_VECTOR_SIZE, ensure_collection
from ragdoll.ingestion.qdrant_writer import build_point, upsert_chunks
from ragdoll.ingestion.sparse_embedding import embed_documents
from ragdoll.retrieval.hybrid_search import hybrid_search

TEST_COLLECTION = "ragdoll_test_retrieval"


def _mock_bedrock_response(embedding: list[float]) -> dict:
    body = MagicMock()
    body.read.return_value = json.dumps({"embedding": embedding}).encode()
    return {"body": body}


async def test_hybrid_search_finds_point_by_exact_token(qdrant_client, sparse_model):
    ensure_collection(qdrant_client, TEST_COLLECTION)

    try:
        text = "the zebra1234 identifier is unique in this document"
        dense_vector = [0.1] * DENSE_VECTOR_SIZE
        sparse_vector = embed_documents(sparse_model, [text])[0]

        point = build_point("retrieval_test.pdf", 0, text, dense_vector, sparse_vector)
        upsert_chunks(qdrant_client, TEST_COLLECTION, [point])

        bedrock_client = MagicMock()
        bedrock_client.invoke_model.return_value = _mock_bedrock_response(
            [0.1] * DENSE_VECTOR_SIZE
        )

        results = await hybrid_search(
            bedrock_client=bedrock_client,
            sparse_model=sparse_model,
            qdrant_client=qdrant_client,
            collection_name=TEST_COLLECTION,
            query_text="zebra1234",
            limit=5,
        )

        assert len(results) == 1
        assert results[0].payload["source"] == "retrieval_test.pdf"
        assert results[0].payload["text"] == text
    finally:
        qdrant_client.delete_collection(TEST_COLLECTION)
