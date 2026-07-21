from ragdoll.ingestion.sparse_embedding import embed_documents, embed_query

# Real model (see conftest.sparse_model) — BM25 is local/deterministic/no
# network after first download, so we exercise the real thing, not a mock.
# What we're proving: exact-token matching mechanics (shared vocabulary index
# between a document and a query containing the same word) — NOT semantic
# understanding, which BM25 does not do.


def test_embed_documents_returns_one_vector_per_text(sparse_model):
    result = embed_documents(sparse_model, ["apple banana", "banana cherry"])

    assert len(result) == 2
    for vector in result:
        assert len(vector.indices) > 0
        assert len(vector.values) > 0
        assert len(vector.indices) == len(vector.values)


def test_shared_token_produces_shared_index(sparse_model):
    [doc_vector] = embed_documents(sparse_model, ["apple banana"])
    query_vector = embed_query(sparse_model, "apple")

    assert set(doc_vector.indices) & set(query_vector.indices)


def test_document_without_shared_token_has_no_overlap(sparse_model):
    [doc_vector] = embed_documents(sparse_model, ["xylophone zephyr"])
    query_vector = embed_query(sparse_model, "apple")

    assert not (set(doc_vector.indices) & set(query_vector.indices))
