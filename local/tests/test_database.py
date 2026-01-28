"""Tests for database operations."""
import pytest
from datetime import datetime
import uuid


@pytest.mark.asyncio
async def test_add_paper(test_db):
    """Test adding a paper to the database."""
    paper = {
        "id": str(uuid.uuid4()),
        "title": "Test Paper",
        "authors": "John Doe",
        "year": 2024,
        "doi": "10.1234/test",
        "source_url": "https://example.com/paper.pdf",
        "local_pdf_path": "/tmp/test.pdf",
        "collection": "test"
    }

    paper_id = await test_db.add_paper(paper)
    assert paper_id == paper["id"]

    # Retrieve and verify
    retrieved = await test_db.get_paper(paper_id)
    assert retrieved is not None
    assert retrieved["title"] == "Test Paper"
    assert retrieved["authors"] == "John Doe"
    assert retrieved["status"] == "pending"


@pytest.mark.asyncio
async def test_list_papers(test_db):
    """Test listing papers."""
    # Add multiple papers
    for i in range(3):
        paper = {
            "id": str(uuid.uuid4()),
            "title": f"Paper {i}",
            "local_pdf_path": f"/tmp/paper{i}.pdf",
            "collection": "default" if i < 2 else "other"
        }
        await test_db.add_paper(paper)

    # List all papers
    papers = await test_db.list_papers()
    assert len(papers) == 3

    # List by collection
    default_papers = await test_db.list_papers(collection="default")
    assert len(default_papers) == 2


@pytest.mark.asyncio
async def test_update_paper(test_db):
    """Test updating paper fields."""
    paper = {
        "id": str(uuid.uuid4()),
        "title": "Original Title",
        "local_pdf_path": "/tmp/test.pdf"
    }
    paper_id = await test_db.add_paper(paper)

    # Update
    await test_db.update_paper(paper_id, {
        "title": "Updated Title",
        "embeddings_ready": 1,
        "status": "indexed"
    })

    # Verify
    updated = await test_db.get_paper(paper_id)
    assert updated["title"] == "Updated Title"
    assert updated["embeddings_ready"] == 1
    assert updated["status"] == "indexed"


@pytest.mark.asyncio
async def test_delete_paper(test_db):
    """Test deleting a paper."""
    paper = {
        "id": str(uuid.uuid4()),
        "title": "To Delete",
        "local_pdf_path": "/tmp/delete.pdf"
    }
    paper_id = await test_db.add_paper(paper)

    # Verify exists
    assert await test_db.get_paper(paper_id) is not None

    # Delete
    await test_db.delete_paper(paper_id)

    # Verify deleted
    assert await test_db.get_paper(paper_id) is None


@pytest.mark.asyncio
async def test_annotations(test_db):
    """Test annotation CRUD operations."""
    # First create a paper
    paper = {
        "id": str(uuid.uuid4()),
        "title": "Test Paper",
        "local_pdf_path": "/tmp/test.pdf"
    }
    paper_id = await test_db.add_paper(paper)

    # Create annotation
    annotation = {
        "id": str(uuid.uuid4()),
        "paper_id": paper_id,
        "page": 0,
        "type": "highlight",
        "geometry": {"x": 100, "y": 200, "width": 50, "height": 20},
        "color": "#FFEB3B",
        "opacity": 0.5
    }
    await test_db.save_annotation(annotation)

    # Retrieve
    annotations = await test_db.get_annotations(paper_id)
    assert len(annotations) == 1
    assert annotations[0]["type"] == "highlight"
    assert annotations[0]["geometry"]["x"] == 100

    # Update annotation
    annotation["color"] = "#4CAF50"
    await test_db.save_annotation(annotation)

    annotations = await test_db.get_annotations(paper_id)
    assert annotations[0]["color"] == "#4CAF50"

    # Delete annotation
    await test_db.delete_annotation(annotation["id"])
    annotations = await test_db.get_annotations(paper_id)
    assert len(annotations) == 0


@pytest.mark.asyncio
async def test_chunks(test_db):
    """Test text chunk operations."""
    paper = {
        "id": str(uuid.uuid4()),
        "title": "Test Paper",
        "local_pdf_path": "/tmp/test.pdf"
    }
    paper_id = await test_db.add_paper(paper)

    # Add chunks
    chunks = [
        {
            "id": str(uuid.uuid4()),
            "paper_id": paper_id,
            "page": 0,
            "bbox": {"x": 0, "y": 0, "width": 100, "height": 20},
            "text": "First chunk of text",
            "chunk_index": 0
        },
        {
            "id": str(uuid.uuid4()),
            "paper_id": paper_id,
            "page": 0,
            "bbox": {"x": 0, "y": 25, "width": 100, "height": 20},
            "text": "Second chunk of text",
            "chunk_index": 1
        }
    ]
    await test_db.add_chunks(chunks)

    # Retrieve
    retrieved = await test_db.get_chunks(paper_id)
    assert len(retrieved) == 2
    assert retrieved[0]["text"] == "First chunk of text"

    # Delete chunks
    await test_db.delete_chunks(paper_id)
    retrieved = await test_db.get_chunks(paper_id)
    assert len(retrieved) == 0


@pytest.mark.asyncio
async def test_jobs(test_db):
    """Test job queue operations."""
    paper = {
        "id": str(uuid.uuid4()),
        "title": "Test Paper",
        "local_pdf_path": "/tmp/test.pdf"
    }
    paper_id = await test_db.add_paper(paper)

    # Add jobs
    job1 = {
        "id": str(uuid.uuid4()),
        "paper_id": paper_id,
        "type": "EXTRACT_TEXT",
        "priority": 10
    }
    job2 = {
        "id": str(uuid.uuid4()),
        "paper_id": paper_id,
        "type": "EMBED",
        "priority": 1
    }
    await test_db.add_job(job1)
    await test_db.add_job(job2)

    # Get pending jobs (should be ordered by priority)
    pending = await test_db.get_pending_jobs()
    assert len(pending) == 2
    assert pending[0]["type"] == "EXTRACT_TEXT"  # Higher priority

    # Update job status
    await test_db.update_job(job1["id"], {
        "status": "completed",
        "finished_at": datetime.utcnow().isoformat()
    })

    # Check batch status
    status = await test_db.get_batch_status()
    assert status["pending"] == 1
    assert status["completed"] == 1
