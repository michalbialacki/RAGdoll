import pytest

from ragdoll.ingestion.chunker import chunk_text


def _words(n: int) -> str:
    return " ".join(f"w{i}" for i in range(n))


def test_chunk_size_matches_requested_word_count():
    chunks = chunk_text(_words(120), chunk_size=50, overlap=10)
    assert len(chunks[0].split()) == 50


def test_consecutive_chunks_share_overlap_words():
    chunks = chunk_text(_words(120), chunk_size=50, overlap=10)
    first_tail = chunks[0].split()[-10:]
    second_head = chunks[1].split()[:10]
    assert first_tail == second_head


def test_last_chunk_not_fully_contained_in_previous():
    # A tail fully covered by the previous chunk's overlap would be pure
    # redundancy — chunk_text stops once a chunk reaches the end of the text.
    chunks = chunk_text(_words(55), chunk_size=50, overlap=10)
    assert chunks[-1] != chunks[-2]
    assert len(chunks[-1].split()) <= 50


def test_overlap_not_smaller_than_chunk_size_raises():
    with pytest.raises(ValueError):
        chunk_text(_words(20), chunk_size=10, overlap=10)


def test_empty_text_raises():
    with pytest.raises(ValueError):
        chunk_text("", chunk_size=10, overlap=2)
