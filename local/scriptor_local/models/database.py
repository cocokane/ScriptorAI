"""SQLite database models and schema for Scriptor Local."""
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

SCHEMA_VERSION = 1

SCHEMA_SQL = """
-- Papers table
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT,
    year INTEGER,
    doi TEXT,
    source_url TEXT,
    local_pdf_path TEXT NOT NULL,
    added_at TEXT NOT NULL,
    indexed_at TEXT,
    embeddings_ready INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    collection TEXT DEFAULT 'default',
    metadata TEXT
);

-- Annotations table
CREATE TABLE IF NOT EXISTS annotations (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    page INTEGER NOT NULL,
    type TEXT NOT NULL,
    geometry TEXT NOT NULL,
    color TEXT,
    opacity REAL DEFAULT 1.0,
    text_content TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);

-- Text chunks table
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    page INTEGER NOT NULL,
    bbox TEXT NOT NULL,
    text TEXT NOT NULL,
    chunk_index INTEGER,
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);

-- Embeddings table
CREATE TABLE IF NOT EXISTS embeddings (
    chunk_id TEXT PRIMARY KEY,
    vector BLOB NOT NULL,
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);

-- Jobs queue table
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    error TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    metadata TEXT,
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);

-- Schema version table
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status);
CREATE INDEX IF NOT EXISTS idx_papers_collection ON papers(collection);
CREATE INDEX IF NOT EXISTS idx_annotations_paper ON annotations(paper_id);
CREATE INDEX IF NOT EXISTS idx_chunks_paper ON chunks(paper_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_paper ON jobs(paper_id);
"""


class Database:
    """Async SQLite database manager."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Initialize database connection and schema."""
        self._connection = await aiosqlite.connect(str(self.db_path))
        self._connection.row_factory = aiosqlite.Row
        await self._connection.executescript(SCHEMA_SQL)

        # Check and set schema version
        async with self._connection.execute("SELECT version FROM schema_version LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if row is None:
                await self._connection.execute(
                    "INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
                )

        await self._connection.commit()

    async def close(self):
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._connection:
            raise RuntimeError("Database not connected")
        return self._connection

    # Paper operations
    async def add_paper(self, paper: Dict[str, Any]) -> str:
        """Add a new paper to the database."""
        now = datetime.utcnow().isoformat()
        await self.conn.execute(
            """INSERT INTO papers
               (id, title, authors, year, doi, source_url, local_pdf_path, added_at, status, collection, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                paper["id"],
                paper.get("title", "Untitled"),
                paper.get("authors"),
                paper.get("year"),
                paper.get("doi"),
                paper.get("source_url"),
                paper["local_pdf_path"],
                now,
                "pending",
                paper.get("collection", "default"),
                json.dumps(paper.get("metadata", {}))
            )
        )
        await self.conn.commit()
        return paper["id"]

    async def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get a paper by ID."""
        async with self.conn.execute(
            "SELECT * FROM papers WHERE id = ?", (paper_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
        return None

    async def list_papers(self, collection: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all papers, optionally filtered by collection."""
        if collection:
            query = "SELECT * FROM papers WHERE collection = ? ORDER BY added_at DESC"
            params = (collection,)
        else:
            query = "SELECT * FROM papers ORDER BY added_at DESC"
            params = ()

        async with self.conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_paper(self, paper_id: str, updates: Dict[str, Any]):
        """Update paper fields."""
        allowed_fields = [
            "title", "authors", "year", "doi", "indexed_at",
            "embeddings_ready", "status", "collection", "metadata"
        ]
        set_clauses = []
        values = []

        for field, value in updates.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = ?")
                if field == "metadata" and isinstance(value, dict):
                    value = json.dumps(value)
                values.append(value)

        if set_clauses:
            values.append(paper_id)
            query = f"UPDATE papers SET {', '.join(set_clauses)} WHERE id = ?"
            await self.conn.execute(query, tuple(values))
            await self.conn.commit()

    async def delete_paper(self, paper_id: str):
        """Delete a paper and all related data."""
        await self.conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
        await self.conn.commit()

    # Annotation operations
    async def save_annotation(self, annotation: Dict[str, Any]) -> str:
        """Save or update an annotation."""
        now = datetime.utcnow().isoformat()
        existing = await self.get_annotation(annotation["id"])

        if existing:
            await self.conn.execute(
                """UPDATE annotations SET
                   page = ?, type = ?, geometry = ?, color = ?,
                   opacity = ?, text_content = ?, updated_at = ?
                   WHERE id = ?""",
                (
                    annotation["page"],
                    annotation["type"],
                    json.dumps(annotation["geometry"]),
                    annotation.get("color"),
                    annotation.get("opacity", 1.0),
                    annotation.get("text_content"),
                    now,
                    annotation["id"]
                )
            )
        else:
            await self.conn.execute(
                """INSERT INTO annotations
                   (id, paper_id, page, type, geometry, color, opacity, text_content, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    annotation["id"],
                    annotation["paper_id"],
                    annotation["page"],
                    annotation["type"],
                    json.dumps(annotation["geometry"]),
                    annotation.get("color"),
                    annotation.get("opacity", 1.0),
                    annotation.get("text_content"),
                    now,
                    now
                )
            )

        await self.conn.commit()
        return annotation["id"]

    async def get_annotation(self, annotation_id: str) -> Optional[Dict[str, Any]]:
        """Get an annotation by ID."""
        async with self.conn.execute(
            "SELECT * FROM annotations WHERE id = ?", (annotation_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                result = dict(row)
                result["geometry"] = json.loads(result["geometry"])
                return result
        return None

    async def get_annotations(self, paper_id: str) -> List[Dict[str, Any]]:
        """Get all annotations for a paper."""
        async with self.conn.execute(
            "SELECT * FROM annotations WHERE paper_id = ? ORDER BY page, created_at",
            (paper_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                result = dict(row)
                result["geometry"] = json.loads(result["geometry"])
                results.append(result)
            return results

    async def delete_annotation(self, annotation_id: str):
        """Delete an annotation."""
        await self.conn.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
        await self.conn.commit()

    # Chunk operations
    async def add_chunks(self, chunks: List[Dict[str, Any]]):
        """Add text chunks for a paper."""
        for chunk in chunks:
            await self.conn.execute(
                """INSERT OR REPLACE INTO chunks
                   (id, paper_id, page, bbox, text, chunk_index)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    chunk["id"],
                    chunk["paper_id"],
                    chunk["page"],
                    json.dumps(chunk["bbox"]),
                    chunk["text"],
                    chunk.get("chunk_index", 0)
                )
            )
        await self.conn.commit()

    async def get_chunks(self, paper_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a paper."""
        async with self.conn.execute(
            "SELECT * FROM chunks WHERE paper_id = ? ORDER BY page, chunk_index",
            (paper_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                result = dict(row)
                result["bbox"] = json.loads(result["bbox"])
                results.append(result)
            return results

    async def delete_chunks(self, paper_id: str):
        """Delete all chunks for a paper."""
        await self.conn.execute("DELETE FROM chunks WHERE paper_id = ?", (paper_id,))
        await self.conn.commit()

    # Embedding operations
    async def add_embedding(self, chunk_id: str, vector: bytes):
        """Add embedding for a chunk."""
        await self.conn.execute(
            "INSERT OR REPLACE INTO embeddings (chunk_id, vector) VALUES (?, ?)",
            (chunk_id, vector)
        )
        await self.conn.commit()

    async def get_embeddings(self, paper_id: str) -> List[Dict[str, Any]]:
        """Get all embeddings for a paper's chunks."""
        async with self.conn.execute(
            """SELECT c.id, c.page, c.bbox, c.text, e.vector
               FROM chunks c
               JOIN embeddings e ON c.id = e.chunk_id
               WHERE c.paper_id = ?
               ORDER BY c.page, c.chunk_index""",
            (paper_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                result = dict(row)
                result["bbox"] = json.loads(result["bbox"])
                results.append(result)
            return results

    # Job operations
    async def add_job(self, job: Dict[str, Any]) -> str:
        """Add a job to the queue."""
        now = datetime.utcnow().isoformat()
        await self.conn.execute(
            """INSERT INTO jobs
               (id, paper_id, type, status, priority, created_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                job["id"],
                job["paper_id"],
                job["type"],
                "pending",
                job.get("priority", 0),
                now,
                json.dumps(job.get("metadata", {}))
            )
        )
        await self.conn.commit()
        return job["id"]

    async def get_pending_jobs(self) -> List[Dict[str, Any]]:
        """Get all pending jobs ordered by priority."""
        async with self.conn.execute(
            "SELECT * FROM jobs WHERE status = 'pending' ORDER BY priority DESC, created_at ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_job(self, job_id: str, updates: Dict[str, Any]):
        """Update job status."""
        allowed_fields = ["status", "error", "started_at", "finished_at"]
        set_clauses = []
        values = []

        for field, value in updates.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = ?")
                values.append(value)

        if set_clauses:
            values.append(job_id)
            query = f"UPDATE jobs SET {', '.join(set_clauses)} WHERE id = ?"
            await self.conn.execute(query, tuple(values))
            await self.conn.commit()

    async def get_batch_status(self) -> Dict[str, Any]:
        """Get batch queue status."""
        async with self.conn.execute(
            """SELECT status, COUNT(*) as count FROM jobs GROUP BY status"""
        ) as cursor:
            rows = await cursor.fetchall()
            status = {row["status"]: row["count"] for row in rows}

        async with self.conn.execute(
            "SELECT * FROM jobs WHERE status = 'running' LIMIT 1"
        ) as cursor:
            current = await cursor.fetchone()

        return {
            "pending": status.get("pending", 0),
            "running": status.get("running", 0),
            "completed": status.get("completed", 0),
            "failed": status.get("failed", 0),
            "current_job": dict(current) if current else None
        }
