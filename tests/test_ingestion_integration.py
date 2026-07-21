"""Integration test: chunk -> embed (dense mocked, sparse real) -> write -> read back.

Dense embedding is mocked here (no real Bedrock call) because this test's
purpose is proving the *Qdrant round trip* — collection creation, point
writing, payload/vector retrieval — not AWS connectivity. Sparse uses the
real local model, same as test_sparse_embedding.py.
"""

from ragdoll.ingestion.qdrant_collection import (
    DENSE_VECTOR_NAME,
    DENSE_VECTOR_SIZE,
    SPARSE_VECTOR_NAME,
    ensure_collection,
)
from ragdoll.ingestion.qdrant_writer import build_point, upsert_chunks
from ragdoll.ingestion.sparse_embedding import embed_documents

TEST_COLLECTION = "ragdoll_test_integration"


def test_write_and_read_back_hybrid_point(qdrant_client, sparse_model):
    ensure_collection(qdrant_client, TEST_COLLECTION)

    try:
        text = "hello world"
        dense_vector = [0.1] * DENSE_VECTOR_SIZE
        sparse_vector = embed_documents(sparse_model, [text])[0]

        point = build_point("integration_test.pdf", 0, text, dense_vector, sparse_vector)
        upsert_chunks(qdrant_client, TEST_COLLECTION, [point])

        [retrieved] = qdrant_client.retrieve(
            TEST_COLLECTION,
            ids=[point.id],
            with_vectors=True,
            with_payload=True,
        )

        assert retrieved.payload == {
            "source": "integration_test.pdf",
            "chunk_index": 0,
            "text": text,
        }
        assert DENSE_VECTOR_NAME in retrieved.vector
        assert SPARSE_VECTOR_NAME in retrieved.vector
    finally:
        qdrant_client.delete_collection(TEST_COLLECTION)
