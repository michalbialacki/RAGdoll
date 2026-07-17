"""Assemble chunk + dense + sparse embeddings into Qdrant points and write them."""
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, SparseVector

from ragdoll.ingestion.qdrant_collection import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME


def build_point(
    source: str,
    chunk_index: int,
    text: str,
    dense_vector: list[float],
    sparse_vector: SparseVector,
) -> PointStruct:
    """Build one Qdrant point: dense + sparse named vectors, payload = metadata + text.

    id is a deterministic uuid5 of (source, chunk_index): re-ingesting the same
    document overwrites its existing points instead of duplicating them.
    """
    namespace = uuid.NAMESPACE_DNS
    name = f"{source}_{chunk_index}"
    point_id = str(uuid.uuid5(namespace,name))
    payload = {
        "source": source,
        "chunk_index": chunk_index,
        "text": text,
    }
    return PointStruct(
        id=point_id,
        vector={
            DENSE_VECTOR_NAME: dense_vector,
            SPARSE_VECTOR_NAME: sparse_vector,
        },
        payload=payload,
    )


def upsert_chunks(client: QdrantClient, collection_name: str, points: list[PointStruct]) -> None:
    """Write points to Qdrant."""
    client.upsert(
        collection_name=collection_name,
        points=points,
        wait=True # pewnosc ze wszystko zostalo zaindeksowane i zwroci kontrole
    )
