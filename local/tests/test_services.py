"""Tests for service modules."""
import pytest
from pathlib import Path
import tempfile
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scriptor_local.services.embeddings import EmbeddingService, generate_micro_summary
from scriptor_local.services.export import (
    parse_citation_to_bibtex,
    generate_doi_link
)


class TestEmbeddingService:
    """Tests for the embedding service."""

    @pytest.fixture
    def embedding_service(self):
        """Create embedding service instance."""
        # Use a small model for testing
        return EmbeddingService(model_name="all-MiniLM-L6-v2")

    def test_embed_text(self, embedding_service):
        """Test embedding a single text."""
        text = "This is a test sentence for embedding."
        embedding = embedding_service.embed_text(text)

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] == 384  # MiniLM dimension
        # Check normalized
        assert abs(np.linalg.norm(embedding) - 1.0) < 0.01

    def test_embed_texts(self, embedding_service):
        """Test embedding multiple texts."""
        texts = [
            "First test sentence.",
            "Second test sentence.",
            "Third test sentence."
        ]
        embeddings = embedding_service.embed_texts(texts)

        assert len(embeddings) == 3
        for emb in embeddings:
            assert emb.shape[0] == 384

    def test_vector_serialization(self, embedding_service):
        """Test vector to bytes conversion and back."""
        text = "Test sentence"
        original = embedding_service.embed_text(text)

        # Convert to bytes and back
        bytes_data = embedding_service.vector_to_bytes(original)
        restored = embedding_service.bytes_to_vector(bytes_data)

        np.testing.assert_array_almost_equal(original, restored)

    def test_cosine_similarity(self, embedding_service):
        """Test cosine similarity calculation."""
        text1 = "The cat sat on the mat."
        text2 = "A cat is sitting on a rug."
        text3 = "The stock market is volatile."

        vec1 = embedding_service.embed_text(text1)
        vec2 = embedding_service.embed_text(text2)
        vec3 = embedding_service.embed_text(text3)

        sim_similar = embedding_service.cosine_similarity(vec1, vec2)
        sim_different = embedding_service.cosine_similarity(vec1, vec3)

        # Similar sentences should have higher similarity
        assert sim_similar > sim_different
        # Similarity should be between -1 and 1
        assert -1 <= sim_similar <= 1
        assert -1 <= sim_different <= 1

    def test_search(self, embedding_service):
        """Test semantic search functionality."""
        # Create mock chunks with embeddings
        texts = [
            "Machine learning is a subset of artificial intelligence.",
            "Deep learning uses neural networks.",
            "The weather today is sunny.",
            "Natural language processing handles text."
        ]

        chunks = []
        for i, text in enumerate(texts):
            vec = embedding_service.embed_text(text)
            chunks.append({
                "id": f"chunk_{i}",
                "page": 0,
                "bbox": {"x": 0, "y": i * 20, "width": 100, "height": 15},
                "text": text,
                "vector": embedding_service.vector_to_bytes(vec)
            })

        # Search for AI-related content
        results = embedding_service.search("artificial intelligence", chunks, top_k=2)

        assert len(results) == 2
        # First result should be the most relevant (about AI/ML)
        assert "machine learning" in results[0]["text"].lower() or \
               "artificial intelligence" in results[0]["text"].lower()

    def test_normalize_scores(self, embedding_service):
        """Test score normalization."""
        results = [
            {"id": "1", "score": 0.9},
            {"id": "2", "score": 0.5},
            {"id": "3", "score": 0.1}
        ]

        normalized = embedding_service.normalize_scores(results)

        assert normalized[0]["normalized_score"] == 1.0  # Highest
        assert normalized[2]["normalized_score"] == 0.0  # Lowest
        assert 0 < normalized[1]["normalized_score"] < 1  # Middle


class TestMicroSummary:
    """Tests for micro-summary generation."""

    def test_generate_micro_summary(self):
        """Test basic micro-summary generation."""
        text = "This research proposes a novel approach to quantum computing using trapped ions."
        summary = generate_micro_summary(text, max_words=5)

        words = summary.split()
        assert len(words) <= 5

    def test_short_text(self):
        """Test with very short text."""
        text = "Hello world"
        summary = generate_micro_summary(text, max_words=5)
        assert len(summary) > 0

    def test_empty_text(self):
        """Test with empty text."""
        summary = generate_micro_summary("", max_words=5)
        assert summary == "Key finding"  # Default fallback


class TestCitationParsing:
    """Tests for citation parsing."""

    def test_parse_standard_citation(self):
        """Test parsing a standard APA-style citation."""
        citation = "Smith, J., & Doe, A. (2020). A Study of Testing. Journal of Tests, 15(2), 100-120."
        bibtex = parse_citation_to_bibtex(citation)

        assert "@article" in bibtex
        assert "2020" in bibtex
        assert "Smith" in bibtex

    def test_parse_citation_with_quotes(self):
        """Test parsing citation with quoted title."""
        citation = 'Johnson, M. (2019). "Machine Learning for Everyone." AI Review.'
        bibtex = parse_citation_to_bibtex(citation)

        assert "Machine Learning" in bibtex
        assert "2019" in bibtex

    def test_parse_minimal_citation(self):
        """Test parsing minimal citation."""
        citation = "Unknown Author, Some Paper"
        bibtex = parse_citation_to_bibtex(citation)

        # Should still generate something valid
        assert "@article" in bibtex


class TestDOILink:
    """Tests for DOI link generation."""

    def test_generate_doi_link_plain(self):
        """Test with plain DOI."""
        doi = "10.1234/test.123"
        link = generate_doi_link(doi)
        assert link == "https://doi.org/10.1234/test.123"

    def test_generate_doi_link_with_prefix(self):
        """Test with DOI that has doi: prefix."""
        doi = "doi:10.1234/test.123"
        link = generate_doi_link(doi)
        assert link == "https://doi.org/10.1234/test.123"

    def test_generate_doi_link_full_url(self):
        """Test with full DOI URL."""
        doi = "https://doi.org/10.1234/test.123"
        link = generate_doi_link(doi)
        assert link == "https://doi.org/10.1234/test.123"

    def test_generate_doi_link_http(self):
        """Test with HTTP DOI URL (should upgrade to HTTPS)."""
        doi = "http://doi.org/10.1234/test.123"
        link = generate_doi_link(doi)
        assert link == "https://doi.org/10.1234/test.123"


class TestConfig:
    """Tests for configuration management."""

    def test_config_creation(self, temp_dir):
        """Test that config is created with defaults."""
        from scriptor_local.config import Config

        config_path = temp_dir / "new_config.json"
        config = Config(config_path)

        assert config.auth_token is not None
        assert len(config.auth_token) > 20
        assert config.server_port == 52525
        assert config_path.exists()

    def test_config_regenerate_token(self, temp_dir):
        """Test token regeneration."""
        from scriptor_local.config import Config

        config_path = temp_dir / "config.json"
        config = Config(config_path)
        old_token = config.auth_token

        new_token = config.regenerate_token()

        assert new_token != old_token
        assert config.auth_token == new_token

    def test_config_persistence(self, temp_dir):
        """Test that config persists across loads."""
        from scriptor_local.config import Config

        config_path = temp_dir / "config.json"
        config1 = Config(config_path)
        token = config1.auth_token

        # Load again
        config2 = Config(config_path)
        assert config2.auth_token == token
