"""Shared fixtures for ingestion tests."""

import pytest
from qdrant_client import QdrantClient

from ragdoll.ingestion.sparse_embedding import get_model


@pytest.fixture(scope="session")
def sparse_model():
    """Load the real BM25 model once per test session (loading is expensive)."""
    return get_model()


@pytest.fixture(scope="session")
def qdrant_client():
    """Real client against the local docker-compose Qdrant. Skips if unreachable."""
    client = QdrantClient(url="http://localhost:6333")
    try:
        client.get_collections()
    except Exception as e:
        pytest.skip(f"Local Qdrant not reachable at localhost:6333: {e}")
    return client
