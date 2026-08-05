from unittest.mock import MagicMock

from qdrant_client.models import SparseVector

from ragdoll.ingestion.qdrant_collection import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
from ragdoll.ingestion.qdrant_writer import build_point, upsert_chunks

DENSE = [0.1] * 1024
SPARSE = SparseVector(indices=[1, 2, 3], values=[0.5, 0.3, 0.1])


def test_build_point_id_is_deterministic():
    p1 = build_point("doc.pdf", 3, "hello world", DENSE, SPARSE)
    p2 = build_point("doc.pdf", 3, "hello world", DENSE, SPARSE)
    assert p1.id == p2.id


def test_build_point_id_differs_by_chunk_index():
    p1 = build_point("doc.pdf", 3, "hello world", DENSE, SPARSE)
    p2 = build_point("doc.pdf", 4, "hello world", DENSE, SPARSE)
    assert p1.id != p2.id


def test_build_point_payload_and_vectors():
    p = build_point("doc.pdf", 3, "hello world", DENSE, SPARSE)
    assert p.payload == {"source": "doc.pdf", "chunk_index": 3, "text": "hello world"}
    assert p.vector[DENSE_VECTOR_NAME] == DENSE
    assert p.vector[SPARSE_VECTOR_NAME] == SPARSE


def test_upsert_chunks_calls_client_with_wait_true():
    client = MagicMock()
    point = build_point("doc.pdf", 3, "hello world", DENSE, SPARSE)
    upsert_chunks(client, "ragdoll_chunks", [point])
    client.upsert.assert_called_once_with(
        collection_name="ragdoll_chunks", points=[point], wait=True
    )
