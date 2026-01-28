"""Text extraction service using PyMuPDF."""
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Any, Tuple
import uuid
import re


def extract_text_from_pdf(pdf_path: Path) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Extract text and bounding boxes from PDF.

    Returns:
        Tuple of (chunks list, has_text boolean)
        Each chunk has: id, page, bbox, text, chunk_index
    """
    doc = fitz.open(str(pdf_path))
    chunks = []
    has_text = False
    chunk_index = 0

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Get text blocks with positioning
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

        for block in blocks:
            if block.get("type") == 0:  # Text block
                # Extract text from lines
                text_parts = []
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text_parts.append(span.get("text", ""))

                text = " ".join(text_parts).strip()

                if text and len(text) > 10:  # Minimum chunk size
                    has_text = True
                    bbox = block.get("bbox", [0, 0, 0, 0])

                    chunks.append({
                        "id": str(uuid.uuid4()),
                        "page": page_num,
                        "bbox": {
                            "x": bbox[0],
                            "y": bbox[1],
                            "width": bbox[2] - bbox[0],
                            "height": bbox[3] - bbox[1]
                        },
                        "text": text,
                        "chunk_index": chunk_index
                    })
                    chunk_index += 1

    doc.close()
    return chunks, has_text


def extract_doi_from_pdf(pdf_path: Path) -> str | None:
    """Extract DOI from the first few pages of a PDF."""
    doc = fitz.open(str(pdf_path))
    doi_pattern = re.compile(r'10\.\d{4,}/[^\s]+')

    # Check first 3 pages
    for page_num in range(min(3, len(doc))):
        page = doc[page_num]
        text = page.get_text()

        match = doi_pattern.search(text)
        if match:
            doi = match.group(0)
            # Clean up common trailing characters
            doi = re.sub(r'[.,;)\]]+$', '', doi)
            doc.close()
            return doi

    doc.close()
    return None


def get_pdf_metadata(pdf_path: Path) -> Dict[str, Any]:
    """Extract basic metadata from PDF."""
    doc = fitz.open(str(pdf_path))

    metadata = {
        "page_count": len(doc),
        "title": doc.metadata.get("title", ""),
        "author": doc.metadata.get("author", ""),
        "subject": doc.metadata.get("subject", ""),
        "creator": doc.metadata.get("creator", ""),
        "producer": doc.metadata.get("producer", ""),
    }

    # Try to extract title from first page if not in metadata
    if not metadata["title"] and len(doc) > 0:
        first_page = doc[0]
        blocks = first_page.get_text("dict")["blocks"]

        # Find largest text as title candidate
        max_size = 0
        title_candidate = ""
        for block in blocks[:5]:  # Check first few blocks
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span.get("size", 0) > max_size:
                            max_size = span.get("size", 0)
                            title_candidate = span.get("text", "").strip()

        if title_candidate and len(title_candidate) > 5:
            metadata["title"] = title_candidate

    doc.close()
    return metadata


def render_page_to_image(pdf_path: Path, page_num: int, scale: float = 2.0) -> bytes:
    """Render a PDF page to PNG bytes."""
    doc = fitz.open(str(pdf_path))
    page = doc[page_num]

    # Render at higher resolution
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat)
    png_bytes = pix.tobytes("png")

    doc.close()
    return png_bytes


def extract_region_image(
    pdf_path: Path,
    page_num: int,
    bbox: Dict[str, float],
    scale: float = 3.0
) -> bytes:
    """Extract a region from a PDF page as PNG."""
    doc = fitz.open(str(pdf_path))
    page = doc[page_num]

    # Define clip rectangle
    rect = fitz.Rect(
        bbox["x"],
        bbox["y"],
        bbox["x"] + bbox["width"],
        bbox["y"] + bbox["height"]
    )

    # Render clipped region
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, clip=rect)
    png_bytes = pix.tobytes("png")

    doc.close()
    return png_bytes
