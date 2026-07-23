"""POST /query — hybrid retrieval + Bedrock LLM generation (Phase 03)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastembed import SparseTextEmbedding
from pydantic import BaseModel
from qdrant_client import QdrantClient

from ragdoll.api.config import Settings
from ragdoll.api.dependencies import (
    get_bedrock_client,
    get_qdrant_client,
    get_settings,
    get_sparse_model,
)
from ragdoll.generation.answer_service import answer_query
from ragdoll.retrieval.hybrid_search import hybrid_search

router = APIRouter()


class QueryRequest(BaseModel):
    text: str
    limit: int = 5


class RetrievedChunk(BaseModel):
    source: str
    chunk_index: int
    text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[RetrievedChunk]


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    bedrock_client: Annotated[Any, Depends(get_bedrock_client)],
    sparse_model: Annotated[SparseTextEmbedding, Depends(get_sparse_model)],
    qdrant_client: Annotated[QdrantClient, Depends(get_qdrant_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> QueryResponse:
    points = await hybrid_search(
        bedrock_client=bedrock_client,
        sparse_model=sparse_model,
        qdrant_client=qdrant_client,
        collection_name=settings.collection_name,
        query_text=request.text,
        limit=request.limit,
    )
    sources = [
        RetrievedChunk(
            source=point.payload["source"],
            chunk_index=point.payload["chunk_index"],
            text=point.payload["text"],
            score=point.score,
        )
        for point in points
        if point.payload is not None
    ]
    answer = await answer_query(bedrock_client, request.text, points)
    return QueryResponse(answer=answer, sources=sources)
