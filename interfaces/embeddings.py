"""Abstract base for embedding providers."""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """Abstract base for computing text embeddings.

    Every implementation must expose ``embedding_dim`` so that
    downstream consumers (vector store, pipeline) know the
    expected vector size without computing a dummy embedding.
    """

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Dimensionality of the produced embeddings."""
        ...

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Compute embeddings for a batch of texts.

        Args:
            texts: List of text strings.

        Returns:
            List of embedding vectors, len == len(texts).
        """
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Compute embedding for a single query text.

        Args:
            text: Query string.

        Returns:
            Embedding vector of length ``embedding_dim``.
        """
        ...
