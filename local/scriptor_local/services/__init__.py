"""Services for Scriptor Local."""
from .text_extraction import (
    extract_text_from_pdf,
    extract_doi_from_pdf,
    get_pdf_metadata,
    render_page_to_image,
    extract_region_image
)
from .embeddings import EmbeddingService, generate_micro_summary
from .batch_processor import BatchProcessor, enqueue_paper_jobs
from .latexify import LatexifyService
from .export import (
    export_flattened_pdf,
    fetch_bibtex_from_doi,
    parse_citation_to_bibtex,
    generate_doi_link
)

__all__ = [
    "extract_text_from_pdf",
    "extract_doi_from_pdf",
    "get_pdf_metadata",
    "render_page_to_image",
    "extract_region_image",
    "EmbeddingService",
    "generate_micro_summary",
    "BatchProcessor",
    "enqueue_paper_jobs",
    "LatexifyService",
    "export_flattened_pdf",
    "fetch_bibtex_from_doi",
    "parse_citation_to_bibtex",
    "generate_doi_link"
]
