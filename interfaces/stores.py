"""Abstract bases for store implementations (graph + vector)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from raptor_pipeline.knowledge_graph.base import Keyword, Relation


class BaseGraphStore(ABC):
    """Abstract base for knowledge graph store implementations.

    Manages nodes: Article, Keyword, Topic.
    Manages relationships: HAS_KEYWORD, RELATED_TO, BELONGS_TO_TOPIC, REFERENCES.
    """

    # ── Lifecycle ─────────────────────────────────────────────

    @abstractmethod
    def ensure_indexes(self) -> None:
        """Create indexes / constraints for fast lookups."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Release resources (connections, drivers)."""
        ...

    # ── Articles ──────────────────────────────────────────────

    @abstractmethod
    def store_article(
        self, article_id: str, title: str = "", summary: str = "",
        article_name: str = "", version: str = "",
    ) -> None:
        """Create or merge an Article node."""
        ...

    @abstractmethod
    def store_article_metadata(self, article_id: str, metadata: dict[str, Any]) -> None:
        """Upsert article metadata.

        Supported keys: author, reading_time, complexity, labels, tags, hubs.
        Only the supplied keys are updated; existing properties are preserved.
        """
        ...

    @abstractmethod
    def store_links(
        self, source_article_id: str, links: list[Any], version: str = "",
    ) -> None:
        """Store cross-article references.

        Creates REFERENCES relationships between Article nodes.
        Target articles that don't exist yet are created as placeholders.
        """
        ...

    # ── Keywords & Relations ──────────────────────────────────

    @abstractmethod
    def store_keywords(self, article_id: str, keywords: list[Keyword]) -> None:
        """Store keywords and link them to the article via HAS_KEYWORD."""
        ...

    @abstractmethod
    def store_relations(self, article_id: str, relations: list[Relation]) -> None:
        """Store subject-predicate-object triples as RELATED_TO edges between Keywords."""
        ...

    @abstractmethod
    def get_article_keywords(self, article_id: str) -> list[dict[str, Any]]:
        """Retrieve all keywords for an article.

        Returns:
            List of dicts with keys: word, category, confidence, chunk_ids.
        """
        ...

    @abstractmethod
    def get_keyword_relations(self, word: str) -> list[dict[str, Any]]:
        """Get all relations involving a keyword (as subject or object).

        Returns:
            List of dicts with keys: subject, predicate, object, confidence, chunk_ids.
        """
        ...

    # ── Topics ────────────────────────────────────────────────

    @abstractmethod
    def store_topic(self, topic_id: int, label: str, top_keywords: list[str]) -> None:
        """Create or update a Topic node."""
        ...

    @abstractmethod
    def link_article_to_topic(
        self, article_id: str, topic_id: int, confidence: float = 1.0,
    ) -> None:
        """Create BELONGS_TO_TOPIC relationship between Article and Topic."""
        ...


class BaseVectorStore(ABC):
    """Abstract base for vector store implementations."""

    @abstractmethod
    def ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        ...

    @abstractmethod
    def upsert_nodes(
        self, nodes: list[Any], keywords_map: dict[str, list[str]] | None = None,
    ) -> None:
        """Upsert nodes into the vector store.

        Args:
            nodes: List of node objects (must have embeddings).
            keywords_map: Optional mapping node_id → keyword strings.
        """
        ...

    @abstractmethod
    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        level: int | None = None,
        article_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search similar vectors with optional filtering.

        Args:
            query_vector: Query embedding.
            top_k: Number of results.
            level: Optional tree level filter.
            article_id: Optional article filter.

        Returns:
            List of dicts with keys: id, score, payload.
        """
        ...

    def close(self) -> None:
        """Release resources (optional override)."""
        pass
