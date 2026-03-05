"""Abstract base for summarisers."""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseSummarizer(ABC):
    """Abstract summariser interface."""

    @abstractmethod
    def summarize(self, texts: list[str]) -> str:
        """Summarise a group of texts into one summary.

        Args:
            texts: List of text chunks to be summarised.

        Returns:
            A single summary string.
        """
        ...
