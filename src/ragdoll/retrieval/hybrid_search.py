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
    use_sparse: bool = True,
) -> list[ScoredPoint]:
    """Embed the query (dense + sparse), run RRF-fused search, return top-k points.

    `use_sparse=False` gives a dense-only baseline for Phase 04's comparison —
    it still goes through FusionQuery(fusion=Fusion.RRF) with a single prefetch
    list, not a plain vector search. RRF score is rank-based (1/(k+rank)), not
    cosine similarity, so keeping fusion in both modes keeps scores on the same
    scale — comparing a dense-only cosine score against a hybrid RRF score
    directly would be apples-to-oranges.
    """
    if use_sparse:
        dense_task = embed_texts(bedrock_client, [query_text])
        sparse_task = asyncio.to_thread(embed_query, sparse_model, query_text)
        dense_vectors, sparse_vector = await asyncio.gather(dense_task, sparse_task)
    else:
        dense_vectors = await embed_texts(bedrock_client, [query_text])
    dense_vector = dense_vectors[0]

    prefetch = [Prefetch(query=dense_vector, using=DENSE_VECTOR_NAME, limit=PREFETCH_LIMIT)]
    if use_sparse:
        prefetch.append(
            Prefetch(query=sparse_vector, using=SPARSE_VECTOR_NAME, limit=PREFETCH_LIMIT)
        )

    response = qdrant_client.query_points(
        collection_name=collection_name,
        prefetch=prefetch,
        query=FusionQuery(fusion=Fusion.RRF),
        limit=limit,
    )
    return response.points
