"""Pydantic I/O schemas for all RAG tools.

Each tool has a pair of Input/Output models with full JSON Schema
descriptions, suitable for LangGraph Structured Outputs and MCP.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# 1. raptor_process
# ═══════════════════════════════════════════════════════════════

class RaptorProcessInput(BaseModel):
    """Input for RAPTOR pipeline processing."""

    file_path: str = Field(
        ...,
        description=(
            "Path to the article file. Accepts: "
            ".yaml (pre-parsed), .md (Markdown), .html (HTML), "
            "or .csv (CSV with HTML articles). "
            "Non-YAML files are automatically converted to YAML first."
        ),
    )
    config_overrides: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional Hydra-style config overrides (key=value).",
    )

    model_config = {"extra": "forbid"}


class LinkInfo(BaseModel):
    """A cross-article link extracted from article text."""

    link_type: str = ""
    target: str = ""
    section: str = ""
    display: str = ""
    source_chunk_ids: list[str] = Field(default_factory=list)


class RaptorProcessOutput(BaseModel):
    """Output from RAPTOR pipeline processing."""

    article_id: str = Field(description="Unique article identifier.")
    article_name: str = Field(default="", description="Human-readable article name.")
    version: str = Field(default="", description="Article version string.")
    chunks: int = Field(default=0, description="Number of text chunks created.")
    raptor_nodes: int = Field(default=0, description="Total RAPTOR tree nodes.")
    keywords: int = Field(default=0, description="Total extracted keywords.")
    unique_keywords: int = Field(default=0, description="Unique keywords after refinement.")
    relations: int = Field(default=0, description="Number of extracted relations.")
    links: list[LinkInfo] = Field(
        default_factory=list,
        description="Cross-article links found in text.",
    )
    article_summary: str = Field(default="", description="Generated article summary (truncated).")
    token_usage: dict[str, Any] = Field(
        default_factory=dict,
        description="LLM token usage statistics.",
    )

    model_config = {"extra": "allow"}


# ═══════════════════════════════════════════════════════════════
# 2. concept_build
# ═══════════════════════════════════════════════════════════════

class ConceptBuildInput(BaseModel):
    """Input for cross-article concept building."""

    article_ids: list[str] = Field(
        ..., description="List of article IDs to process.",
    )
    config_overrides: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional Hydra-style config overrides.",
    )

    model_config = {"extra": "forbid"}


class ConceptBuildOutput(BaseModel):
    """Output from concept building."""

    concepts_created: int = Field(default=0, description="Number of concepts created.")
    relations_created: int = Field(default=0, description="Number of cross-relations created.")
    concepts: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of created concept summaries.",
    )
    summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Full processing summary.",
    )

    model_config = {"extra": "allow"}


# ═══════════════════════════════════════════════════════════════
# 3. concept_expand
# ═══════════════════════════════════════════════════════════════

class ConceptExpandInput(BaseModel):
    """Input for expanding concepts with new articles."""

    concept_ids: list[str] = Field(
        ..., description="UUIDs of concepts to expand.",
    )
    article_ids: list[str] = Field(
        ..., description="Article IDs containing new keywords.",
    )
    high_threshold: float = Field(
        default=0.85, ge=0.0, le=1.0,
        description="Cosine similarity threshold for direct matches.",
    )
    low_threshold: float = Field(
        default=0.65, ge=0.0, le=1.0,
        description="Lower threshold for LLM-verified candidates.",
    )
    llm_confidence_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0,
        description="LLM confidence threshold for candidate acceptance.",
    )

    model_config = {"extra": "forbid"}


class ExpandedConceptInfo(BaseModel):
    """Summary of a single expanded concept."""

    concept_id: str
    concept_name: str
    domain: str = ""
    original_version: int = 0
    direct_keywords: list[str] = Field(default_factory=list)
    llm_keywords: list[str] = Field(default_factory=list)


class ConceptExpandOutput(BaseModel):
    """Output from concept expansion."""

    expanded_concepts: list[ExpandedConceptInfo] = Field(
        default_factory=list,
        description="List of expanded concepts with new keywords.",
    )

    model_config = {"extra": "allow"}


# ═══════════════════════════════════════════════════════════════
# 4. concept_dry_run
# ═══════════════════════════════════════════════════════════════

class ConceptDryRunInput(BaseModel):
    """Input for concept building dry run."""

    article_ids: list[str] = Field(
        ..., description="Article IDs to analyze.",
    )

    model_config = {"extra": "forbid"}


class ConceptDryRunOutput(BaseModel):
    """Output from concept building dry run."""

    articles: list[str] = Field(default_factory=list)
    article_names: dict[str, str] = Field(default_factory=dict)
    total_keywords: int = Field(default=0)
    keywords_per_article: dict[str, int] = Field(default_factory=dict)
    estimated_llm_calls: int = Field(default=0)
    unprocessed_articles: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


# ═══════════════════════════════════════════════════════════════
# 5. rag_search
# ═══════════════════════════════════════════════════════════════

class RagSearchInput(BaseModel):
    """Input for multi-source RAG search."""

    query: str = Field(
        ..., description="Search query text.",
    )
    top_k: int = Field(
        default=10, ge=1, le=100,
        description="Max results per source per query variant.",
    )
    rephrase: bool = Field(
        default=True,
        description="Whether to generate LLM-rephrased query variants.",
    )
    level: Optional[int] = Field(
        default=None,
        description="Optional RAPTOR tree level filter for chunks.",
    )

    model_config = {"extra": "forbid"}


class ChunkResultSchema(BaseModel):
    """A single RAPTOR chunk search result."""

    node_id: str
    article_id: str = ""
    level: int = 0
    text: str = ""
    score: float = 0.0
    hit_count: int = 1
    keywords: list[str] = Field(default_factory=list)


class ConceptResultSchema(BaseModel):
    """A concept search result."""

    concept_id: str
    name: str = ""
    domain: str = ""
    description: str = ""
    score: float = 0.0
    hit_count: int = 1
    keywords: list[str] = Field(default_factory=list)
    articles: list[str] = Field(default_factory=list)
    relations: list[dict[str, Any]] = Field(default_factory=list)


class RelationResultSchema(BaseModel):
    """A cross-relation search result."""

    source_name: str = ""
    target_name: str = ""
    predicate: str = ""
    description: str = ""
    score: float = 0.0
    hit_count: int = 1


class RagSearchOutput(BaseModel):
    """Output from RAG search."""

    query: str = Field(description="Original query.")
    rephrased_queries: list[str] = Field(
        default_factory=list,
        description="LLM-rephrased query variants.",
    )
    chunks: list[ChunkResultSchema] = Field(default_factory=list)
    concepts: list[ConceptResultSchema] = Field(default_factory=list)
    relations: list[RelationResultSchema] = Field(default_factory=list)

    model_config = {"extra": "allow"}

    @classmethod
    def from_retrieval_result(cls, result) -> RagSearchOutput:
        """Convert a retrieval.models.RetrievalResult to this schema."""
        return cls(
            query=result.query,
            rephrased_queries=result.rephrased_queries,
            chunks=[
                ChunkResultSchema(
                    node_id=c.node_id,
                    article_id=c.article_id,
                    level=c.level,
                    text=c.text,
                    score=c.score,
                    hit_count=c.hit_count,
                    keywords=c.keywords,
                )
                for c in result.chunks
            ],
            concepts=[
                ConceptResultSchema(
                    concept_id=c.concept_id,
                    name=c.name,
                    domain=c.domain,
                    description=c.description,
                    score=c.score,
                    hit_count=c.hit_count,
                    keywords=c.keywords,
                    articles=c.articles,
                    relations=c.relations,
                )
                for c in result.concepts
            ],
            relations=[
                RelationResultSchema(
                    source_name=r.source_name,
                    target_name=r.target_name,
                    predicate=r.predicate,
                    description=r.description,
                    score=r.score,
                    hit_count=r.hit_count,
                )
                for r in result.relations
            ],
        )


# ═══════════════════════════════════════════════════════════════
# 6. concept_inspect
# ═══════════════════════════════════════════════════════════════

class ConceptInspectInput(BaseModel):
    """Input for concept inspection."""

    concept_id: str = Field(
        ..., description="UUID of the Concept node to inspect.",
    )
    full_text: bool = Field(
        default=False,
        description="Return full chunk texts instead of truncated.",
    )

    model_config = {"extra": "forbid"}


class KeywordTraceInfo(BaseModel):
    """Provenance trace for a keyword within a concept."""

    word: str
    article_id: str = ""
    article_name: Optional[str] = None
    confidence: Optional[float] = None
    description: Optional[str] = None
    in_concept: bool = False
    similarity: Optional[float] = None
    chunks: list[dict[str, Any]] = Field(default_factory=list)


class CrossRelationInfo(BaseModel):
    """Cross-concept relationship info."""

    other_name: str = ""
    other_domain: str = ""
    predicate: str = ""
    description: str = ""
    confidence: Optional[float] = None


class ConceptInspectOutput(BaseModel):
    """Output from concept inspection."""

    concept_id: str
    canonical_name: str = ""
    domain: str = ""
    description: str = ""
    source_articles: list[str] = Field(default_factory=list)
    version: Optional[int] = None
    is_active: Optional[bool] = None
    run_id: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    keyword_traces: list[KeywordTraceInfo] = Field(default_factory=list)
    cross_relations: list[CrossRelationInfo] = Field(default_factory=list)

    model_config = {"extra": "allow"}


# ═══════════════════════════════════════════════════════════════
# 7. list_articles
# ═══════════════════════════════════════════════════════════════

class ListArticlesInput(BaseModel):
    """Input for listing indexed articles."""

    model_config = {"extra": "forbid"}


class ArticleInfo(BaseModel):
    """Summary info about an indexed article."""

    id: str
    name: str = ""
    keyword_count: int = 0
    has_summary: bool = False


class ListArticlesOutput(BaseModel):
    """Output from listing articles."""

    articles: list[ArticleInfo] = Field(default_factory=list)

    model_config = {"extra": "allow"}


# ═══════════════════════════════════════════════════════════════
# 8. list_concepts
# ═══════════════════════════════════════════════════════════════

class ListConceptsInput(BaseModel):
    """Input for listing concepts."""

    domain: Optional[str] = Field(
        default=None,
        description="Filter concepts by domain.",
    )
    article_id: Optional[str] = Field(
        default=None,
        description="Filter concepts by source article ID.",
    )

    model_config = {"extra": "forbid"}


class ConceptInfo(BaseModel):
    """Summary info about a concept."""

    id: str
    name: str = ""
    domain: str = ""
    description: str = ""
    keyword_words: list[str] = Field(default_factory=list)
    source_articles: list[str] = Field(default_factory=list)
    relations_count: int = 0
    version: int = 1
    is_active: bool = True


class ListConceptsOutput(BaseModel):
    """Output from listing concepts."""

    concepts: list[ConceptInfo] = Field(default_factory=list)

    model_config = {"extra": "allow"}


# ═══════════════════════════════════════════════════════════════
# 9. parse_document
# ═══════════════════════════════════════════════════════════════

class ParseDocumentInput(BaseModel):
    """Input for parsing a document to YAML."""

    file_path: str = Field(
        ...,
        description=(
            "Path to the source document. "
            "Supported: .md (Markdown), .html (HTML), .csv (CSV with HTML)."
        ),
    )
    output_dir: Optional[str] = Field(
        default=None,
        description="Output directory for YAML files. Default: parsed_yaml/",
    )

    model_config = {"extra": "forbid"}


class ParseDocumentOutput(BaseModel):
    """Output from document parsing."""

    yaml_path: str = Field(description="Path to the generated YAML file.")
    article_id: str = Field(default="", description="Article ID extracted from file.")
    blocks: int = Field(default=0, description="Number of document blocks parsed.")
    articles_parsed: int = Field(
        default=1,
        description="Number of articles parsed (>1 for CSV inputs).",
    )

    model_config = {"extra": "allow"}


# ═══════════════════════════════════════════════════════════════
# 10. topic_modeler
# ═══════════════════════════════════════════════════════════════

class TopicTrainInput(BaseModel):
    article_ids: list[str] = Field(default_factory=list, description="IDs of articles to train on. Empty means all.")
    config_overrides: dict[str, Any] = Field(default_factory=dict, description="Overrides for TopicModelerConfig")
    model_config = {"extra": "forbid"}

class TopicTrainOutput(BaseModel):
    topics_found: int = Field(default=0)
    docs_trained: int = Field(default=0)
    model_config = {"extra": "allow"}

class TopicPredictInput(BaseModel):
    article_path: str = Field(..., description="Path to the markdown article")
    config_overrides: dict[str, Any] = Field(default_factory=dict)
    model_config = {"extra": "forbid"}

class TopicPredictOutput(BaseModel):
    topic: str = Field(default="")
    confidence: float = Field(default=0.0)
    model_config = {"extra": "allow"}

# ═══════════════════════════════════════════════════════════════
# 11. vault_parser & vault_acl
# ═══════════════════════════════════════════════════════════════

class VaultParseInput(BaseModel):
    config_overrides: dict[str, Any] = Field(default_factory=dict)
    model_config = {"extra": "forbid"}

class VaultParseOutput(BaseModel):
    daily_count: int = Field(default=0)
    weekly_count: int = Field(default=0)
    monthly_count: int = Field(default=0)
    model_config = {"extra": "allow"}

class VaultListTasksInput(BaseModel):
    status: Optional[str] = Field(None, description="Task status (open, done, cancelled, in_progress)")
    date_range: Optional[str] = Field(None, description="today, this_week, this_month, or YYYY-MM-DD")
    person: Optional[str] = Field(None)
    priority: Optional[str] = Field(None)
    section: Optional[str] = Field(None)
    model_config = {"extra": "forbid"}

class VaultListTasksOutput(BaseModel):
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    count: int = Field(default=0)
    model_config = {"extra": "allow"}

class VaultSearchInput(BaseModel):
    query: str = Field(..., description="Query string to search tasks")
    model_config = {"extra": "forbid"}

class VaultSearchOutput(BaseModel):
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    count: int = Field(default=0)
    model_config = {"extra": "allow"}

class VaultStatsInput(BaseModel):
    model_config = {"extra": "forbid"}

class VaultStatsOutput(BaseModel):
    daily_notes: int = Field(default=0)
    open_tasks: int = Field(default=0)
    done_tasks: int = Field(default=0)
    total_tasks: int = Field(default=0)
    model_config = {"extra": "allow"}

class VaultWellnessInput(BaseModel):
    date_range: Optional[str] = Field(None)
    model_config = {"extra": "forbid"}

class VaultWellnessOutput(BaseModel):
    entries: list[dict[str, Any]] = Field(default_factory=list)
    count: int = Field(default=0)
    model_config = {"extra": "allow"}

class VaultAddTaskInput(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    text: str = Field(..., description="Task text")
    section: str = Field("main", description="Target section in daily note")
    status: str = Field("open", description="Task status")
    people: Optional[str] = Field(None, description="Comma-separated list of people")
    scheduled_date: Optional[str] = Field(None)
    due_date: Optional[str] = Field(None)
    model_config = {"extra": "forbid"}

class VaultUpdateTaskInput(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    query: str = Field(..., description="Substring matching the task to update")
    status: str = Field(..., description="New status: open, done, cancelled, in_progress")
    model_config = {"extra": "forbid"}

class VaultDeleteTaskInput(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    query: str = Field(..., description="Substring matching the task to delete")
    model_config = {"extra": "forbid"}

class VaultCreateNoteInput(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    model_config = {"extra": "forbid"}

class VaultOperationOutput(BaseModel):
    success: bool = Field(default=False)
    message: str = Field(default="")
    model_config = {"extra": "allow"}

class VaultCheckAccessInput(BaseModel):
    user: str = Field(..., description="Username or role to check")
    file_path: str = Field(..., description="Path to the file relative to vault root")
    action: str = Field("read", description="Action: read, write, update, delete")
    model_config = {"extra": "forbid"}

class VaultCheckAccessOutput(BaseModel):
    allowed: bool = Field(default=False)
    permissions: str = Field(default="")
    rules_matched: int = Field(default=0)
    model_config = {"extra": "allow"}

