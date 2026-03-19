"""Abstract bases for knowledge graph extractors."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from raptor_pipeline.knowledge_graph.base import Keyword, Relation


class BaseKeywordExtractor(ABC):
    """Abstract base for keyword extractors.

    Extracts keywords/key-phrases from text for knowledge graph construction.
    """

    @abstractmethod
    def extract(self, text: str, chunk_id: str = "") -> list[Keyword]:
        """Extract keywords from text.

        Args:
            text: Source text.
            chunk_id: ID of the source chunk (for provenance).

        Returns:
            List of Keyword dataclass objects.
        """
        ...


class BaseKeywordRefiner(ABC):
    """Abstract base for keyword refiners.

    Merges synonyms, normalizes terminology, and fixes categories
    across a batch of raw extracted keywords.
    """

    @abstractmethod
    def refine(self, raw_keywords: list[dict[str, str]]) -> list[dict]:
        """Refine and deduplicate raw keywords.

        Args:
            raw_keywords: List of dicts with keys 'word' and 'category'.

        Returns:
            List of dicts with keys 'refined_word', 'category', 'original_words'.
        """
        ...


class BaseRelationExtractor(ABC):
    """Abstract base for relation (triple) extractors.

    Extracts subject-predicate-object triples from text using
    extracted keywords as context hints.
    """

    @abstractmethod
    def extract(
        self, text: str, keywords: list[Keyword], chunk_id: str = "",
    ) -> list[Relation]:
        """Extract relations from text.

        Args:
            text: Source text.
            keywords: Extracted keywords for context.
            chunk_id: ID of the source chunk.

        Returns:
            List of Relation dataclass objects.
        """
        ...
