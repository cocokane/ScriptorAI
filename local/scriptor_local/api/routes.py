"""API routes for Scriptor Local."""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.responses import FileResponse, Response
from typing import Optional, List
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import uuid
import httpx
import base64

from ..config import config
from ..models.database import Database
from ..services import (
    extract_text_from_pdf,
    extract_doi_from_pdf,
    get_pdf_metadata,
    extract_region_image,
    EmbeddingService,
    BatchProcessor,
    enqueue_paper_jobs,
    LatexifyService,
    export_flattened_pdf,
    fetch_bibtex_from_doi,
    parse_citation_to_bibtex,
    generate_doi_link
)

# Initialize services
db = Database(config.db_path)
embedding_service = EmbeddingService(config.embedding_model, config.models_dir)
batch_processor = BatchProcessor(db, embedding_service, config.pdfs_dir)
latexify_service = LatexifyService(config.gemini_api_key, config.models_dir)

router = APIRouter()


# Auth dependency
async def verify_token(authorization: str = Header(None)):
    """Verify the auth token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    # Handle "Bearer <token>" format
    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]

    if token != config.auth_token:
        raise HTTPException(status_code=401, detail="Invalid token")

    return token


# ============ Health & Auth ============

@router.get("/health")
async def health_check():
    """Health check endpoint (no auth required)."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "storage_dir": str(config.storage_dir)
    }


@router.get("/status")
async def get_status(token: str = Depends(verify_token)):
    """Get detailed status of Scriptor Local."""
    batch_status = await db.get_batch_status()
    papers = await db.list_papers()

    return {
        "connected": True,
        "storage_dir": str(config.storage_dir),
        "papers_count": len(papers),
        "batch_status": batch_status,
        "latexify_status": latexify_service.get_status()
    }


class PairRequest(BaseModel):
    """Request to verify pairing."""
    pass


@router.post("/pair")
async def pair(token: str = Depends(verify_token)):
    """Verify pairing (token already validated by dependency)."""
    return {"paired": True, "message": "Successfully paired"}


# ============ Papers ============

class AddPaperRequest(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    collection: Optional[str] = "default"


@router.post("/papers/add")
async def add_paper(
    request: AddPaperRequest = None,
    file: UploadFile = File(None),
    url: str = Form(None),
    title: str = Form(None),
    collection: str = Form("default"),
    token: str = Depends(verify_token)
):
    """Add a paper to the library."""
    paper_id = str(uuid.uuid4())

    # Get PDF content
    pdf_bytes = None

    if file:
        pdf_bytes = await file.read()
        source_url = None
        filename = file.filename or f"{paper_id}.pdf"
    elif url or (request and request.url):
        source_url = url or request.url
        # Download PDF
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(source_url, follow_redirects=True, timeout=60.0)
                response.raise_for_status()
                pdf_bytes = response.content
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to download PDF: {str(e)}")
        filename = source_url.split("/")[-1].split("?")[0] or f"{paper_id}.pdf"
        if not filename.endswith(".pdf"):
            filename += ".pdf"
    else:
        raise HTTPException(status_code=400, detail="Must provide either file or URL")

    # Save PDF
    pdf_path = config.pdfs_dir / f"{paper_id}_{filename}"
    pdf_path.write_bytes(pdf_bytes)

    # Extract metadata
    try:
        metadata = get_pdf_metadata(pdf_path)
    except Exception:
        metadata = {"page_count": 0}

    # Create paper record
    paper_title = title or (request and request.title) or metadata.get("title") or filename
    paper_collection = collection or (request and request.collection) or "default"

    paper = {
        "id": paper_id,
        "title": paper_title,
        "authors": metadata.get("author"),
        "source_url": source_url if url or (request and request.url) else None,
        "local_pdf_path": str(pdf_path),
        "collection": paper_collection,
        "metadata": metadata
    }

    await db.add_paper(paper)

    # Enqueue processing jobs
    jobs = await enqueue_paper_jobs(db, paper_id)

    return {
        "id": paper_id,
        "title": paper_title,
        "status": "pending",
        "jobs_queued": len(jobs)
    }


@router.get("/papers/list")
async def list_papers(
    collection: Optional[str] = None,
    token: str = Depends(verify_token)
):
    """List all papers."""
    papers = await db.list_papers(collection)
    return {"papers": papers}


@router.get("/papers/{paper_id}")
async def get_paper(paper_id: str, token: str = Depends(verify_token)):
    """Get a specific paper."""
    paper = await db.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.delete("/papers/{paper_id}")
async def delete_paper(paper_id: str, token: str = Depends(verify_token)):
    """Delete a paper."""
    paper = await db.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # Delete PDF file
    pdf_path = Path(paper["local_pdf_path"])
    if pdf_path.exists():
        pdf_path.unlink()

    await db.delete_paper(paper_id)
    return {"deleted": True}


@router.get("/papers/{paper_id}/pdf")
async def get_paper_pdf(paper_id: str, token: str = Depends(verify_token)):
    """Get the PDF file for a paper."""
    paper = await db.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    pdf_path = Path(paper["local_pdf_path"])
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name
    )


# ============ Annotations ============

class AnnotationRequest(BaseModel):
    id: str
    paper_id: str
    page: int
    type: str
    geometry: dict
    color: Optional[str] = None
    opacity: Optional[float] = 1.0
    text_content: Optional[str] = None


@router.post("/annotations/save")
async def save_annotation(
    annotation: AnnotationRequest,
    token: str = Depends(verify_token)
):
    """Save or update an annotation."""
    await db.save_annotation(annotation.model_dump())
    return {"saved": True, "id": annotation.id}


@router.get("/annotations/{paper_id}")
async def get_annotations(paper_id: str, token: str = Depends(verify_token)):
    """Get all annotations for a paper."""
    annotations = await db.get_annotations(paper_id)
    return {"annotations": annotations}


@router.delete("/annotations/{annotation_id}")
async def delete_annotation(annotation_id: str, token: str = Depends(verify_token)):
    """Delete an annotation."""
    await db.delete_annotation(annotation_id)
    return {"deleted": True}


# ============ Semantic Search ============

class SearchRequest(BaseModel):
    paper_id: str
    query: str
    top_k: int = 50


@router.post("/search/semantic")
async def semantic_search(request: SearchRequest, token: str = Depends(verify_token)):
    """Perform semantic search on a paper."""
    paper = await db.get_paper(request.paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if not paper.get("embeddings_ready"):
        raise HTTPException(
            status_code=400,
            detail="Paper not ready for semantic search. Run batch processing first."
        )

    # Get chunks with embeddings
    chunks_with_embeddings = await db.get_embeddings(request.paper_id)

    if not chunks_with_embeddings:
        raise HTTPException(status_code=400, detail="No embeddings found for this paper")

    # Search
    results = embedding_service.search(
        request.query,
        chunks_with_embeddings,
        request.top_k
    )

    # Normalize scores for heatmap
    results = embedding_service.normalize_scores(results)

    return {
        "query": request.query,
        "results": results
    }


# ============ Batch Processing ============

@router.post("/batch/run")
async def run_batch(token: str = Depends(verify_token)):
    """Run all pending batch jobs."""
    result = await batch_processor.run_batch()
    return result


@router.get("/batch/status")
async def get_batch_status(token: str = Depends(verify_token)):
    """Get batch queue status."""
    status = await db.get_batch_status()
    return status


class EnqueueJobRequest(BaseModel):
    paper_id: str
    type: str
    priority: int = 0


@router.post("/jobs/enqueue")
async def enqueue_job(request: EnqueueJobRequest, token: str = Depends(verify_token)):
    """Manually enqueue a job."""
    job = {
        "id": str(uuid.uuid4()),
        "paper_id": request.paper_id,
        "type": request.type,
        "priority": request.priority
    }
    await db.add_job(job)
    return {"job_id": job["id"]}


# ============ LaTeXify ============

class LatexifyRequest(BaseModel):
    paper_id: str
    page: int
    bbox: dict


@router.post("/latexify")
async def latexify(request: LatexifyRequest, token: str = Depends(verify_token)):
    """Convert a region to LaTeX."""
    paper = await db.get_paper(request.paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    pdf_path = Path(paper["local_pdf_path"])
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")

    # Extract region as image
    try:
        image_bytes = extract_region_image(pdf_path, request.page, request.bbox)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract region: {str(e)}")

    # Convert to LaTeX
    result = await latexify_service.convert_to_latex(image_bytes)

    return result


@router.post("/latexify/image")
async def latexify_image(
    image: UploadFile = File(...),
    token: str = Depends(verify_token)
):
    """Convert an uploaded image to LaTeX."""
    image_bytes = await image.read()
    result = await latexify_service.convert_to_latex(image_bytes)
    return result


@router.get("/latexify/status")
async def latexify_status(token: str = Depends(verify_token)):
    """Get LaTeXify service status."""
    return latexify_service.get_status()


# ============ Export & BibTeX ============

class ExportRequest(BaseModel):
    paper_id: str


@router.post("/export/pdf")
async def export_pdf(request: ExportRequest, token: str = Depends(verify_token)):
    """Export a paper as flattened PDF with annotations."""
    paper = await db.get_paper(request.paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    pdf_path = Path(paper["local_pdf_path"])
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")

    # Get annotations
    annotations = await db.get_annotations(request.paper_id)

    # Generate output path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{paper['title'][:50]}_{timestamp}_annotated.pdf"
    output_path = config.exports_dir / output_filename

    # Export
    try:
        await export_flattened_pdf(pdf_path, annotations, output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=output_filename
    )


@router.get("/bibtex/{paper_id}")
async def get_bibtex(paper_id: str, token: str = Depends(verify_token)):
    """Get BibTeX citation for a paper."""
    paper = await db.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    doi = paper.get("doi")

    if doi:
        bibtex = await fetch_bibtex_from_doi(doi)
        if bibtex:
            return {
                "bibtex": bibtex,
                "doi": doi,
                "doi_link": generate_doi_link(doi),
                "source": "doi"
            }

    return {
        "bibtex": None,
        "doi": doi,
        "doi_link": generate_doi_link(doi) if doi else None,
        "message": "No DOI found. Use manual citation input.",
        "source": None
    }


class ParseCitationRequest(BaseModel):
    citation: str


@router.post("/bibtex/parse")
async def parse_citation(request: ParseCitationRequest, token: str = Depends(verify_token)):
    """Parse a citation string to BibTeX."""
    bibtex = parse_citation_to_bibtex(request.citation)
    return {"bibtex": bibtex, "source": "parsed"}


# ============ Config ============

class UpdateConfigRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    storage_dir: Optional[str] = None


@router.post("/config/update")
async def update_config(request: UpdateConfigRequest, token: str = Depends(verify_token)):
    """Update configuration."""
    if request.gemini_api_key is not None:
        config.gemini_api_key = request.gemini_api_key
        latexify_service.gemini_api_key = request.gemini_api_key

    if request.storage_dir:
        config.set_storage_dir(request.storage_dir)

    config.save()
    return {"updated": True}


@router.get("/config/token")
async def get_token():
    """Get the auth token (for initial pairing display only)."""
    # This endpoint is intentionally open for the local UI to display the token
    return {"token": config.auth_token}


@router.post("/config/regenerate-token")
async def regenerate_token(token: str = Depends(verify_token)):
    """Regenerate the auth token."""
    new_token = config.regenerate_token()
    return {"token": new_token, "message": "Token regenerated. Update extension pairing."}


# Startup/shutdown
async def startup():
    """Initialize database on startup."""
    await db.connect()


async def shutdown():
    """Close database on shutdown."""
    await db.close()
