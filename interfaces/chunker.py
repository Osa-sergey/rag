"""Abstract base for document chunkers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from raptor_pipeline.chunker.base import Chunk


class BaseChunker(ABC):
    """Abstract base for document chunkers.

    Splits a structured document (list of blocks from YAML) into
    a list of Chunk objects suitable for embedding and indexing.
    """

    @abstractmethod
    def chunk(self, document: list[dict], article_id: str) -> list[Chunk]:
        """Split a structured document into a list of Chunks.

        Args:
            document: Parsed document (list of blocks from YAML).
            article_id: Identifier of the source article.

        Returns:
            List of Chunk objects.
        """
        ...
