"""Data models for cross-article concept builder."""
from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class KeywordContext:
    """Keyword in context of a specific article.

    Attributes:
        word:           The keyword text.
        article_id:     Source article.
        version:        Article version at extraction time.
        category:       Keyword category.
        confidence:     Extraction confidence 0-1.
        chunk_ids:      RAPTOR node IDs where this keyword appears.
        description:    Short description in article context (generated lazily).
        embedding:      Embedding of the description (computed on demand).
    """

    word: str
    article_id: str
    version: str = ""
    category: str = ""
    confidence: float = 1.0
    chunk_ids: list[str] = field(default_factory=list)
    description: str = ""
    embedding: list[float] | None = None


@dataclass
class ConceptNode:
    """A cross-article concept — unifies semantically similar keywords.

    Attributes:
        id:                 UUID (unique per version).
        concept_group_id:   Shared UUID across all versions of same concept.
        canonical_name:     Primary name (e.g. "docker").
        domain:             Knowledge domain (e.g. "devops", "ml").
        description:        Generalized description from all source articles.
        source_articles:    List of article IDs contributing to this concept.
        source_versions:    Mapping {article_id: version} for provenance.
        keyword_words:      Which Keyword.word instances map to this concept.
        version:            Version number (1-based, increments on expand).
        is_active:          Whether this is the currently active version.
        previous_version_id: UUID of the previous version (for tracing).
        embedding:          Embedding of the description.
        created_at:         Creation timestamp.
        updated_at:         Last update timestamp.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    concept_group_id: str = ""
    canonical_name: str = ""
    domain: str = ""
    description: str = ""
    source_articles: list[str] = field(default_factory=list)
    source_versions: dict[str, str] = field(default_factory=dict)
    keyword_words: list[str] = field(default_factory=list)
    version: int = 1
    is_active: bool = True
    previous_version_id: str | None = None
    run_id: str = ""  # identifies which process/expand run created this
    embedding: list[float] | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __post_init__(self):
        if not self.concept_group_id:
            self.concept_group_id = self.id

    def evolve(
        self,
        new_keywords: list[KeywordContext],
        new_description: str = "",
        new_domain: str = "",
    ) -> ConceptNode:
        """Create a new version of this concept with additional keywords.

        Returns a new ConceptNode with incremented version,
        new UUID, and updated fields. The original is untouched.
        """
        new_kw_words = list(set(
            self.keyword_words + [kc.word for kc in new_keywords]
        ))
        new_articles = list(set(
            self.source_articles + [kc.article_id for kc in new_keywords]
        ))
        new_versions = dict(self.source_versions)
        for kc in new_keywords:
            if kc.article_id and kc.version:
                new_versions[kc.article_id] = kc.version

        return ConceptNode(
            id=str(uuid.uuid4()),
            concept_group_id=self.concept_group_id,
            canonical_name=self.canonical_name,
            domain=new_domain or self.domain,
            description=new_description or self.description,
            source_articles=new_articles,
            source_versions=new_versions,
            keyword_words=new_kw_words,
            version=self.version + 1,
            is_active=False,  # not active until user chooses
            previous_version_id=self.id,
        )


@dataclass
class ExpandResult:
    """Result of expand matching for a single Concept.

    Holds version candidates and user's choice.
    """

    concept_id: str
    concept_name: str
    domain: str
    original_version: int
    original: ConceptNode

    # Version v(N+1): direct cosine matches
    v_direct: ConceptNode | None = None
    direct_keywords: list[tuple[str, float]] = field(default_factory=list)

    # Version v(N+2): direct + LLM-verified
    v_llm: ConceptNode | None = None
    llm_keywords: list[tuple[str, float, str]] = field(default_factory=list)

    # User's choice
    chosen_version: int | None = None


@dataclass
class CrossRelation:
    """A relationship between two Concept nodes across articles.

    Attributes:
        source_concept_id:  UUID of source Concept.
        target_concept_id:  UUID of target Concept.
        predicate:          Relationship type (e.g. "используется_в").
        description:        Human-readable description of the relationship.
        source_articles:    Articles that contributed to this relation.
        source_versions:    Mapping {article_id: version} for provenance.
        confidence:         Extraction confidence 0-1.
        embedding:          Embedding of the description.
    """

    source_concept_id: str
    target_concept_id: str
    predicate: str = ""
    description: str = ""
    source_articles: list[str] = field(default_factory=list)
    source_versions: dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0
    embedding: list[float] | None = None


@dataclass
class DryRunReport:
    """Report from dry-run analysis — what would be processed.

    Attributes:
        articles:           List of article IDs selected.
        article_names:      Mapping article_id → article_name.
        total_keywords:     Total keywords (confidence ≥ threshold).
        keywords_per_article: {article_id: count with confidence ≥ threshold}.
        raw_keywords_per_article: {article_id: total count including low confidence}.
        confidence_distributions: {article_id: {high, med, low, null} counts}.
        sample_confidences: {article_id: [first 10 confidence values]} for debugging.
        references:         List of (source, target) article pairs.
        estimated_llm_calls: Estimated number of LLM calls.
    """

    articles: list[str] = field(default_factory=list)
    article_names: dict[str, str] = field(default_factory=dict)
    total_keywords: int = 0
    keywords_per_article: dict[str, int] = field(default_factory=dict)
    raw_keywords_per_article: dict[str, int] = field(default_factory=dict)
    confidence_distributions: dict[str, dict] = field(default_factory=dict)
    sample_confidences: dict[str, list] = field(default_factory=dict)
    unprocessed_articles: list[str] = field(default_factory=list)
    keywords_needing_description: dict[str, int] = field(default_factory=dict)
    total_needing_description: int = 0
    references: list[tuple[str, str]] = field(default_factory=list)
    estimated_llm_calls: int = 0
