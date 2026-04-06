"""DSL steps for the Retrieval module."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from dagster_dsl.steps import register_step
from retrieval.schemas import RetrievalConfig

log = logging.getLogger(__name__)

# Config directory for Hydra
_CONFIG_DIR = str(Path(__file__).parent.parent.parent / "retrieval" / "conf")


@register_step(
    "retrieval.search",
    description="Multi-source RAG search across RAPTOR chunks, concepts, and relations",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=RetrievalConfig,
    tags={"module": "retrieval", "type": "search"},
)
def search(cfg: Any) -> dict[str, Any]:
    """Execute a multi-source retrieval search."""
    query = getattr(cfg, "query", None)
    if not query:
        raise ValueError("query is required for retrieval.search")

    top_k = getattr(cfg, "top_k", 10)
    rephrase = getattr(cfg, "rephrase", True)
    level = getattr(cfg, "level", None)

    # Build dependencies
    from raptor_pipeline.embeddings.providers import create_embedding_provider
    from cli_base.class_resolver import resolve_class
    from interfaces import BaseGraphStore
    from retrieval.retriever import MultiSourceRetriever

    embedder = create_embedding_provider(cfg.embeddings)
    
    gs_cls = resolve_class(
        cfg.stores.neo4j.get("_class_", "stores.graph_store.Neo4jGraphStore"),
        BaseGraphStore,
    )
    gs = gs_cls(cfg.stores.neo4j)

    retriever = MultiSourceRetriever(
        cfg, embedder=embedder, graph_store=gs,
    )

    try:
        log.info("Running retrieval search for query: '%s'", query)
        result = retriever.search(
            query, top_k=top_k, rephrase=rephrase, level=level,
        )
        
        # Serialize RetrievalResult to dict for pipeline outputs
        out = {
            "query": result.query,
            "rephrased_queries": result.rephrased_queries,
            "chunks": [c.model_dump() for c in getattr(result, "chunks", [])],
            "concepts": [c.model_dump() for c in getattr(result, "concepts", [])],
            "relations": [r.model_dump() for r in getattr(result, "relations", [])],
        }
        return out
    finally:
        gs.close()
