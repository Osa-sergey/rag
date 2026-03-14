"""Abstract base classes for all swappable components.

This is the canonical location for all ABCs.
Import via ``from interfaces import BaseGraphStore`` etc.

Hierarchy:
    # ── Embeddings / Stores ───────────────────────────
    BaseEmbeddingProvider   — embed_texts, embed_query, embedding_dim
    BaseGraphStore          — articles, keywords, relations, topics
    BaseVectorStore         — ensure_collection, upsert_nodes, search

    # ── RAPTOR pipeline ───────────────────────────────
    BaseChunker             — chunk(document, article_id)
    BaseSummarizer          — summarize(texts)
    BaseKeywordExtractor    — extract(text, chunk_id)
    BaseKeywordRefiner      — refine(raw_keywords)
    BaseRelationExtractor   — extract(text, keywords, chunk_id)

    # ── Vault parser ─────────────────────────────────
    BaseVaultParser         — parse_all, parse_daily/weekly/monthly
    BaseNoteEditor          — exists, read, read_raw, create
      └─ BaseDailyNoteEditor — add_task, list_tasks, delete_task
    BaseWellnessEditor      — set_sleep, set_energy, set_focus (mixin)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from raptor_pipeline.chunker.base import Chunk
    from raptor_pipeline.knowledge_graph.base import Keyword, Relation
    from vault_parser.models import DayNote, VaultTask, WeeklyNote, MonthlyNote
    from vault_parser.people import PeopleRegistry


# ══════════════════════════════════════════════════════════════
# Embedding Provider
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
# Graph Store
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
# Vector Store
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
# Vault Parser
# ══════════════════════════════════════════════════════════════

class BaseVaultParser(ABC):
    """Abstract base for vault note parsers.

    Parses an entire Obsidian vault directory into structured
    DayNote / WeeklyNote / MonthlyNote objects.
    """

    @abstractmethod
    def parse_all(self) -> dict[str, list[DayNote] | list[WeeklyNote] | list[MonthlyNote]]:
        """Parse all notes (daily, weekly, monthly).

        Returns:
            Dict with keys ``'daily'``, ``'weekly'``, ``'monthly'``.
        """
        ...

    @abstractmethod
    def all_tasks(self) -> list[VaultTask]:
        """Extract all tasks across all daily and weekly notes.

        Returns:
            Flat list of VaultTask objects.
        """
        ...

    @abstractmethod
    def parse_daily_notes(self) -> list[DayNote]:
        """Parse daily notes, sorted by date ascending."""
        ...

    @abstractmethod
    def parse_weekly_notes(self) -> list[WeeklyNote]:
        """Parse weekly notes, sorted by week ascending."""
        ...

    @abstractmethod
    def parse_monthly_notes(self) -> list[MonthlyNote]:
        """Parse monthly notes, sorted by month ascending."""
        ...

    @property
    @abstractmethod
    def people_registry(self) -> PeopleRegistry | None:
        """Return loaded PeopleRegistry, or None if people_dir was not set."""
        ...


# ══════════════════════════════════════════════════════════════
# Note Editor  (3-level hierarchy)
# ══════════════════════════════════════════════════════════════

class BaseNoteEditor(ABC):
    """Base for any note editor (daily / weekly / monthly).

    Provides only the universal operations that apply to
    any type of Obsidian note regardless of its structure.
    """

    @abstractmethod
    def exists(self, note_date: str | date) -> bool:
        """Check if a note exists for this date."""
        ...

    @abstractmethod
    def read(self, note_date: str | date) -> DayNote | None:
        """Parse and return structured content of a note.

        Returns:
            Parsed note object, or None if the file doesn't exist.
        """
        ...

    @abstractmethod
    def read_raw(self, note_date: str | date) -> str | None:
        """Return raw markdown content.

        Returns:
            Markdown string, or None if the file doesn't exist.
        """
        ...

    @abstractmethod
    def create_from_template(
        self, note_date: str | date, template_path: str | Path | None = None,
    ) -> Path:
        """Create a new note from a template.

        Returns:
            Path to the created file.

        Raises:
            FileExistsError: If a note already exists for this date.
        """
        ...


class BaseDailyNoteEditor(BaseNoteEditor):
    """Editor for daily notes — adds task management.

    Task operations are universal across any daily note format.
    """

    @abstractmethod
    def add_task(
        self, note_date: str | date, text: str, *,
        section: str = "main",
        scheduled_date: date | None = None,
        start_date: date | None = None,
        due_date: date | None = None,
        time_slot: str | None = None,
        people: list[str] | None = None,
        completion_date: date | None = None,
        recurrence: str | None = None,
    ) -> None:
        """Add a task to a section.

        Args:
            note_date: Target date.
            text: Task description.
            section: ``'main'`` or ``'secondary'``.
        """
        ...

    @abstractmethod
    def update_task_status(
        self, note_date: str | date, query: str, new_status: Any, *,
        completion_date: date | None = None,
    ) -> bool:
        """Update the status of a task matching the query substring.

        Returns:
            True if a task was found and updated.
        """
        ...

    @abstractmethod
    def list_tasks(self, note_date: str | date) -> list[VaultTask]:
        """List all tasks in a note (for preview / confirmation).

        Returns:
            List of VaultTask objects with ``raw_line`` and ``section`` populated.

        Raises:
            FileNotFoundError: If the note doesn't exist.
        """
        ...

    @abstractmethod
    def delete_task(self, note_date: str | date, query: str) -> bool:
        """Delete a task whose text matches the query substring.

        The first matching checkbox line is removed entirely from the file.

        Args:
            note_date: Target date.
            query: Substring to match against the task line (case-insensitive).

        Returns:
            True if a task was found and deleted.

        Raises:
            FileNotFoundError: If the note doesn't exist.
        """
        ...


class BaseWellnessEditor(ABC):
    """Mixin for wellness / reflection operations.

    These are OPTIONAL and specific to note formats that track
    sleep, energy, focus, gratitude, problems, etc.

    Compose with BaseDailyNoteEditor::

        class DailyNoteEditor(BaseDailyNoteEditor, BaseWellnessEditor):
            ...
    """

    @abstractmethod
    def set_sleep(self, note_date: str | date, **kwargs: Any) -> None:
        """Update sleep data in frontmatter.

        Args:
            **kwargs: bed_time_start, sleep_start, sleep_end,
                sleep_duration, sleep_quality, quick_fall_asleep,
                night_awakenings, deep_sleep, remembered_dreams,
                no_nightmare, morning_mood, no_phone,
                physical_exercise, late_dinner.
        """
        ...

    @abstractmethod
    def set_energy(
        self, note_date: str | date, *,
        morning: int | None = None,
        day: int | None = None,
        evening: int | None = None,
    ) -> None:
        """Update energy levels in frontmatter."""
        ...

    @abstractmethod
    def set_focus(self, note_date: str | date, items: list[str]) -> None:
        """Set the focus items bullet list."""
        ...

    @abstractmethod
    def set_gratitude(self, note_date: str | date, text: str) -> None:
        """Set the gratitude section."""
        ...

    @abstractmethod
    def set_notes(self, note_date: str | date, text: str) -> None:
        """Set the notes section."""
        ...

    @abstractmethod
    def set_problem(
        self, note_date: str | date,
        what: str, cause: str = "", consequences: str = "",
    ) -> None:
        """Set the problem/post-mortem section."""
        ...

    @abstractmethod
    def add_think_about(self, note_date: str | date, text: str) -> None:
        """Append an item to the 'things to think about' section."""
        ...


# ══════════════════════════════════════════════════════════════
# Chunker
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
# Summarizer
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
# Knowledge Graph — Extractors
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
# Concept Builder
# ══════════════════════════════════════════════════════════════

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

