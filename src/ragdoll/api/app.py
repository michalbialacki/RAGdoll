from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ragdoll.api.config import Settings
from ragdoll.api.dependencies import build_bedrock_client, build_qdrant_client, build_sparse_model
from ragdoll.api.query import router as query_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build expensive clients once at startup, tear them down at shutdown."""
    settings = Settings()
    app.state.settings = settings
    app.state.bedrock_client = build_bedrock_client(settings)
    app.state.sparse_model = build_sparse_model()
    app.state.qdrant_client = build_qdrant_client(settings)
    yield
    app.state.qdrant_client.close()


def create_app() -> FastAPI:
    app = FastAPI(title="RAGdoll", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(query_router)

    return app
