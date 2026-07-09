"""Fixed-size word-count chunking with overlap (PoC — see Phase 08 for semantic chunking)."""


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks of `chunk_size` words each.

    Consecutive chunks share `overlap` words at the boundary, so that
    information split across a chunk boundary is not entirely lost to
    either chunk.
    """
    if overlap >= chunk_size or text == "":
        raise ValueError(f"Overlap ({overlap}) must be smaller than chunk_size ({chunk_size})")

    words = text.split()
    chunks = []
    start = 0
    end = 0
    while start < len(words) and end < len(words):
        end = start + chunk_size if start + chunk_size <= len(words) else len(words)
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks