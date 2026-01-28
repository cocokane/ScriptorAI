"""Batch processing service for AI jobs."""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import uuid
import logging

from ..models.database import Database
from .text_extraction import extract_text_from_pdf, extract_doi_from_pdf, get_pdf_metadata
from .embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Handles batch processing of AI jobs."""

    def __init__(
        self,
        db: Database,
        embedding_service: EmbeddingService,
        pdfs_dir: Path
    ):
        self.db = db
        self.embedding_service = embedding_service
        self.pdfs_dir = pdfs_dir
        self._running = False
        self._current_job: Optional[Dict[str, Any]] = None
        self._progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates."""
        self._progress_callback = callback

    def _notify_progress(self, job_id: str, status: str, progress: float = 0, message: str = ""):
        """Notify progress callback if set."""
        if self._progress_callback:
            self._progress_callback({
                "job_id": job_id,
                "status": status,
                "progress": progress,
                "message": message
            })

    async def run_batch(self) -> Dict[str, Any]:
        """
        Process all pending jobs in the queue.

        Returns status summary.
        """
        if self._running:
            return {"error": "Batch already running", "status": "busy"}

        self._running = True
        processed = 0
        failed = 0
        errors = []

        try:
            while True:
                # Get next pending job
                pending_jobs = await self.db.get_pending_jobs()
                if not pending_jobs:
                    break

                job = pending_jobs[0]
                self._current_job = job

                try:
                    await self._process_job(job)
                    processed += 1
                except Exception as e:
                    logger.error(f"Job {job['id']} failed: {e}")
                    await self.db.update_job(job["id"], {
                        "status": "failed",
                        "error": str(e),
                        "finished_at": datetime.utcnow().isoformat()
                    })
                    failed += 1
                    errors.append({"job_id": job["id"], "error": str(e)})

                self._current_job = None

        finally:
            self._running = False

        return {
            "status": "completed",
            "processed": processed,
            "failed": failed,
            "errors": errors if errors else None
        }

    async def _process_job(self, job: Dict[str, Any]):
        """Process a single job."""
        job_id = job["id"]
        job_type = job["type"]
        paper_id = job["paper_id"]

        logger.info(f"Processing job {job_id}: {job_type} for paper {paper_id}")

        # Mark as running
        await self.db.update_job(job_id, {
            "status": "running",
            "started_at": datetime.utcnow().isoformat()
        })

        self._notify_progress(job_id, "running", 0, f"Starting {job_type}")

        # Get paper info
        paper = await self.db.get_paper(paper_id)
        if not paper:
            raise ValueError(f"Paper {paper_id} not found")

        pdf_path = Path(paper["local_pdf_path"])
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Route to appropriate handler
        if job_type == "EXTRACT_TEXT":
            await self._extract_text(paper, pdf_path)
        elif job_type == "EXTRACT_DOI":
            await self._extract_doi(paper, pdf_path)
        elif job_type == "EMBED":
            await self._compute_embeddings(paper)
        else:
            raise ValueError(f"Unknown job type: {job_type}")

        # Mark as completed
        await self.db.update_job(job_id, {
            "status": "completed",
            "finished_at": datetime.utcnow().isoformat()
        })

        self._notify_progress(job_id, "completed", 1.0, f"Completed {job_type}")

    async def _extract_text(self, paper: Dict[str, Any], pdf_path: Path):
        """Extract text chunks from PDF."""
        paper_id = paper["id"]

        self._notify_progress("", "running", 0.1, "Extracting text from PDF...")

        # Extract text and chunks
        chunks, has_text = extract_text_from_pdf(pdf_path)

        if not has_text:
            logger.warning(f"No text found in PDF {paper_id}, may need OCR")
            # For V1, we just note this - OCR would be a separate service
            await self.db.update_paper(paper_id, {
                "status": "needs_ocr",
                "metadata": {"has_text": False}
            })
            return

        # Add paper_id to chunks
        for chunk in chunks:
            chunk["paper_id"] = paper_id

        self._notify_progress("", "running", 0.5, f"Saving {len(chunks)} text chunks...")

        # Delete existing chunks and save new ones
        await self.db.delete_chunks(paper_id)
        await self.db.add_chunks(chunks)

        # Update paper status
        await self.db.update_paper(paper_id, {
            "indexed_at": datetime.utcnow().isoformat(),
            "status": "indexed"
        })

        self._notify_progress("", "running", 1.0, f"Extracted {len(chunks)} chunks")

    async def _extract_doi(self, paper: Dict[str, Any], pdf_path: Path):
        """Extract DOI from PDF."""
        paper_id = paper["id"]

        self._notify_progress("", "running", 0.5, "Extracting DOI...")

        doi = extract_doi_from_pdf(pdf_path)

        if doi:
            await self.db.update_paper(paper_id, {"doi": doi})
            self._notify_progress("", "running", 1.0, f"Found DOI: {doi}")
        else:
            self._notify_progress("", "running", 1.0, "No DOI found")

    async def _compute_embeddings(self, paper: Dict[str, Any]):
        """Compute embeddings for all chunks."""
        paper_id = paper["id"]

        # Get chunks
        chunks = await self.db.get_chunks(paper_id)
        if not chunks:
            raise ValueError(f"No chunks found for paper {paper_id}. Run text extraction first.")

        total = len(chunks)
        self._notify_progress("", "running", 0.1, f"Computing embeddings for {total} chunks...")

        # Batch embed for efficiency
        texts = [c["text"] for c in chunks]

        # Process in batches to show progress
        batch_size = 32
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_chunks = chunks[i:i + batch_size]

            embeddings = self.embedding_service.embed_texts(batch_texts)

            for chunk, embedding in zip(batch_chunks, embeddings):
                vector_bytes = self.embedding_service.vector_to_bytes(embedding)
                await self.db.add_embedding(chunk["id"], vector_bytes)

            progress = min(0.9, 0.1 + 0.8 * (i + len(batch_texts)) / total)
            self._notify_progress("", "running", progress, f"Embedded {min(i + batch_size, total)}/{total}")

        # Mark paper as embeddings ready
        await self.db.update_paper(paper_id, {"embeddings_ready": 1})

        self._notify_progress("", "running", 1.0, f"Computed {total} embeddings")


async def enqueue_paper_jobs(db: Database, paper_id: str):
    """Enqueue standard processing jobs for a new paper."""
    jobs = [
        {"id": str(uuid.uuid4()), "paper_id": paper_id, "type": "EXTRACT_TEXT", "priority": 10},
        {"id": str(uuid.uuid4()), "paper_id": paper_id, "type": "EXTRACT_DOI", "priority": 5},
        {"id": str(uuid.uuid4()), "paper_id": paper_id, "type": "EMBED", "priority": 1},
    ]

    for job in jobs:
        await db.add_job(job)

    return jobs
