from ragdoll.ingestion.sparse_embedding import embed_documents, embed_query

# Real model (see conftest.sparse_model) — BM25 is local/deterministic/no
# network after first download, so we exercise the real thing, not a mock.
# What we're proving: exact-token matching mechanics (shared vocabulary index
# between a document and a query containing the same word) — NOT semantic
# understanding, which BM25 does not do.


def test_embed_documents_returns_one_vector_per_text(sparse_model):
    # TODO:
    # 1. call embed_documents(sparse_model, ["apple banana", "banana cherry"])
    # 2. assert len(result) == 2
    # 3. assert each result has non-empty .indices and .values, and that
    #    len(indices) == len(values) for each
    raise NotImplementedError


def test_shared_token_produces_shared_index(sparse_model):
    # TODO: this is the core exact-match assertion.
    # 1. embed a document containing a distinctive word, e.g. "apple banana"
    # 2. embed_query for a query containing the SAME distinctive word, e.g. "apple"
    # 3. assert there's at least one index present in BOTH the document's
    #    .indices and the query's .indices (BM25 hashes tokens to indices —
    #    same token -> same index, regardless of doc vs query)
    raise NotImplementedError


def test_document_without_shared_token_has_no_overlap(sparse_model):
    # TODO: the contrast case.
    # 1. embed a document with unrelated vocabulary, e.g. "xylophone zephyr"
    # 2. embed_query("apple")
    # 3. assert there is NO overlap between the two .indices sets — proving
    #    BM25 does NOT do concept expansion (no shared token -> zero match,
    #    even if the concepts were "related")
    raise NotImplementedError
