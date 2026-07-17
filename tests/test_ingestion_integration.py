"""Integration test: chunk -> embed (dense mocked, sparse real) -> write -> read back.

Dense embedding is mocked here (no real Bedrock call) because this test's
purpose is proving the *Qdrant round trip* — collection creation, point
writing, payload/vector retrieval — not AWS connectivity. Sparse uses the
real local model, same as test_sparse_embedding.py.
"""

from unittest.mock import MagicMock

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
    # TODO:
    # 1. ensure_collection(qdrant_client, TEST_COLLECTION)
    # 2. build a fake dense vector: [0.1] * DENSE_VECTOR_SIZE (mocked — no
    #    real Bedrock call needed for this test's purpose)
    # 3. get a real sparse vector: embed_documents(sparse_model, ["hello world"])[0]
    # 4. build_point("integration_test.pdf", 0, "hello world", dense_vector, sparse_vector)
    # 5. upsert_chunks(qdrant_client, TEST_COLLECTION, [point])
    # 6. read it back: qdrant_client.retrieve(TEST_COLLECTION, ids=[point.id],
    #    with_vectors=True, with_payload=True)
    # 7. assert the retrieved point's payload matches what you wrote, and
    #    that both DENSE_VECTOR_NAME and SPARSE_VECTOR_NAME are present in
    #    its vector dict
    # 8. cleanup: qdrant_client.delete_collection(TEST_COLLECTION) — tests
    #    shouldn't leave state behind for the next run
    raise NotImplementedError
