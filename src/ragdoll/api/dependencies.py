"""Client construction and FastAPI dependency wiring.

Bedrock client, sparse model, and Qdrant client are expensive to build (network
handshake / model weights load) — each is created once at app startup via the
lifespan context in app.py and stashed on app.state, then handed out per-request
via these Depends functions instead of being rebuilt per call.
"""

from typing import Any, cast

import boto3
from fastapi import Request
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient

from ragdoll.api.config import Settings


def build_bedrock_client(settings: Settings) -> Any:
    return boto3.client("bedrock-runtime", region_name=settings.aws_region)


def build_sparse_model() -> SparseTextEmbedding:
    from ragdoll.ingestion.sparse_embedding import get_model

    return get_model()


def build_qdrant_client(settings: Settings) -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def get_bedrock_client(request: Request) -> Any:
    return request.app.state.bedrock_client


def get_sparse_model(request: Request) -> SparseTextEmbedding:
    return cast(SparseTextEmbedding, request.app.state.sparse_model)


def get_qdrant_client(request: Request) -> QdrantClient:
    return cast(QdrantClient, request.app.state.qdrant_client)


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)
