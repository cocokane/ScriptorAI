"""Embedding service for semantic search."""
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
import struct


class EmbeddingService:
    """Manages text embeddings using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", models_dir: Optional[Path] = None):
        self.model_name = model_name
        self.models_dir = models_dir
        self._model = None
        self._dimension = 384  # Default for MiniLM

    @property
    def model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                cache_folder = str(self.models_dir) if self.models_dir else None
                self._model = SentenceTransformer(self.model_name, cache_folder=cache_folder)
                self._dimension = self._model.get_sentence_embedding_dimension()
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
        return self._model

    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self.model.encode(text, normalize_embeddings=True)

    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts."""
        return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    def vector_to_bytes(self, vector: np.ndarray) -> bytes:
        """Convert numpy vector to bytes for storage."""
        return vector.astype(np.float32).tobytes()

    def bytes_to_vector(self, data: bytes) -> np.ndarray:
        """Convert bytes back to numpy vector."""
        return np.frombuffer(data, dtype=np.float32)

    def cosine_similarity(self, query_vec: np.ndarray, doc_vec: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        # Vectors are already normalized, so dot product = cosine similarity
        return float(np.dot(query_vec, doc_vec))

    def search(
        self,
        query: str,
        chunks_with_embeddings: List[Dict[str, Any]],
        top_k: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search chunks by semantic similarity.

        Args:
            query: Search query string
            chunks_with_embeddings: List of chunks with 'vector' field (bytes)
            top_k: Maximum results to return

        Returns:
            List of chunks with added 'score' field, sorted by relevance
        """
        query_vec = self.embed_text(query)

        results = []
        for chunk in chunks_with_embeddings:
            doc_vec = self.bytes_to_vector(chunk["vector"])
            score = self.cosine_similarity(query_vec, doc_vec)

            result = {**chunk, "score": score}
            del result["vector"]  # Don't return raw vector
            results.append(result)

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:top_k]

    def normalize_scores(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize scores to 0-1 range for heatmap display."""
        if not results:
            return results

        scores = [r["score"] for r in results]
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score

        if score_range == 0:
            # All scores the same
            for r in results:
                r["normalized_score"] = 0.5
        else:
            for r in results:
                r["normalized_score"] = (r["score"] - min_score) / score_range

        return results


def generate_micro_summary(text: str, max_words: int = 5) -> str:
    """
    Generate a micro-summary (4-5 words) for high-relevance chunks.

    This is a heuristic approach that extracts key phrases.
    For better results, integrate with an LLM.
    """
    import re

    # Clean text
    text = re.sub(r'\s+', ' ', text).strip()

    # Split into sentences
    sentences = re.split(r'[.!?]', text)
    if not sentences:
        return text[:50] + "..."

    # Take first sentence
    first_sentence = sentences[0].strip()

    # Simple extractive approach: take first N content words
    # Skip common stopwords
    stopwords = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
        'those', 'it', 'its', 'of', 'in', 'to', 'for', 'with', 'on', 'at',
        'by', 'from', 'as', 'and', 'or', 'but', 'if', 'then', 'so', 'we',
        'our', 'their', 'they', 'which', 'who', 'what', 'when', 'where'
    }

    words = first_sentence.split()
    content_words = [w for w in words if w.lower() not in stopwords and len(w) > 2]

    if len(content_words) >= max_words:
        summary = ' '.join(content_words[:max_words])
    elif words:
        summary = ' '.join(words[:max_words])
    else:
        summary = text[:30]

    # Clean up
    summary = re.sub(r'[^\w\s-]', '', summary).strip()

    return summary if summary else "Key finding"
