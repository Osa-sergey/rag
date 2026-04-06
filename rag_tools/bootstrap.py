"""Shared dependency bootstrap for RAG tools.

Reuses existing DI containers from raptor_pipeline and concept_builder
to initialise stores, embedders, and pipeline objects lazily.
"""
from __future__ import annotations

import logging
from functools import cached_property
from pathlib import Path
from typing import Any

from omegaconf import OmegaConf, DictConfig

logger = logging.getLogger(__name__)

# Default config paths (relative to repo root).
_RAPTOR_CONFIG = Path(__file__).resolve().parent.parent / "raptor_pipeline" / "conf"
_CONCEPT_CONFIG = Path(__file__).resolve().parent.parent / "concept_builder" / "conf"
_RETRIEVAL_CONFIG = Path(__file__).resolve().parent.parent / "retrieval" / "conf"


def _load_yaml_config(config_dir: Path, name: str = "config") -> DictConfig:
    """Load a YAML config from *config_dir*/*name*.yaml."""
    cfg_path = config_dir / f"{name}.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config not found: {cfg_path}")
    return OmegaConf.load(cfg_path)


def _apply_overrides(cfg: DictConfig, overrides: dict[str, Any]) -> DictConfig:
    """Merge dot-list overrides into a config."""
    if not overrides:
        return cfg
    override_cfg = OmegaConf.from_dotlist(
        [f"{k}={v}" for k, v in overrides.items()],
    )
    return OmegaConf.merge(cfg, override_cfg)


class ToolContext:
    """Holds initialised dependencies for tool execution.

    All heavy objects are created lazily via `cached_property` — stores
    are only initialised when the first tool that needs them is called.

    Args:
        raptor_config_dir:  Path to raptor_pipeline/conf/
        concept_config_dir: Path to concept_builder/conf/
        retrieval_config_dir: Path to retrieval/conf/
    """

    def __init__(
        self,
        raptor_config_dir: Path | str | None = None,
        concept_config_dir: Path | str | None = None,
        retrieval_config_dir: Path | str | None = None,
    ) -> None:
        self._raptor_cfg_dir = Path(raptor_config_dir) if raptor_config_dir else _RAPTOR_CONFIG
        self._concept_cfg_dir = Path(concept_config_dir) if concept_config_dir else _CONCEPT_CONFIG
        self._retrieval_cfg_dir = Path(retrieval_config_dir) if retrieval_config_dir else _RETRIEVAL_CONFIG

    # ── Raw configs ──────────────────────────────────────────

    @cached_property
    def raptor_cfg(self) -> DictConfig:
        return _load_yaml_config(self._raptor_cfg_dir)

    @cached_property
    def concept_cfg(self) -> DictConfig:
        return _load_yaml_config(self._concept_cfg_dir)

    @cached_property
    def retrieval_cfg(self) -> DictConfig:
        return _load_yaml_config(self._retrieval_cfg_dir)

    # ── Shared components ────────────────────────────────────

    @cached_property
    def embedder(self):
        from raptor_pipeline.embeddings.providers import create_embedding_provider
        cfg = self.raptor_cfg.get("embeddings", self.retrieval_cfg.get("embeddings"))
        return create_embedding_provider(cfg)

    @cached_property
    def graph_store(self):
        from cli_base.class_resolver import resolve_class
        from interfaces import BaseGraphStore
        cfg = self.raptor_cfg.stores.neo4j
        gs_cls = resolve_class(
            cfg.get("_class_", "stores.graph_store.Neo4jGraphStore"),
            BaseGraphStore,
        )
        return gs_cls(cfg)

    @cached_property
    def vector_store(self):
        from cli_base.class_resolver import resolve_class
        from interfaces import BaseVectorStore
        cfg = self.raptor_cfg.stores.qdrant
        vs_cls = resolve_class(
            cfg.get("_class_", "stores.vector_store.QdrantVectorStore"),
            BaseVectorStore,
        )
        return vs_cls(cfg)

    # ── Cached default pipelines ─────────────────────────────

    @cached_property
    def raptor_pipeline(self):
        from raptor_pipeline.pipeline import RaptorPipeline
        pipeline = RaptorPipeline(
            self.raptor_cfg,
            embedder=self.embedder,
            vector_store=self.vector_store,
            graph_store=self.graph_store,
        )
        pipeline.init_stores()
        return pipeline

    @cached_property
    def concept_processor(self):
        from concept_builder.processor import CrossArticleProcessor
        return CrossArticleProcessor(
            self.concept_cfg,
            graph_store=self.graph_store,
            vector_store=self.vector_store,
            embedder=self.embedder,
        )

    @cached_property
    def concept_inspector(self):
        from concept_builder.inspector import ConceptInspector
        return ConceptInspector(self.graph_store, self.vector_store)

    @cached_property
    def retriever(self):
        from retrieval.retriever import MultiSourceRetriever
        return MultiSourceRetriever(
            self.retrieval_cfg,
            embedder=self.embedder,
            graph_store=self.graph_store,
        )

    # ── Per-call factories (with config overrides) ─────────────

    def build_raptor_pipeline(self, overrides: dict[str, Any] | None = None):
        """Create a RaptorPipeline with optional config overrides.

        Reuses shared stores and embedder (connections are expensive),
        but applies *overrides* to the pipeline config — so LLM provider,
        temperatures, keyword counts, etc. can be changed per call.

        If *overrides* is empty / None, returns the cached default pipeline.
        """
        if not overrides:
            return self.raptor_pipeline

        from raptor_pipeline.pipeline import RaptorPipeline
        cfg = _apply_overrides(self.raptor_cfg.copy(), overrides)
        pipeline = RaptorPipeline(
            cfg,
            embedder=self.embedder,
            vector_store=self.vector_store,
            graph_store=self.graph_store,
        )
        pipeline.init_stores()
        return pipeline

    def build_concept_processor(self, overrides: dict[str, Any] | None = None):
        """Create a CrossArticleProcessor with optional config overrides."""
        if not overrides:
            return self.concept_processor

        from concept_builder.processor import CrossArticleProcessor
        cfg = _apply_overrides(self.concept_cfg.copy(), overrides)
        return CrossArticleProcessor(
            cfg,
            graph_store=self.graph_store,
            vector_store=self.vector_store,
            embedder=self.embedder,
        )

    def build_retriever(self, overrides: dict[str, Any] | None = None):
        """Create a MultiSourceRetriever with optional config overrides."""
        if not overrides:
            return self.retriever

        from retrieval.retriever import MultiSourceRetriever
        cfg = _apply_overrides(self.retrieval_cfg.copy(), overrides)
        return MultiSourceRetriever(
            cfg,
            embedder=self.embedder,
            graph_store=self.graph_store,
        )

    # ── Lifecycle ────────────────────────────────────────────

    def close(self) -> None:
        """Release store connections if they were initialised."""
        if "graph_store" in self.__dict__:
            self.graph_store.close()
        if "vector_store" in self.__dict__ and hasattr(self.vector_store, "close"):
            self.vector_store.close()
        logger.info("ToolContext closed")
