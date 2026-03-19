"""DI container for RAPTOR Pipeline — with wiring, class resolution, and lazy init.

Flow:
  Click CLI → Hydra compose → pydantic validate → DI container → pipeline

Features:
  - Config-driven class replacement via _class_ field (all components)
  - Base class validation (issubclass check)
  - Wiring: @inject + Provide[] on Click commands
  - Singleton stores, Resource (lazy) embedder
"""
from __future__ import annotations

from dependency_injector import containers, providers

from cli_base.class_resolver import resolve_class
from cli_base.config_utils import to_dictconfig
from raptor_pipeline.schemas import RaptorPipelineConfig


def _create_embedding_provider(cfg: RaptorPipelineConfig):
    """Resolve embedding provider class from config and instantiate."""
    from interfaces import BaseEmbeddingProvider
    cls = resolve_class(cfg.embeddings.class_, BaseEmbeddingProvider)
    return cls(to_dictconfig(cfg.embeddings))


def _create_graph_store(cfg: RaptorPipelineConfig):
    """Resolve graph store class from config and instantiate."""
    from interfaces import BaseGraphStore
    cls = resolve_class(cfg.stores.neo4j.class_, BaseGraphStore)
    return cls(to_dictconfig(cfg.stores.neo4j))


def _create_vector_store(cfg: RaptorPipelineConfig):
    """Resolve vector store class from config and instantiate."""
    from interfaces import BaseVectorStore
    cls = resolve_class(cfg.stores.qdrant.class_, BaseVectorStore)
    return cls(to_dictconfig(cfg.stores.qdrant))


def _create_chunker(cfg: RaptorPipelineConfig, embedder):
    """Resolve chunker class from _class_ and instantiate."""
    from interfaces import BaseChunker
    cls = resolve_class(cfg.chunker.class_, BaseChunker)
    return cls(to_dictconfig(cfg.chunker), embedding_provider=embedder)


def _create_summarizer(cfg: RaptorPipelineConfig):
    """Resolve summarizer class from config and instantiate."""
    from interfaces import BaseSummarizer
    cls = resolve_class(cfg.summarizer.class_, BaseSummarizer)
    return cls(to_dictconfig(cfg.summarizer), to_dictconfig(cfg.prompts.summarize))


def _create_kw_extractor(cfg: RaptorPipelineConfig):
    """Resolve keyword extractor class from config and instantiate."""
    from interfaces import BaseKeywordExtractor
    cls = resolve_class(cfg.knowledge_graph.kw_extractor_class, BaseKeywordExtractor)
    return cls(to_dictconfig(cfg.knowledge_graph), to_dictconfig(cfg.prompts.keywords))


def _create_kw_refiner(cfg: RaptorPipelineConfig):
    """Resolve keyword refiner class from config and instantiate."""
    from interfaces import BaseKeywordRefiner
    cls = resolve_class(cfg.knowledge_graph.kw_refiner_class, BaseKeywordRefiner)
    return cls(to_dictconfig(cfg.knowledge_graph), to_dictconfig(cfg.prompts.refine_keywords))


def _create_rel_extractor(cfg: RaptorPipelineConfig):
    """Resolve relation extractor class from config and instantiate."""
    from interfaces import BaseRelationExtractor
    cls = resolve_class(cfg.knowledge_graph.rel_extractor_class, BaseRelationExtractor)
    return cls(to_dictconfig(cfg.knowledge_graph), to_dictconfig(cfg.prompts.relations))


def _create_pipeline(cfg, embedder, chunker, summarizer,
                      kw_extractor, kw_refiner, rel_extractor,
                      vector_store, graph_store):
    """Assemble the full pipeline with all injected dependencies."""
    from raptor_pipeline.pipeline import RaptorPipeline
    return RaptorPipeline(
        to_dictconfig(cfg),
        embedder=embedder,
        chunker=chunker,
        summarizer=summarizer,
        kw_extractor=kw_extractor,
        kw_refiner=kw_refiner,
        rel_extractor=rel_extractor,
        vector_store=vector_store,
        graph_store=graph_store,
    )


class RaptorPipelineContainer(containers.DeclarativeContainer):
    """DI-контейнер для RAPTOR Pipeline.

    Принимает провалидированный RaptorPipelineConfig (pydantic).
    Все компоненты резолвятся из _class_ в конфиге через resolve_class.

    Usage::

        container = RaptorPipelineContainer(config=validated_cfg)
        container.wire(modules=[raptor_pipeline.__main__])
        pipeline = container.pipeline()
    """

    config = providers.Dependency(instance_of=RaptorPipelineConfig)

    # ── Embedding Provider (Resource = lazy Singleton) ────────
    embedding_provider = providers.Resource(
        _create_embedding_provider, cfg=config,
    )

    # ── Stores (Singleton) ────────────────────────────────────
    vector_store = providers.Singleton(
        _create_vector_store, cfg=config,
    )
    graph_store = providers.Singleton(
        _create_graph_store, cfg=config,
    )

    # ── Chunker ───────────────────────────────────────────────
    chunker = providers.Factory(
        _create_chunker, cfg=config, embedder=embedding_provider,
    )

    # ── LLM components (Factory — stateless) ──────────────────
    summarizer = providers.Factory(
        _create_summarizer, cfg=config,
    )
    kw_extractor = providers.Factory(
        _create_kw_extractor, cfg=config,
    )
    kw_refiner = providers.Factory(
        _create_kw_refiner, cfg=config,
    )
    rel_extractor = providers.Factory(
        _create_rel_extractor, cfg=config,
    )

    # ── Pipeline (Factory, full) ──────────────────────────────
    pipeline = providers.Factory(
        _create_pipeline,
        cfg=config,
        embedder=embedding_provider,
        chunker=chunker,
        summarizer=summarizer,
        kw_extractor=kw_extractor,
        kw_refiner=kw_refiner,
        rel_extractor=rel_extractor,
        vector_store=vector_store,
        graph_store=graph_store,
    )
