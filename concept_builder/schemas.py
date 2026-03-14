"""Pydantic configuration schemas for Concept Builder."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ConceptLLMConfig(BaseModel):
    """LLM settings for concept builder (descriptions, summaries, relations)."""
    provider: str = "llama_cpp"
    model_name: str = "gemma-3-12b-it"
    base_url: str = "http://localhost:8080/v1"
    api_key: Optional[str] = None
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(2048, ge=1)

    class Config:
        extra = "allow"


class ConceptPromptConfig(BaseModel):
    """Single prompt template."""
    template: str = ""
    version: str = "1.0"

    class Config:
        extra = "allow"


class ConceptPromptsConfig(BaseModel):
    """All prompt templates for concept builder."""
    keyword_description: ConceptPromptConfig = Field(default_factory=ConceptPromptConfig)
    concept_summary: ConceptPromptConfig = Field(default_factory=ConceptPromptConfig)
    cross_relations: ConceptPromptConfig = Field(default_factory=ConceptPromptConfig)


class ConceptQdrantConfig(BaseModel):
    """Qdrant settings for concept collections."""
    host: str = "localhost"
    port: int = Field(6333, ge=1, le=65535)
    concepts_collection: str = "concepts"
    cross_relations_collection: str = "cross_relations"
    vector_size: int = Field(768, ge=1)

    class Config:
        extra = "allow"


class ConceptNeo4jConfig(BaseModel):
    """Neo4j settings (reuse from raptor_pipeline)."""
    class_: str = Field("stores.graph_store.Neo4jGraphStore", alias="class_")
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "raptor_password"
    database: str = "neo4j"

    class Config:
        extra = "allow"
        populate_by_name = True


class ConceptEmbeddingsConfig(BaseModel):
    """Embedding settings (reuse from raptor_pipeline)."""
    class_: str = Field(
        "raptor_pipeline.embeddings.providers.HuggingFaceEmbeddingProvider",
        alias="class_",
    )
    provider: str = "huggingface"
    model_name: str = "sergeyzh/BERTA"
    local_path: Optional[str] = None
    embedding_dim: int = Field(768, ge=1)
    model_kwargs: dict = Field(default_factory=lambda: {"device": "cpu"})
    encode_kwargs: dict = Field(default_factory=lambda: {"normalize_embeddings": True})

    class Config:
        extra = "allow"
        populate_by_name = True


class ConceptStoresConfig(BaseModel):
    """Stores configuration."""
    qdrant: ConceptQdrantConfig = Field(default_factory=ConceptQdrantConfig)
    neo4j: ConceptNeo4jConfig = Field(default_factory=ConceptNeo4jConfig)


class ConceptBuilderConfig(BaseModel):
    """Root configuration for Concept Builder.

    Validated at startup.
    """
    log_level: str = "INFO"

    # Thresholds
    similarity_threshold: float = Field(
        0.85, ge=0.0, le=1.0,
        description="Cosine similarity threshold for keyword clustering",
    )
    min_keyword_confidence: float = Field(
        0.8, ge=0.0, le=1.0,
        description="Minimum keyword confidence for concept building",
    )
    max_prompt_tokens: int = Field(
        3000, ge=100,
        description="Maximum tokens in LLM prompts",
    )

    # Traversal defaults
    default_strategy: str = "bfs"
    default_max_articles: int = Field(20, ge=1)

    # Sub-configs
    llm: ConceptLLMConfig = Field(default_factory=ConceptLLMConfig)
    embeddings: ConceptEmbeddingsConfig = Field(default_factory=ConceptEmbeddingsConfig)
    prompts: ConceptPromptsConfig = Field(default_factory=ConceptPromptsConfig)
    stores: ConceptStoresConfig = Field(default_factory=ConceptStoresConfig)

    class Config:
        extra = "allow"
