"""Hybrid retrieval: dense + sparse prefetch, fused with Qdrant's native RRF."""

import asyncio
from typing import Any

from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Fusion, FusionQuery, Prefetch, ScoredPoint

from ragdoll.ingestion.dense_embedding import embed_texts
from ragdoll.ingestion.qdrant_collection import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
from ragdoll.ingestion.sparse_embedding import embed_query

PREFETCH_LIMIT = 20


async def hybrid_search(
    bedrock_client: Any,
    sparse_model: SparseTextEmbedding,
    qdrant_client: QdrantClient,
    collection_name: str,
    query_text: str,
    limit: int = 5,
) -> list[ScoredPoint]:
    """Embed the query (dense + sparse), run RRF-fused search, return top-k points.

    Dense and sparse embedding are independent (no data dependency between them)
    — TODO 1: run them concurrently instead of awaiting one after the other.
    Hint: embed_texts() is async and already retry-wrapped; embed_query() is
    sync/local (fastembed, no network call) so it doesn't need to join the gather.

    TODO 2: build the Query API call.
    - prefetch: one Prefetch per vector type (dense via DENSE_VECTOR_NAME,
      sparse via SPARSE_VECTOR_NAME), each with its own query vector and
      `limit=PREFETCH_LIMIT` — this is the candidate pool BEFORE fusion,
      deliberately wider than the final `limit`.
    - query: FusionQuery(fusion=Fusion.RRF) — tells Qdrant to fuse the two
      prefetch result lists via RRF instead of returning them separately.
    - top-level `limit`: the final number of fused results to return.

    Use qdrant_client.query_points(...) and return `.points`.
    """
    dense_task = embed_texts(bedrock_client, [query_text])
    sparse_task = asyncio.to_thread(embed_query, sparse_model, query_text)
    dense_vectors, sparse_vector = await asyncio.gather(dense_task, sparse_task)
    dense_vector = dense_vectors[0]

    response = qdrant_client.query_points(
        collection_name=collection_name,
        prefetch=[
            Prefetch(query=dense_vector, using=DENSE_VECTOR_NAME, limit=PREFETCH_LIMIT),
            Prefetch(query=sparse_vector, using=SPARSE_VECTOR_NAME, limit=PREFETCH_LIMIT),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=limit,
    )
    return response.points
