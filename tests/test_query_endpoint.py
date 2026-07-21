"""Unit tests for POST /query: FastAPI wiring only. hybrid_search() itself is
tested separately in test_hybrid_search.py — mocking it here keeps this test
from depending on Bedrock/Qdrant/fastembed at all, and isolates "does the
endpoint build the right request / shape the right response" from "does the
retrieval logic work"."""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from qdrant_client.models import ScoredPoint

import ragdoll.api.query as query_module
from ragdoll.api.app import create_app
from ragdoll.api.config import Settings
from ragdoll.api.dependencies import (
    get_bedrock_client,
    get_qdrant_client,
    get_settings,
    get_sparse_model,
)


def _client_with_overrides() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_bedrock_client] = lambda: object()
    app.dependency_overrides[get_sparse_model] = lambda: object()
    app.dependency_overrides[get_qdrant_client] = lambda: object()
    app.dependency_overrides[get_settings] = lambda: Settings(collection_name="ragdoll_chunks")
    return TestClient(app)


def test_query_endpoint_returns_hybrid_search_results(monkeypatch):
    fake_point = ScoredPoint(
        id="11111111-1111-1111-1111-111111111111",
        version=0,
        score=0.75,
        payload={"source": "doc.pdf", "chunk_index": 2, "text": "hello world"},
    )
    mock_hybrid_search = AsyncMock(return_value=[fake_point])
    monkeypatch.setattr(query_module, "hybrid_search", mock_hybrid_search)

    client = _client_with_overrides()
    response = client.post("/query", json={"text": "hello", "limit": 3})

    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {"source": "doc.pdf", "chunk_index": 2, "text": "hello world", "score": 0.75}
        ]
    }

    mock_hybrid_search.assert_called_once()
    _, kwargs = mock_hybrid_search.call_args
    assert kwargs["query_text"] == "hello"
    assert kwargs["limit"] == 3


def test_query_endpoint_skips_points_without_payload(monkeypatch):
    point_without_payload = ScoredPoint(
        id="22222222-2222-2222-2222-222222222222",
        version=0,
        score=0.5,
        payload=None,
    )
    mock_hybrid_search = AsyncMock(return_value=[point_without_payload])
    monkeypatch.setattr(query_module, "hybrid_search", mock_hybrid_search)

    client = _client_with_overrides()
    response = client.post("/query", json={"text": "hello"})

    assert response.status_code == 200
    assert response.json() == {"results": []}
