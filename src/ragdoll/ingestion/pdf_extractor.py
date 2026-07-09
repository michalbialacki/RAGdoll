"""Raw text extraction from PDF files."""

from pathlib import Path

from pypdf import PdfReader


def extract_text(pdf_path: Path) -> str:
    """Extract raw text from a PDF, concatenating all pages with a blank line between them."""
    reader = PdfReader(pdf_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)
