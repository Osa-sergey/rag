"""DI container for Concept Builder — Hydra config → DI → processor.

Follows the same pattern as raptor_pipeline/containers.py:
  Click CLI → Hydra compose → pydantic validate → DI container → processor
"""
from __future__ import annotations

from dependency_injector import containers, providers
from omegaconf import OmegaConf, DictConfig
from pydantic import BaseModel

from cli_base.class_resolver import resolve_class
from concept_builder.schemas import ConceptBuilderConfig


def _to_dictconfig(obj) -> DictConfig:
    """Convert Pydantic model or dict to OmegaConf DictConfig."""
    if isinstance(obj, DictConfig):
        return obj
    if isinstance(obj, BaseModel):
        return OmegaConf.create(obj.model_dump(by_alias=True))
    if isinstance(obj, dict):
        return OmegaConf.create(obj)
    return obj


def _create_embedding_provider(cfg: ConceptBuilderConfig):
    """Resolve and instantiate embedding provider."""
    from interfaces import BaseEmbeddingProvider
    cls = resolve_class(cfg.embeddings.class_, BaseEmbeddingProvider)
    return cls(_to_dictconfig(cfg.embeddings))


def _create_graph_store(cfg: ConceptBuilderConfig):
    """Resolve and instantiate graph store."""
    from interfaces import BaseGraphStore
    cls = resolve_class(cfg.stores.neo4j.class_, BaseGraphStore)
    return cls(_to_dictconfig(cfg.stores.neo4j))


def _create_vector_store(cfg: ConceptBuilderConfig):
    """Create Qdrant vector store."""
    from stores.vector_store import QdrantVectorStore
    return QdrantVectorStore(_to_dictconfig(cfg.stores.qdrant))


def _create_keyword_describer(cfg: ConceptBuilderConfig, vector_store, embedder, tracker):
    """Create keyword describer."""
    from concept_builder.keyword_describer import KeywordDescriber
    return KeywordDescriber(
        _to_dictconfig(cfg.llm),
        _to_dictconfig(cfg.prompts.keyword_description),
        vector_store=vector_store,
        embedder=embedder,
        tracker=tracker,
        max_prompt_tokens=cfg.max_prompt_tokens,
    )


def _create_relation_builder(cfg: ConceptBuilderConfig, tracker):
    """Create relation builder."""
    from concept_builder.relation_builder import RelationBuilder
    return RelationBuilder(
        _to_dictconfig(cfg.llm),
        _to_dictconfig(cfg.prompts.cross_relations),
        tracker=tracker,
        max_prompt_tokens=cfg.max_prompt_tokens,
    )


def _create_article_selector(graph_store):
    """Create article selector."""
    from concept_builder.article_selector import ArticleSelector
    return ArticleSelector(graph_store)


def _create_inspector(graph_store, vector_store):
    """Create concept inspector."""
    from concept_builder.inspector import ConceptInspector
    return ConceptInspector(graph_store, vector_store)


def _create_processor(cfg, graph_store, vector_store, embedder,
                       article_selector, keyword_describer, relation_builder):
    """Assemble the full processor with all dependencies."""
    from concept_builder.processor import CrossArticleProcessor
    return CrossArticleProcessor(
        _to_dictconfig(cfg),
        graph_store=graph_store,
        vector_store=vector_store,
        embedder=embedder,
        article_selector=article_selector,
        keyword_describer=keyword_describer,
        relation_builder=relation_builder,
    )


class ConceptBuilderContainer(containers.DeclarativeContainer):
    """DI container for Concept Builder.

    Usage::

        container = ConceptBuilderContainer(config=validated_cfg)
        container.wire(modules=[concept_builder.__main__])
        processor = container.processor()
    """

    config = providers.Dependency(instance_of=ConceptBuilderConfig)

    # Token tracker (shared)
    token_tracker = providers.Singleton(
        lambda: __import__('raptor_pipeline.token_tracker', fromlist=['TokenTracker']).TokenTracker()
    )

    # ── Embedding Provider ────────────────────────────────────
    embedding_provider = providers.Resource(
        _create_embedding_provider, cfg=config,
    )

    # ── Stores ────────────────────────────────────────────────
    graph_store = providers.Singleton(
        _create_graph_store, cfg=config,
    )
    vector_store = providers.Singleton(
        _create_vector_store, cfg=config,
    )

    # ── Components ────────────────────────────────────────────
    article_selector = providers.Factory(
        _create_article_selector,
        graph_store=graph_store,
    )
    keyword_describer = providers.Factory(
        _create_keyword_describer,
        cfg=config,
        vector_store=vector_store,
        embedder=embedding_provider,
        tracker=token_tracker,
    )
    relation_builder = providers.Factory(
        _create_relation_builder,
        cfg=config,
        tracker=token_tracker,
    )
    inspector = providers.Factory(
        _create_inspector,
        graph_store=graph_store,
        vector_store=vector_store,
    )

    # ── Processor (full pipeline) ─────────────────────────────
    processor = providers.Factory(
        _create_processor,
        cfg=config,
        graph_store=graph_store,
        vector_store=vector_store,
        embedder=embedding_provider,
        article_selector=article_selector,
        keyword_describer=keyword_describer,
        relation_builder=relation_builder,
    )
