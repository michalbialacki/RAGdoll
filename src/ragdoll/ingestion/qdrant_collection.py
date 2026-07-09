"""Qdrant collection setup: one point per chunk, dense + sparse named vectors.

Dense: Bedrock Titan Embeddings V2, 1024 dims, Cosine distance, HNSW-indexed.
Sparse: fastembed BM25 (Qdrant/bm25), inverted-index, IDF-weighted at query time.

HNSW `m`/`ef_construct` are left at Qdrant defaults (16 / 100) — at this PoC's
scale (single document, low hundreds of chunks) approximate search is not
meaningfully different from brute-force, so tuning them here would optimize
a problem we don't have yet.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Modifier,
    SparseVectorParams,
    VectorParams,
)

DENSE_VECTOR_NAME = "dense_vector"
SPARSE_VECTOR_NAME = "sparse_vector"
DENSE_VECTOR_SIZE = 1024


def ensure_collection(client: QdrantClient, collection_name: str) -> None:
    """Create the collection if it doesn't already exist."""
    if client.collection_exists(collection_name):
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config={
            DENSE_VECTOR_NAME: VectorParams(
                size=DENSE_VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        },
        sparse_vectors_config={
            SPARSE_VECTOR_NAME: SparseVectorParams(
                modifier=Modifier.IDF,
            ),
        },
    )
