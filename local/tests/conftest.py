"""Pytest configuration and fixtures."""
import pytest
import tempfile
import asyncio
from pathlib import Path
from httpx import AsyncClient, ASGITransport
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scriptor_local.app import app
from scriptor_local.config import Config
from scriptor_local.models.database import Database


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config(temp_dir):
    """Create a test configuration."""
    config_path = temp_dir / "config.json"
    config = Config(config_path)
    config.storage_dir = temp_dir / "storage"
    config.save()
    return config


@pytest.fixture
async def test_db(temp_dir):
    """Create a test database."""
    db_path = temp_dir / "test.db"
    db = Database(db_path)
    await db.connect()
    yield db
    await db.close()


@pytest.fixture
async def client(test_config):
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers(test_config):
    """Get authorization headers for API requests."""
    return {"Authorization": f"Bearer {test_config.auth_token}"}


@pytest.fixture
def sample_pdf_bytes():
    """Generate a minimal valid PDF for testing."""
    # Minimal PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
306
%%EOF"""
    return pdf_content
