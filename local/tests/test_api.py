"""Tests for API endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from scriptor_local.app import app
from scriptor_local.config import config


@pytest.fixture
async def client():
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Get authorization headers."""
    return {"Authorization": f"Bearer {config.auth_token}"}


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health endpoint (no auth required)."""
    response = await client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_status_requires_auth(client):
    """Test that status endpoint requires authentication."""
    response = await client.get("/api/status")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_status_with_auth(client, auth_headers):
    """Test status endpoint with valid auth."""
    response = await client.get("/api/status", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["connected"] is True
    assert "papers_count" in data


@pytest.mark.asyncio
async def test_pair_invalid_token(client):
    """Test pairing with invalid token."""
    response = await client.post(
        "/api/pair",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_pair_valid_token(client, auth_headers):
    """Test pairing with valid token."""
    response = await client.post("/api/pair", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["paired"] is True


@pytest.mark.asyncio
async def test_list_papers_empty(client, auth_headers):
    """Test listing papers when empty."""
    response = await client.get("/api/papers/list", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "papers" in data
    assert isinstance(data["papers"], list)


@pytest.mark.asyncio
async def test_get_nonexistent_paper(client, auth_headers):
    """Test getting a paper that doesn't exist."""
    response = await client.get(
        "/api/papers/nonexistent-id",
        headers=auth_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_batch_status(client, auth_headers):
    """Test getting batch status."""
    response = await client.get("/api/batch/status", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "pending" in data
    assert "running" in data
    assert "completed" in data


@pytest.mark.asyncio
async def test_latexify_status(client, auth_headers):
    """Test LaTeXify service status."""
    response = await client.get("/api/latexify/status", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "pix2tex_available" in data
    assert "gemini_configured" in data
    assert "ready" in data


@pytest.mark.asyncio
async def test_get_token(client):
    """Test getting auth token (for pairing UI)."""
    response = await client.get("/api/config/token")
    assert response.status_code == 200

    data = response.json()
    assert "token" in data
    assert len(data["token"]) > 0


@pytest.mark.asyncio
async def test_parse_citation(client, auth_headers):
    """Test citation parsing endpoint."""
    citation = "Smith, J. (2020). A Test Paper. Journal of Testing, 1(1), 1-10."

    response = await client.post(
        "/api/bibtex/parse",
        headers=auth_headers,
        json={"citation": citation}
    )
    assert response.status_code == 200

    data = response.json()
    assert "bibtex" in data
    assert "@article" in data["bibtex"]


@pytest.mark.asyncio
async def test_add_paper_no_url(client, auth_headers):
    """Test adding paper without URL or file."""
    response = await client.post(
        "/api/papers/add",
        headers=auth_headers,
        json={}
    )
    assert response.status_code == 400


class TestAnnotations:
    """Tests for annotation endpoints."""

    @pytest.mark.asyncio
    async def test_get_annotations_nonexistent_paper(self, client, auth_headers):
        """Test getting annotations for nonexistent paper."""
        response = await client.get(
            "/api/annotations/nonexistent-id",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["annotations"] == []

    @pytest.mark.asyncio
    async def test_delete_annotation(self, client, auth_headers):
        """Test deleting an annotation."""
        response = await client.delete(
            "/api/annotations/nonexistent-id",
            headers=auth_headers
        )
        # Should succeed even if annotation doesn't exist
        assert response.status_code == 200


class TestSemanticSearch:
    """Tests for semantic search endpoint."""

    @pytest.mark.asyncio
    async def test_search_nonexistent_paper(self, client, auth_headers):
        """Test searching a nonexistent paper."""
        response = await client.post(
            "/api/search/semantic",
            headers=auth_headers,
            json={
                "paper_id": "nonexistent",
                "query": "test query"
            }
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_search_missing_query(self, client, auth_headers):
        """Test search with missing required fields."""
        response = await client.post(
            "/api/search/semantic",
            headers=auth_headers,
            json={"paper_id": "test"}
        )
        assert response.status_code == 422  # Validation error
