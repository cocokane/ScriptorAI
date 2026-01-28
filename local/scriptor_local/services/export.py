"""PDF export and BibTeX services."""
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import httpx
import re
import logging

logger = logging.getLogger(__name__)


async def export_flattened_pdf(
    pdf_path: Path,
    annotations: List[Dict[str, Any]],
    output_path: Path
) -> Path:
    """
    Export PDF with annotations burned in (flattened).

    Args:
        pdf_path: Source PDF path
        annotations: List of annotations to overlay
        output_path: Where to save the exported PDF

    Returns:
        Path to the exported PDF
    """
    doc = fitz.open(str(pdf_path))

    for annotation in annotations:
        page_num = annotation["page"]
        if page_num >= len(doc):
            continue

        page = doc[page_num]
        geom = annotation["geometry"]
        ann_type = annotation["type"]

        # Convert geometry to fitz.Rect
        rect = fitz.Rect(
            geom["x"],
            geom["y"],
            geom["x"] + geom.get("width", 0),
            geom["y"] + geom.get("height", 0)
        )

        color = _parse_color(annotation.get("color", "#FFFF00"))
        opacity = annotation.get("opacity", 0.5)

        if ann_type == "highlight":
            # Add highlight annotation
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=color)
            annot.set_opacity(opacity)
            annot.update()

        elif ann_type == "rectangle":
            # Draw rectangle shape
            shape = page.new_shape()
            shape.draw_rect(rect)
            stroke_color = color
            fill_color = None
            if annotation.get("fill"):
                fill_color = _parse_color(annotation.get("fill"))
            shape.finish(color=stroke_color, fill=fill_color, width=2)
            shape.commit()

        elif ann_type == "ellipse":
            # Draw ellipse shape
            shape = page.new_shape()
            shape.draw_oval(rect)
            shape.finish(color=color, width=2)
            shape.commit()

        elif ann_type == "text":
            # Insert text annotation
            text = annotation.get("text_content", "")
            if text:
                page.insert_text(
                    (geom["x"], geom["y"] + 12),
                    text,
                    fontsize=12,
                    color=color
                )

        elif ann_type == "comment":
            # Add sticky note
            annot = page.add_text_annot(
                (geom["x"], geom["y"]),
                annotation.get("text_content", "")
            )
            annot.set_colors(stroke=color)
            annot.update()

        elif ann_type == "ink":
            # Draw ink strokes
            points = geom.get("points", [])
            if points:
                shape = page.new_shape()
                for i, point in enumerate(points):
                    if i == 0:
                        shape.draw_line(
                            fitz.Point(point["x"], point["y"]),
                            fitz.Point(point["x"], point["y"])
                        )
                    else:
                        prev = points[i - 1]
                        shape.draw_line(
                            fitz.Point(prev["x"], prev["y"]),
                            fitz.Point(point["x"], point["y"])
                        )
                shape.finish(color=color, width=2)
                shape.commit()

        elif ann_type == "image":
            # Insert image overlay
            image_data = annotation.get("image_data")
            if image_data:
                page.insert_image(rect, stream=image_data)

    # Save flattened PDF
    doc.save(str(output_path), garbage=4, deflate=True)
    doc.close()

    return output_path


def _parse_color(color_str: str) -> tuple:
    """Parse color string to RGB tuple (0-1 range)."""
    if color_str.startswith("#"):
        hex_color = color_str[1:]
        if len(hex_color) == 3:
            hex_color = ''.join([c * 2 for c in hex_color])
        r = int(hex_color[0:2], 16) / 255
        g = int(hex_color[2:4], 16) / 255
        b = int(hex_color[4:6], 16) / 255
        return (r, g, b)
    return (1, 1, 0)  # Default yellow


async def fetch_bibtex_from_doi(doi: str) -> Optional[str]:
    """
    Fetch BibTeX citation from DOI using content negotiation.

    Uses doi.org content negotiation which is the official, reliable method.
    """
    # Clean DOI
    doi = doi.strip()
    if doi.startswith("https://doi.org/"):
        doi = doi[16:]
    elif doi.startswith("http://doi.org/"):
        doi = doi[15:]
    elif doi.startswith("doi:"):
        doi = doi[4:]

    url = f"https://doi.org/{doi}"

    headers = {
        "Accept": "application/x-bibtex"
    }

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=headers, timeout=15.0)
            if response.status_code == 200:
                return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to fetch BibTeX for DOI {doi}: {e}")

    # Fallback to Crossref API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.crossref.org/works/{doi}/transform/application/x-bibtex",
                timeout=15.0
            )
            if response.status_code == 200:
                return response.text.strip()
    except Exception as e:
        logger.error(f"Crossref fallback failed for DOI {doi}: {e}")

    return None


def parse_citation_to_bibtex(citation_text: str) -> str:
    """
    Best-effort parsing of a citation string to BibTeX format.

    This is a heuristic parser for manually pasted citations.
    """
    # Try to extract components
    # Common patterns: Author (Year). Title. Journal, Volume(Issue), Pages.

    # Extract year
    year_match = re.search(r'\((\d{4})\)', citation_text)
    year = year_match.group(1) if year_match else "YEAR"

    # Extract authors (text before year)
    if year_match:
        authors_text = citation_text[:year_match.start()].strip().rstrip(',')
    else:
        authors_text = "Unknown Author"

    # Extract title (often in quotes or after year)
    title_match = re.search(r'[""]([^""]+)[""]', citation_text)
    if title_match:
        title = title_match.group(1)
    else:
        # Try text between year and period
        after_year = citation_text[year_match.end():] if year_match else citation_text
        title_end = after_year.find('.')
        title = after_year[1:title_end].strip() if title_end > 0 else "Untitled"

    # Generate citation key
    first_author = authors_text.split(',')[0].split()[-1] if authors_text else "unknown"
    cite_key = f"{first_author.lower()}{year}"

    # Build BibTeX
    bibtex = f"""@article{{{cite_key},
  author = {{{authors_text}}},
  title = {{{title}}},
  year = {{{year}}},
  note = {{Parsed from citation text}}
}}"""

    return bibtex


def generate_doi_link(doi: str) -> str:
    """Generate a clickable DOI URL."""
    doi = doi.strip()
    if doi.startswith("https://doi.org/"):
        return doi
    elif doi.startswith("http://doi.org/"):
        return "https" + doi[4:]
    elif doi.startswith("doi:"):
        return f"https://doi.org/{doi[4:]}"
    else:
        return f"https://doi.org/{doi}"
