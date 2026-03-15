"""Data models for retrieval results."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChunkResult:
    """A single RAPTOR chunk search result."""

    node_id: str
    article_id: str
    level: int
    text: str
    score: float
    keywords: list[str] = field(default_factory=list)
    # Dedup tracking
    hit_count: int = 1  # how many query variants found this
    found_by: list[str] = field(default_factory=list)  # which queries


@dataclass
class ConceptResult:
    """A concept search result."""

    concept_id: str
    name: str
    domain: str
    description: str
    score: float
    keywords: list[str] = field(default_factory=list)
    articles: list[str] = field(default_factory=list)
    relations: list[dict] = field(default_factory=list)
    hit_count: int = 1
    found_by: list[str] = field(default_factory=list)


@dataclass
class RelationResult:
    """A cross-relation search result."""

    source_concept_id: str
    target_concept_id: str
    source_name: str = ""
    target_name: str = ""
    predicate: str = ""
    description: str = ""
    score: float = 0.0
    hit_count: int = 1
    found_by: list[str] = field(default_factory=list)


@dataclass
class RetrievalResult:
    """Full retrieval result across all sources."""

    query: str
    rephrased_queries: list[str] = field(default_factory=list)
    chunks: list[ChunkResult] = field(default_factory=list)
    concepts: list[ConceptResult] = field(default_factory=list)
    relations: list[RelationResult] = field(default_factory=list)
