"""Pydantic configuration schemas for RAPTOR Pipeline.

Validates all parameters at startup so errors are caught before
expensive LLM / embedding calls begin.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enums ─────────────────────────────────────────────────────

class ChunkerType(str, Enum):
    section = "section"
    semantic = "semantic"
    hybrid = "hybrid"


class LLMProvider(str, Enum):
    deepseek = "deepseek"
    ollama = "ollama"
    llama_cpp = "llama_cpp"


class EmbeddingProviderType(str, Enum):
    deepseek = "deepseek"
    ollama = "ollama"
    huggingface = "huggingface"


# ── Sub-configs ───────────────────────────────────────────────

class ChunkerConfig(BaseModel):
    """Chunker configuration."""
    type: ChunkerType = ChunkerType.hybrid
    max_chunk_chars: int = Field(2000, ge=100, le=50_000, description="Максимальная длина чанка")
    min_chunk_chars: int = Field(200, ge=0, description="Минимальная длина чанка")
    target_chunk_chars: int = Field(800, ge=100, description="Целевая длина чанка")
    overlap_chars: int = Field(100, ge=0, description="Перекрытие при разбиении")
    similarity_threshold: float = Field(0.6, ge=0.0, le=1.0, description="Порог семантической схожести")

    class Config:
        extra = "allow"


class EmbeddingsConfig(BaseModel):
    """Embedding provider configuration."""
    class_: str = Field(
        "raptor_pipeline.embeddings.providers.HuggingFaceEmbeddingProvider",
        alias="class_",
        description="Dotted path to embedding provider class",
    )
    provider: EmbeddingProviderType = EmbeddingProviderType.huggingface
    model_name: str = "sergeyzh/BERTA"
    local_path: Optional[str] = None
    embedding_dim: int = Field(768, ge=1, description="Размерность вектора")
    model_kwargs: dict[str, Any] = Field(default_factory=lambda: {"device": "cpu"})
    encode_kwargs: dict[str, Any] = Field(default_factory=lambda: {"normalize_embeddings": True})

    class Config:
        extra = "allow"
        populate_by_name = True


class SummarizerConfig(BaseModel):
    """Summarizer configuration."""
    provider: LLMProvider = LLMProvider.llama_cpp
    model_name: str = "gemma-3-12b-it"
    base_url: str = "http://localhost:8080/v1"
    api_key: Optional[str] = None
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(2048, ge=1)

    class Config:
        extra = "allow"


class KnowledgeGraphConfig(BaseModel):
    """Knowledge graph extractor configuration."""
    provider: LLMProvider = LLMProvider.llama_cpp
    model_name: str = "gemma-3-12b-it"
    base_url: str = "http://localhost:8080/v1"
    api_key: Optional[str] = None
    temperature: float = Field(0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(2048, ge=1)
    max_keywords: int = Field(5, ge=1, le=100)
    max_relations: int = Field(10, ge=1, le=200)
    confidence_threshold: float = Field(0.8, ge=0.0, le=1.0)

    class Config:
        extra = "allow"


class RaptorConfig(BaseModel):
    """RAPTOR tree builder configuration."""
    max_levels: int = Field(3, ge=1, le=10, description="Макс. глубина дерева")
    min_cluster_size: int = Field(3, ge=2, description="Мин. размер кластера")
    reduction_factor: float = Field(0.5, ge=0.1, le=1.0, description="Коэффициент редукции")
    clustering_threshold: float = Field(0.1, ge=0.0, le=1.0, description="Порог BIC")


class PromptConfig(BaseModel):
    """Single prompt template."""
    template: str = ""
    version: str = "1.0"

    class Config:
        extra = "allow"


class PromptsConfig(BaseModel):
    """All prompt templates."""
    summarize: PromptConfig = Field(default_factory=PromptConfig)
    keywords: PromptConfig = Field(default_factory=PromptConfig)
    refine_keywords: PromptConfig = Field(default_factory=PromptConfig)
    relations: PromptConfig = Field(default_factory=PromptConfig)


class QdrantStoreConfig(BaseModel):
    """Qdrant vector store configuration."""
    host: str = "localhost"
    port: int = Field(6333, ge=1, le=65535)
    collection_name: str = "raptor_chunks"
    vector_size: int = Field(768, ge=1)

    class Config:
        extra = "allow"


class Neo4jStoreConfig(BaseModel):
    """Neo4j graph store configuration."""
    class_: str = Field("stores.graph_store.Neo4jGraphStore", alias="class_")
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "raptor_password"
    database: str = "neo4j"

    class Config:
        extra = "allow"
        populate_by_name = True


class StoresConfig(BaseModel):
    """Stores configuration."""
    qdrant: QdrantStoreConfig = Field(default_factory=QdrantStoreConfig)
    neo4j: Neo4jStoreConfig = Field(default_factory=Neo4jStoreConfig)


# ── Root config ───────────────────────────────────────────────

class RaptorPipelineConfig(BaseModel):
    """Root configuration for RAPTOR pipeline.

    Validated at startup; all sub-configs are expanded from
    Hydra defaults composition.
    """

    input_dir: str = "parsed_yaml"
    input_file: Optional[str] = None
    log_level: str = "DEBUG"
    max_concurrency: int = Field(2, ge=1, le=64, description="Потоки для LLM")
    batch_size: int = Field(16, ge=1, le=256, description="Размер батча")
    full_text: bool = False
    article_id: Optional[str] = None
    word: Optional[str] = None

    # Sub-configs
    chunker: ChunkerConfig = Field(default_factory=ChunkerConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    summarizer: SummarizerConfig = Field(default_factory=SummarizerConfig)
    knowledge_graph: KnowledgeGraphConfig = Field(default_factory=KnowledgeGraphConfig)
    raptor: RaptorConfig = Field(default_factory=RaptorConfig)
    prompts: PromptsConfig = Field(default_factory=PromptsConfig)
    stores: StoresConfig = Field(default_factory=StoresConfig)

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"log_level must be one of {valid}, got '{v}'")
        return v.upper()

    class Config:
        extra = "allow"
