"""Sparse embeddings via fastembed BM25 (`Qdrant/bm25`).

Runs locally on CPU — no network call, no retry/backoff needed (unlike
dense_embedding.py's Bedrock calls). embed() and query_embed() are
asymmetric: embed() produces TF-with-saturation weights per document (no
IDF baked in — that's applied by Qdrant's `Modifier.IDF` at indexing time,
see qdrant_collection.py); query_embed() produces presence weights (1.0)
per query term, since IDF is already carried on the document side.
"""

from fastembed import SparseTextEmbedding
from qdrant_client.models import SparseVector

MODEL_NAME = "Qdrant/bm25"


def get_model() -> SparseTextEmbedding:
    """Load the BM25 sparse model once; callers should reuse the instance."""
    return SparseTextEmbedding(model_name=MODEL_NAME)


def embed_documents(model: SparseTextEmbedding, texts: list[str]) -> list[SparseVector]:
    """Embed chunks for indexing (TF-with-saturation, no IDF)."""
    embeddings = model.embed(texts)
    return [SparseVector(indices=e.indices.tolist(), values=e.values.tolist()) for e in embeddings]


def embed_query(model: SparseTextEmbedding, text: str) -> SparseVector:
    """Embed a single query for search (presence weights, IDF applied server-side)."""
    embedding = next(iter(model.query_embed(text)))
    return SparseVector(indices=embedding.indices.tolist(), values=embedding.values.tolist())
