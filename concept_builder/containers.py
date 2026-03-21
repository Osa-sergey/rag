"""DI container for Concept Builder — Hydra config → DI → processor.

Follows the same pattern as raptor_pipeline/containers.py:
  Click CLI → Hydra compose → pydantic validate → DI container → processor
"""
from __future__ import annotations

from dependency_injector import containers, providers

from cli_base.class_resolver import resolve_class
from cli_base.config_utils import to_dictconfig
from interfaces import BaseConceptClusterer
from concept_builder.schemas import ConceptBuilderConfig


def _create_embedding_provider(cfg: ConceptBuilderConfig):
    """Resolve and instantiate embedding provider."""
    from interfaces import BaseEmbeddingProvider
    cls = resolve_class(cfg.embeddings.class_, BaseEmbeddingProvider)
    return cls(to_dictconfig(cfg.embeddings))


def _create_graph_store(cfg: ConceptBuilderConfig):
    """Resolve and instantiate graph store."""
    from interfaces import BaseGraphStore
    cls = resolve_class(cfg.stores.neo4j.class_, BaseGraphStore)
    return cls(to_dictconfig(cfg.stores.neo4j))


def _create_vector_store(cfg: ConceptBuilderConfig):
    """Resolve and instantiate vector store."""
    from interfaces import BaseVectorStore
    cls = resolve_class(cfg.stores.qdrant.class_, BaseVectorStore)
    return cls(to_dictconfig(cfg.stores.qdrant))


def _create_keyword_describer(cfg: ConceptBuilderConfig, vector_store, embedder, tracker):
    """Resolve and instantiate keyword describer."""
    from interfaces import BaseKeywordDescriber
    cls = resolve_class(cfg.keyword_describer_class, BaseKeywordDescriber)
    return cls(
        to_dictconfig(cfg.llm),
        to_dictconfig(cfg.prompts.keyword_description),
        vector_store=vector_store,
        embedder=embedder,
        tracker=tracker,
        max_prompt_tokens=cfg.max_prompt_tokens,
    )


def _create_relation_builder(cfg: ConceptBuilderConfig, tracker):
    """Create relation builder."""
    from concept_builder.relation_builder import RelationBuilder
    return RelationBuilder(
        to_dictconfig(cfg.llm),
        to_dictconfig(cfg.prompts.cross_relations),
        tracker=tracker,
        max_prompt_tokens=cfg.max_prompt_tokens,
    )


def _create_article_selector(cfg: ConceptBuilderConfig, graph_store):
    """Resolve and instantiate article selector."""
    from interfaces import BaseArticleSelector
    cls = resolve_class(cfg.article_selector_class, BaseArticleSelector)
    return cls(graph_store)


def _create_inspector(cfg: ConceptBuilderConfig, graph_store, vector_store):
    """Resolve and instantiate concept inspector."""
    from interfaces import BaseConceptInspector
    cls = resolve_class(cfg.inspector_class, BaseConceptInspector)
    return cls(graph_store, vector_store)


def _create_concept_clusterer(cfg: ConceptBuilderConfig):
    """Resolve and instantiate concept clusterer."""
    cls = resolve_class(cfg.clustering.class_, BaseConceptClusterer)
    # GreedyConceptClusterer takes no args, HdbscanConceptClusterer takes kwargs
    import inspect
    sig = inspect.signature(cls.__init__)
    params = {k: v for k, v in cfg.clustering.model_dump().items()
              if k in sig.parameters and k != "self" and k != "class_"}
    return cls(**params)


def _create_processor(cfg, graph_store, vector_store, embedder,
                       article_selector, keyword_describer,
                       concept_clusterer, relation_builder):
    """Assemble the full processor with all dependencies."""
    from concept_builder.processor import CrossArticleProcessor
    return CrossArticleProcessor(
        to_dictconfig(cfg),
        graph_store=graph_store,
        vector_store=vector_store,
        embedder=embedder,
        article_selector=article_selector,
        keyword_describer=keyword_describer,
        concept_clusterer=concept_clusterer,
        relation_builder=relation_builder,
    )


class ConceptBuilderContainer(containers.DeclarativeContainer):
    """DI container for Concept Builder.

    All components are resolved from _class_ in config via resolve_class.

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
        cfg=config,
        graph_store=graph_store,
    )
    keyword_describer = providers.Factory(
        _create_keyword_describer,
        cfg=config,
        vector_store=vector_store,
        embedder=embedding_provider,
        tracker=token_tracker,
    )
    concept_clusterer = providers.Singleton(
        _create_concept_clusterer,
        cfg=config,
    )
    relation_builder = providers.Factory(
        _create_relation_builder,
        cfg=config,
        tracker=token_tracker,
    )
    inspector = providers.Factory(
        _create_inspector,
        cfg=config,
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
        concept_clusterer=concept_clusterer,
        relation_builder=relation_builder,
    )
