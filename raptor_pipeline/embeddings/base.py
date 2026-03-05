"""Abstract base class for embedding providers."""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """Abstract base for computing text embeddings."""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Compute embeddings for a batch of texts.

        Args:
            texts: List of text strings.

        Returns:
            List of embedding vectors (each a list of floats).
        """
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Compute embedding for a single query text.

        Args:
            text: Query string.

        Returns:
            Embedding vector.
        """
        ...
