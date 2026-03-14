"""Concept inspector — provenance tracing from Concept → Keyword → Chunks."""
from __future__ import annotations

import logging
from typing import Any

from interfaces import BaseConceptInspector

logger = logging.getLogger(__name__)


class ConceptInspector(BaseConceptInspector):
    """Inspect concepts with full tracing back to source chunks.

    Uses Neo4j for graph traversal and Qdrant for chunk texts.
    """

    def __init__(self, graph_store: Any, vector_store: Any) -> None:
        self._gs = graph_store
        self._vs = vector_store

    def inspect_concept(self, concept_id: str) -> dict:
        """Concept → Keywords → chunk_ids → chunk texts."""
        with self._gs._driver.session(database=self._gs._database) as session:
            # Get Concept info
            concept_result = session.run(
                """
                MATCH (c:Concept {id: $id})
                OPTIONAL MATCH (k:Keyword)-[:INSTANCE_OF]->(c)
                OPTIONAL MATCH (a:Article)-[:HAS_KEYWORD]->(k)
                RETURN c.canonical_name AS name,
                       c.domain AS domain,
                       c.description AS description,
                       c.source_articles AS source_articles,
                       collect(DISTINCT k.word) AS keywords,
                       collect(DISTINCT {
                           word: k.word,
                           article_id: a.id,
                           article_name: a.article_name
                       }) AS keyword_articles
                """,
                id=concept_id,
            ).single()

            if not concept_result:
                return {"error": f"Concept '{concept_id}' not found"}

            # Get cross-relations
            rels_result = session.run(
                """
                MATCH (c:Concept {id: $id})-[r:CROSS_RELATED_TO]-(other:Concept)
                RETURN other.canonical_name AS other_name,
                       other.domain AS other_domain,
                       r.predicate AS predicate,
                       r.description AS description,
                       r.confidence AS confidence,
                       type(r) = 'CROSS_RELATED_TO' AS is_outgoing
                """,
                id=concept_id,
            ).data()

        # Trace each keyword to its chunks
        keyword_traces: list[dict] = []
        keyword_articles = concept_result.get("keyword_articles", [])
        seen: set[str] = set()

        for ka in keyword_articles:
            if not ka or not ka.get("word"):
                continue
            key = f"{ka['word']}:{ka.get('article_id', '')}"
            if key in seen:
                continue
            seen.add(key)

            chunks = self.trace_keyword_to_chunks(
                ka["word"], ka.get("article_id", ""),
            )
            keyword_traces.append({
                "word": ka["word"],
                "article_id": ka.get("article_id"),
                "article_name": ka.get("article_name"),
                "chunks": chunks,
            })

        return {
            "concept_id": concept_id,
            "canonical_name": concept_result["name"],
            "domain": concept_result["domain"],
            "description": concept_result["description"],
            "source_articles": concept_result.get("source_articles", []),
            "keywords": concept_result.get("keywords", []),
            "keyword_traces": keyword_traces,
            "cross_relations": rels_result,
        }

    def trace_keyword_to_chunks(
        self, keyword_word: str, article_id: str,
    ) -> list[dict]:
        """Keyword → HAS_KEYWORD.chunk_ids → Qdrant texts."""
        # Get chunk_ids from Neo4j
        with self._gs._driver.session(database=self._gs._database) as session:
            result = session.run(
                """
                MATCH (a:Article {id: $article_id})-[r:HAS_KEYWORD]->(k:Keyword {word: $word})
                RETURN r.chunk_ids AS chunk_ids
                """,
                article_id=article_id,
                word=keyword_word,
            ).single()

            if not result or not result["chunk_ids"]:
                return []

            chunk_ids = result["chunk_ids"]

        # Retrieve chunk texts from Qdrant
        chunks: list[dict] = []
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            all_points = self._vs._client.scroll(
                collection_name=self._vs._collection,
                scroll_filter=Filter(must=[
                    FieldCondition(key="article_id", match=MatchValue(value=article_id)),
                ]),
                limit=500,
                with_payload=True,
            )[0]

            for point in all_points:
                payload = point.payload or {}
                if payload.get("node_id") in chunk_ids:
                    chunks.append({
                        "chunk_id": payload.get("node_id"),
                        "level": payload.get("level", 0),
                        "text": payload.get("text", "")[:300] + "...",
                    })
        except Exception as exc:
            logger.warning("Failed to trace chunks: %s", exc)

        return sorted(chunks, key=lambda c: c.get("level", 0), reverse=True)
