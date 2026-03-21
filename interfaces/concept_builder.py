"""Abstract bases for concept builder components."""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseArticleSelector(ABC):
    """Abstract base for selecting related articles for concept building."""

    @abstractmethod
    def select_by_traversal(
        self,
        base_article_id: str,
        strategy: str = "bfs",
        max_articles: int = 20,
    ) -> list[str]:
        """Traverse REFERENCES graph from base article.

        Args:
            base_article_id: Starting article.
            strategy: 'bfs' or 'dfs'.
            max_articles: Maximum number of articles to return.

        Returns:
            List of article IDs.
        """
        ...

    @abstractmethod
    def select_explicit(
        self,
        article_ids: list[str],
        check_connectivity: bool = True,
    ) -> list[str]:
        """Validate and return an explicit list of article IDs.

        Args:
            article_ids: Explicit list.
            check_connectivity: If True, verify all articles are
                connected via REFERENCES (directly or transitively).

        Returns:
            Validated list of article IDs.

        Raises:
            ValueError: If check_connectivity is True and articles are disconnected.
        """
        ...


class BaseKeywordDescriber(ABC):
    """Abstract base for generating keyword descriptions in article context."""

    @abstractmethod
    def describe(
        self,
        keyword_word: str,
        article_id: str,
        chunk_ids: list[str],
    ) -> str:
        """Generate a 1-2 sentence description of a keyword in article context.

        Uses dual-context strategy:
          - Max-level chunk for broad context.
          - Leaf chunk with highest confidence for detail.

        Args:
            keyword_word: The keyword text.
            article_id: Source article.
            chunk_ids: RAPTOR node IDs where this keyword appears.

        Returns:
            Short description string.
        """
        ...


class BaseConceptClusterer(ABC):
    """Abstract base for clustering keywords into concepts."""

    @abstractmethod
    def cluster(
        self,
        keyword_contexts: list,
        similarity_threshold: float = 0.85,
    ) -> list[list]:
        """Group keyword contexts by semantic similarity.

        Args:
            keyword_contexts: List of KeywordContext objects with embeddings.
            similarity_threshold: Cosine similarity threshold for grouping.

        Returns:
            List of clusters, each cluster is a list of KeywordContext.
        """
        ...


class BaseConceptInspector(ABC):
    """Abstract base for inspecting concepts with provenance tracing."""

    @abstractmethod
    def inspect_concept(self, concept_id: str) -> dict:
        """Concept → Keywords → chunk_ids → chunk texts.

        Returns:
            Dict with concept details and traced source chunks.
        """
        ...

    @abstractmethod
    def trace_keyword_to_chunks(
        self, keyword_word: str, article_id: str,
    ) -> list[dict]:
        """Trace a keyword back to its source chunk texts.

        Returns:
            List of dicts with chunk_id, text, level.
        """
        ...
