"""DI container for Topic Modeler — with wiring, class resolution, and partial init.

Поток данных:
  Click CLI → Hydra compose → pydantic validate → DI container → services

Features:
  - Config-driven class replacement via _class_ field
  - Base class validation (issubclass check)
  - Wiring: @inject + Provide[] on Click commands
  - Resource provider for lazy init (heavy ML models)
  - Partial init: topic_modeler_partial — without graph_store (for validate/preview)
"""
from __future__ import annotations

from dependency_injector import containers, providers

from cli_base.class_resolver import resolve_class
from topic_modeler.schemas import TopicModelerConfig


def _create_graph_store(cfg: TopicModelerConfig):
    """Resolve graph store class from config and instantiate."""
    from interfaces import BaseGraphStore
    gs_cfg = cfg.stores.graph_store
    cls = resolve_class(gs_cfg.class_, BaseGraphStore)
    return cls(gs_cfg)


def _create_embedding_provider(cfg: TopicModelerConfig):
    """Resolve embedding provider class from config and instantiate.

    Uses Resource pattern — lazy init, created only on first access.
    """
    from interfaces import BaseEmbeddingProvider
    emb_cfg = cfg.embeddings
    cls = resolve_class(emb_cfg.class_, BaseEmbeddingProvider)
    return cls(emb_cfg)


def _create_modeler(cfg, graph_store, embedder):
    """Create TopicModeler with injected dependencies."""
    from topic_modeler.modeler import TopicModeler
    return TopicModeler(cfg, embedder=embedder, graph_store=graph_store)


def _create_modeler_partial(cfg, embedder):
    """Create TopicModeler without graph_store (partial init for preview/dry-run)."""
    from topic_modeler.modeler import TopicModeler
    return TopicModeler(cfg, embedder=embedder, graph_store=None)


class TopicModelerContainer(containers.DeclarativeContainer):
    """DI-контейнер для Topic Modeler.

    Принимает провалидированный TopicModelerConfig (pydantic).
    Классы graph_store и embedding_provider резолвятся из _class_ в конфиге.

    Usage:
        container = TopicModelerContainer(config=validated_cfg)
        container.wire(modules=[topic_modeler.__main__])
        modeler = container.topic_modeler()
    """

    # Провалидированный pydantic конфиг
    config = providers.Dependency(instance_of=TopicModelerConfig)

    # ── Graph Store (Singleton, class from config) ────────────
    # _class_: stores.graph_store.Neo4jGraphStore
    # Validated: issubclass(cls, BaseGraphStore)
    graph_store = providers.Singleton(
        _create_graph_store,
        cfg=config,
    )

    # ── Embedding Provider (Resource = lazy Singleton) ────────
    # _class_: raptor_pipeline.embeddings.providers.HuggingFaceEmbeddingProvider
    # Validated: issubclass(cls, BaseEmbeddingProvider)
    # Resource — модель НЕ загружается до первого вызова
    embedding_provider = providers.Resource(
        _create_embedding_provider,
        cfg=config,
    )

    # ── Topic Modeler (Factory, full — with all deps) ─────────
    topic_modeler = providers.Factory(
        _create_modeler,
        cfg=config,
        graph_store=graph_store,
        embedder=embedding_provider,
    )

    # ── Topic Modeler (Factory, partial — БЕЗ graph_store) ────
    # Для сценариев preview / dry-run / тестирования эмбеддингов
    topic_modeler_partial = providers.Factory(
        _create_modeler_partial,
        cfg=config,
        embedder=embedding_provider,
    )
