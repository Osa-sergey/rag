"""Concept inspector — provenance tracing from Concept → Keyword → Chunks."""
from __future__ import annotations

import json
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

    def inspect_concept(self, concept_id: str, full_text: bool = False) -> dict:
        """Concept → Keywords → chunk_ids → chunk texts.

        Args:
            concept_id: UUID of the Concept node.
            full_text: If True, return full chunk texts instead of truncated.
        """
        with self._gs._driver.session(database=self._gs._database) as session:
            # Get Concept info + INSTANCE_OF article_similarities
            concept_result = session.run(
                """
                MATCH (c:Concept {id: $id})
                OPTIONAL MATCH (k:Keyword)-[io:INSTANCE_OF]->(c)
                RETURN c.canonical_name AS name,
                       c.domain AS domain,
                       c.description AS description,
                       c.source_articles AS source_articles,
                       c.run_id AS run_id,
                       c.version AS version,
                       c.is_active AS is_active,
                       collect(DISTINCT {
                           word: k.word,
                           article_similarities: io.article_similarities
                       }) AS keyword_instances
                """,
                id=concept_id,
            ).single()

            if not concept_result:
                return {"error": f"Concept '{concept_id}' not found"}

            # Parse keyword_instances into a map: word → {article_id: similarity}
            instance_map: dict[str, dict[str, float]] = {}
            for ki in concept_result.get("keyword_instances", []):
                if not ki or not ki.get("word"):
                    continue
                word = ki["word"]
                raw = ki.get("article_similarities") or "{}"
                try:
                    article_sims = json.loads(raw) if isinstance(raw, str) else (raw or {})
                except (json.JSONDecodeError, TypeError):
                    article_sims = {}
                instance_map[word] = article_sims

            # Get ALL articles that have each keyword (not just those in concept)
            all_keywords = list(instance_map.keys())
            keyword_articles: list[dict] = []
            if all_keywords:
                ka_result = session.run(
                    """
                    MATCH (a:Article)-[r:HAS_KEYWORD]->(k:Keyword)
                    WHERE k.word IN $words
                    RETURN k.word AS word, a.id AS article_id, a.article_name AS article_name,
                           r.confidence AS confidence, r.description AS description,
                           r.chunk_ids AS chunk_ids
                    """,
                    words=all_keywords,
                ).data()
                keyword_articles = ka_result

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

        # Build keyword traces: for each (word, article), determine if in_concept
        keyword_traces: list[dict] = []
        seen: set[str] = set()

        for ka in keyword_articles:
            if not ka or not ka.get("word"):
                continue
            word = ka["word"]
            aid = ka.get("article_id", "")
            key = f"{word}:{aid}"
            if key in seen:
                continue
            seen.add(key)

            # Check if this article is in the INSTANCE_OF map for this word
            word_sims = instance_map.get(word, {})
            in_concept = aid in word_sims
            similarity = word_sims.get(aid, None)

            max_text_len = None if full_text else 300
            chunks = self.trace_keyword_to_chunks(word, aid, max_text_len=max_text_len)

            keyword_traces.append({
                "word": word,
                "article_id": aid,
                "article_name": ka.get("article_name"),
                "confidence": ka.get("confidence"),
                "description": ka.get("description"),
                "in_concept": in_concept,
                "similarity": similarity,
                "chunks": chunks,
            })

        # Sort: in-concept first, then by similarity (desc)
        keyword_traces.sort(key=lambda t: (
            not t["in_concept"],  # in_concept=True first
            -(t["similarity"] or 0),
        ))

        return {
            "concept_id": concept_id,
            "canonical_name": concept_result["name"],
            "domain": concept_result["domain"],
            "description": concept_result["description"],
            "source_articles": concept_result.get("source_articles", []),
            "run_id": concept_result.get("run_id"),
            "version": concept_result.get("version"),
            "is_active": concept_result.get("is_active"),
            "keywords": all_keywords,
            "keyword_traces": keyword_traces,
            "cross_relations": rels_result,
        }

    def trace_keyword_to_chunks(
        self, keyword_word: str, article_id: str,
        max_text_len: int | None = 300,
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
                    text = payload.get("text", "")
                    if max_text_len and len(text) > max_text_len:
                        text = text[:max_text_len] + "…"
                    chunks.append({
                        "chunk_id": payload.get("node_id"),
                        "level": payload.get("level", 0),
                        "text": text,
                    })
        except Exception as exc:
            logger.warning("Failed to trace chunks: %s", exc)

        return sorted(chunks, key=lambda c: c.get("level", 0), reverse=True)
