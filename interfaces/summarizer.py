"""Abstract base for text summarizers."""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseSummarizer(ABC):
    """Abstract base for text summarizers.

    Used by RAPTOR tree builder to summarize clusters of chunks
    into higher-level nodes.
    """

    @abstractmethod
    def summarize(self, texts: list[str]) -> str:
        """Summarize a group of texts into one summary.

        Args:
            texts: List of text chunks to be summarized.

        Returns:
            A single summary string.
        """
        ...
