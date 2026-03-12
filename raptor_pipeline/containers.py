"""DI container for RAPTOR Pipeline — with wiring, class resolution, and lazy init.

Flow:
  Click CLI → Hydra compose → pydantic validate → DI container → pipeline

Features:
  - Config-driven class replacement via _class_ field (embeddings, stores)
  - Base class validation (issubclass check)
  - Wiring: @inject + Provide[] on Click commands
  - Singleton stores, Resource (lazy) embedder
"""
from __future__ import annotations

from dependency_injector import containers, providers

from cli_base.class_resolver import resolve_class
from raptor_pipeline.schemas import RaptorPipelineConfig


def _create_embedding_provider(cfg: RaptorPipelineConfig):
    """Resolve embedding provider class from config and instantiate."""
    from interfaces import BaseEmbeddingProvider
    cls = resolve_class(cfg.embeddings.class_, BaseEmbeddingProvider)
    return cls(cfg.embeddings)


def _create_graph_store(cfg: RaptorPipelineConfig):
    """Resolve graph store class from config and instantiate."""
    from interfaces import BaseGraphStore
    cls = resolve_class(cfg.stores.neo4j.class_, BaseGraphStore)
    return cls(cfg.stores.neo4j)


def _create_vector_store(cfg: RaptorPipelineConfig):
    """Create Qdrant vector store from config."""
    from stores.vector_store import QdrantVectorStore
    return QdrantVectorStore(cfg.stores.qdrant)


def _create_chunker(cfg: RaptorPipelineConfig, embedder):
    """Create chunker based on 'type' field."""
    chunker_type = cfg.chunker.type
    if chunker_type == "semantic":
        from raptor_pipeline.chunker.semantic_chunker import SemanticChunker
        return SemanticChunker(cfg.chunker, embedder)
    elif chunker_type == "hybrid":
        from raptor_pipeline.chunker.hybrid_chunker import HybridChunker
        return HybridChunker(cfg.chunker, embedder)
    else:
        from raptor_pipeline.chunker.section_chunker import SectionChunker
        return SectionChunker(cfg.chunker)


def _create_summarizer(cfg: RaptorPipelineConfig):
    """Create LLM summarizer."""
    from raptor_pipeline.summarizer.llm_summarizer import LLMSummarizer
    return LLMSummarizer(cfg.summarizer, cfg.prompts.summarize)


def _create_kw_extractor(cfg: RaptorPipelineConfig):
    """Create keyword extractor."""
    from raptor_pipeline.knowledge_graph.keyword_extractor import LLMKeywordExtractor
    return LLMKeywordExtractor(cfg.knowledge_graph, cfg.prompts.keywords)


def _create_kw_refiner(cfg: RaptorPipelineConfig):
    """Create keyword refiner."""
    from raptor_pipeline.knowledge_graph.keyword_refiner import LLMKeywordRefiner
    return LLMKeywordRefiner(cfg.knowledge_graph, cfg.prompts.refine_keywords)


def _create_rel_extractor(cfg: RaptorPipelineConfig):
    """Create relation extractor."""
    from raptor_pipeline.knowledge_graph.relation_extractor import LLMRelationExtractor
    return LLMRelationExtractor(cfg.knowledge_graph, cfg.prompts.relations)


def _create_pipeline(cfg, embedder, chunker, summarizer,
                      kw_extractor, kw_refiner, rel_extractor,
                      vector_store, graph_store):
    """Assemble the full pipeline with all injected dependencies."""
    from raptor_pipeline.pipeline import RaptorPipeline
    return RaptorPipeline(
        cfg,
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
    Классы embedding_provider и graph_store резолвятся из _class_ в конфиге.

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
