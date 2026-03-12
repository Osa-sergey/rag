"""Qdrant vector store wrapper with rich metadata payloads."""
from __future__ import annotations

import logging
from typing import Any

from omegaconf import DictConfig
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)

from raptor_pipeline.raptor.tree_builder import RaptorNode

from interfaces import BaseVectorStore

logger = logging.getLogger(__name__)


class QdrantVectorStore(BaseVectorStore):
    """Qdrant integration — stores RAPTOR nodes with metadata payloads.

    Every point has a payload containing:
      - article_id,  level,  block_ids,  keywords
    which enables filtered search by article, tree level, etc.
    """

    def __init__(self, cfg: DictConfig) -> None:
        self._client = QdrantClient(
            host=cfg.get("host", "localhost"),
            port=cfg.get("port", 6333),
        )
        self._collection = cfg.get("collection_name", "raptor_chunks")
        self._vector_size = cfg.get("vector_size", 1536)
        logger.info(
            "QdrantVectorStore connected (%s:%s, collection=%s)",
            cfg.get("host"),
            cfg.get("port"),
            self._collection,
        )

    # ------------------------------------------------------------------
    def ensure_collection(self) -> None:
        """Create collection if it does not exist or has wrong dimension."""
        collections = {
            c.name: c for c in self._client.get_collections().collections
        }
        
        recreate = False
        if self._collection in collections:
            # Check dimension of the existing collection
            info = self._client.get_collection(self._collection)
            # info.config.params.vectors can be VectorParams or dict
            vectors_config = info.config.params.vectors
            
            existing_size = None
            if hasattr(vectors_config, 'size'):
                existing_size = vectors_config.size
            elif isinstance(vectors_config, dict) and 'size' in vectors_config:
                existing_size = vectors_config['size']
            
            if existing_size is not None and existing_size != self._vector_size:
                logger.warning(
                    "Collection '%s' has dimension %d, but config expects %d. Recreating...",
                    self._collection, existing_size, self._vector_size
                )
                self._client.delete_collection(self._collection)
                recreate = True
            else:
                logger.info(
                    "Collection '%s' already exists with matching dimension (%d)", 
                    self._collection, existing_size if existing_size else "?"
                )

        if self._collection not in collections or recreate:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created collection '%s' (dim=%d)", self._collection, self._vector_size)

    # ------------------------------------------------------------------
    def upsert_nodes(
        self,
        nodes: list[RaptorNode],
        keywords_map: dict[str, list[str]] | None = None,
    ) -> None:
        """Upsert RAPTOR nodes into Qdrant.

        Args:
            nodes: List of RaptorNode objects (must have embeddings).
            keywords_map: Optional mapping node_id → list of keyword strings
                          for payload enrichment.
        """
        if not nodes:
            return

        keywords_map = keywords_map or {}
        points = []
        for node in nodes:
            payload: dict[str, Any] = {
                "node_id": node.node_id,
                "article_id": node.article_id,
                "level": node.level,
                "text": node.text,
                "children_ids": node.children_ids,
                **node.metadata,
            }
            if node.node_id in keywords_map:
                payload["keywords"] = keywords_map[node.node_id]

            points.append(
                PointStruct(
                    id=hash(node.node_id) % (2**63),
                    vector=node.embedding,
                    payload=payload,
                )
            )

        self._client.upsert(
            collection_name=self._collection,
            points=points,
        )
        logger.info("Upserted %d points into '%s'", len(points), self._collection)

    # ------------------------------------------------------------------
    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        level: int | None = None,
        article_id: str | None = None,
    ) -> list[dict]:
        """Search similar vectors with optional metadata filtering.

        Args:
            query_vector: Query embedding.
            top_k: Number of results.
            level: Optional RAPTOR tree level filter.
            article_id: Optional article filter.
        """
        conditions = []
        if level is not None:
            conditions.append(
                FieldCondition(key="level", match=MatchValue(value=level))
            )
        if article_id is not None:
            conditions.append(
                FieldCondition(
                    key="article_id",
                    match=MatchValue(value=article_id),
                )
            )

        query_filter = Filter(must=conditions) if conditions else None

        results = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )
        return [
            {"id": r.id, "score": r.score, "payload": r.payload}
            for r in results.points
        ]
