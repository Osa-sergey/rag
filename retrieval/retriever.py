"""Multi-source retriever — search across RAPTOR chunks, concepts, and relations."""
from __future__ import annotations

import logging
from typing import Any

from omegaconf import DictConfig
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from retrieval.models import (
    ChunkResult,
    ConceptResult,
    RelationResult,
    RetrievalResult,
)

logger = logging.getLogger(__name__)


class MultiSourceRetriever:
    """Search across RAPTOR chunks, concepts, and cross-relations.

    Features:
      - Multi-query: original + LLM-rephrased variants
      - Deduplication with hit_count tracking
      - Tracing: which query variant found each result
      - Cross-relation enrichment from Neo4j for found concepts
    """

    def __init__(
        self,
        cfg: DictConfig,
        *,
        qdrant_client: QdrantClient | None = None,
        embedder: Any = None,
        graph_store: Any = None,
    ) -> None:
        self.cfg = cfg

        # Qdrant
        if qdrant_client:
            self._qd = qdrant_client
        else:
            self._qd = QdrantClient(
                host=cfg.stores.qdrant.get("host", "localhost"),
                port=cfg.stores.qdrant.get("port", 6333),
            )

        # Collections
        self._chunks_collection = cfg.stores.qdrant.get(
            "chunks_collection", "raptor_chunks",
        )
        self._concepts_collection = cfg.stores.qdrant.get(
            "concepts_collection", "concepts",
        )
        self._relations_collection = cfg.stores.qdrant.get(
            "cross_relations_collection", "cross_relations",
        )

        self._embedder = embedder
        self._gs = graph_store

    # ──────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        rephrase: bool = True,
        level: int | None = None,
    ) -> RetrievalResult:
        """Run multi-source retrieval.

        Args:
            query: User query string.
            top_k: Max results per source per query variant.
            rephrase: Whether to generate rephrased queries via LLM.
            level: Optional RAPTOR level filter for chunks.

        Returns:
            RetrievalResult with chunks, concepts, relations.
        """
        result = RetrievalResult(query=query)

        # Build query variants
        queries = [query]
        if rephrase:
            rephrased = self._rephrase_query(query)
            result.rephrased_queries = rephrased
            queries.extend(rephrased)

        # Embed all queries
        query_vectors = self._embedder.embed_texts(queries)

        # ── Search RAPTOR chunks ──
        chunks_map: dict[str, ChunkResult] = {}
        for q_text, q_vec in zip(queries, query_vectors):
            hits = self._search_collection(
                self._chunks_collection, q_vec, top_k, level=level,
            )
            for hit in hits:
                payload = hit["payload"]
                nid = payload.get("node_id", str(hit["id"]))
                if nid in chunks_map:
                    chunks_map[nid].hit_count += 1
                    chunks_map[nid].found_by.append(q_text)
                    # Keep best score
                    if hit["score"] > chunks_map[nid].score:
                        chunks_map[nid].score = hit["score"]
                else:
                    chunks_map[nid] = ChunkResult(
                        node_id=nid,
                        article_id=payload.get("article_id", ""),
                        level=payload.get("level", 0),
                        text=payload.get("text", ""),
                        score=hit["score"],
                        keywords=payload.get("keywords", []),
                        hit_count=1,
                        found_by=[q_text],
                    )

        # ── Search Concepts ──
        concepts_map: dict[str, ConceptResult] = {}
        for q_text, q_vec in zip(queries, query_vectors):
            hits = self._search_collection(
                self._concepts_collection, q_vec, top_k,
            )
            for hit in hits:
                payload = hit["payload"]
                cid = payload.get("concept_id", str(hit["id"]))
                if cid in concepts_map:
                    concepts_map[cid].hit_count += 1
                    concepts_map[cid].found_by.append(q_text)
                    if hit["score"] > concepts_map[cid].score:
                        concepts_map[cid].score = hit["score"]
                else:
                    concepts_map[cid] = ConceptResult(
                        concept_id=cid,
                        name=payload.get("canonical_name", ""),
                        domain=payload.get("domain", ""),
                        description=payload.get("description", ""),
                        score=hit["score"],
                        keywords=payload.get("keyword_words", []),
                        articles=payload.get("source_articles", []),
                        hit_count=1,
                        found_by=[q_text],
                    )

        # ── Search Cross-Relations ──
        relations_map: dict[str, RelationResult] = {}
        for q_text, q_vec in zip(queries, query_vectors):
            hits = self._search_collection(
                self._relations_collection, q_vec, top_k,
            )
            for hit in hits:
                payload = hit["payload"]
                rid = f"{payload.get('source_concept_id', '')}:{payload.get('target_concept_id', '')}:{payload.get('predicate', '')}"
                if rid in relations_map:
                    relations_map[rid].hit_count += 1
                    relations_map[rid].found_by.append(q_text)
                    if hit["score"] > relations_map[rid].score:
                        relations_map[rid].score = hit["score"]
                else:
                    relations_map[rid] = RelationResult(
                        source_concept_id=payload.get("source_concept_id", ""),
                        target_concept_id=payload.get("target_concept_id", ""),
                        predicate=payload.get("predicate", ""),
                        description=payload.get("description", ""),
                        score=hit["score"],
                        hit_count=1,
                        found_by=[q_text],
                    )

        # ── Enrich concepts with Neo4j relations ──
        if self._gs and concepts_map:
            self._enrich_concepts_with_relations(concepts_map)

        # ── Enrich relation names from Neo4j ──
        if self._gs and relations_map:
            self._enrich_relation_names(relations_map)

        # ── Sort by weighted score (score * hit_count) ──
        result.chunks = sorted(
            chunks_map.values(),
            key=lambda x: x.score * x.hit_count,
            reverse=True,
        )
        result.concepts = sorted(
            concepts_map.values(),
            key=lambda x: x.score * x.hit_count,
            reverse=True,
        )
        result.relations = sorted(
            relations_map.values(),
            key=lambda x: x.score * x.hit_count,
            reverse=True,
        )

        return result

    # ──────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────

    def _search_collection(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int,
        *,
        level: int | None = None,
    ) -> list[dict]:
        """Search a single Qdrant collection."""
        try:
            collections = {
                c.name for c in self._qd.get_collections().collections
            }
            if collection not in collections:
                logger.warning("Collection '%s' not found, skipping", collection)
                return []

            conditions = []
            if level is not None:
                conditions.append(
                    FieldCondition(key="level", match=MatchValue(value=level))
                )
            query_filter = Filter(must=conditions) if conditions else None

            results = self._qd.query_points(
                collection_name=collection,
                query=query_vector,
                limit=top_k,
                query_filter=query_filter,
                with_payload=True,
            )
            return [
                {"id": r.id, "score": r.score, "payload": r.payload}
                for r in results.points
            ]
        except Exception as exc:
            logger.warning("Search in '%s' failed: %s", collection, exc)
            return []

    def _rephrase_query(self, query: str) -> list[str]:
        """Generate 2-3 rephrased query variants via LLM."""
        try:
            from raptor_pipeline.summarizer.llm_summarizer import _build_llm
            llm = _build_llm(self.cfg.llm)

            template = self.cfg.get("rephrase_prompt", {}).get("template", "")
            if not template:
                template = (
                    "Перефразируй следующий поисковый запрос 3 разными способами "
                    "для поиска в базе знаний по IT-статьям. "
                    "Используй синонимы, другие формулировки и переводы (рус/англ).\n\n"
                    "Запрос: {query}\n\n"
                    "Верни ТОЛЬКО список из 3 вариантов, каждый на новой строке, "
                    "без нумерации и без пояснений."
                )

            prompt = template.replace("{query}", query)
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # Parse: strip thinking tags
            import re
            content = re.sub(
                r'<(thought|think)>.*?</\1>', '', content,
                flags=re.DOTALL | re.IGNORECASE,
            )

            lines = [
                line.strip().lstrip("0123456789.-) ")
                for line in content.strip().split("\n")
                if line.strip() and len(line.strip()) > 5
            ]
            result = lines[:3]
            logger.info("Rephrased query into %d variants", len(result))
            return result

        except Exception as exc:
            logger.warning("Query rephrasing failed: %s", exc)
            return []

    def _enrich_concepts_with_relations(
        self, concepts_map: dict[str, ConceptResult],
    ) -> None:
        """Load CROSS_RELATED_TO relations for found concepts from Neo4j."""
        concept_ids = list(concepts_map.keys())
        try:
            with self._gs._driver.session(database=self._gs._database) as session:
                result = session.run(
                    """
                    UNWIND $ids AS cid
                    MATCH (c:Concept {id: cid})-[r:CROSS_RELATED_TO]-(other:Concept)
                    RETURN c.id AS concept_id,
                           other.canonical_name AS other_name,
                           other.domain AS other_domain,
                           r.predicate AS predicate,
                           r.description AS description,
                           r.confidence AS confidence
                    """,
                    ids=concept_ids,
                ).data()

            for row in result:
                cid = row["concept_id"]
                if cid in concepts_map:
                    concepts_map[cid].relations.append({
                        "name": row["other_name"],
                        "domain": row.get("other_domain", ""),
                        "predicate": row.get("predicate", ""),
                        "description": row.get("description", ""),
                        "confidence": row.get("confidence", 0),
                    })
        except Exception as exc:
            logger.warning("Failed to enrich concepts: %s", exc)

    def _enrich_relation_names(
        self, relations_map: dict[str, RelationResult],
    ) -> None:
        """Resolve concept_id → canonical_name for relations."""
        all_ids = set()
        for rel in relations_map.values():
            all_ids.add(rel.source_concept_id)
            all_ids.add(rel.target_concept_id)
        all_ids.discard("")

        if not all_ids:
            return

        try:
            with self._gs._driver.session(database=self._gs._database) as session:
                result = session.run(
                    """
                    UNWIND $ids AS cid
                    MATCH (c:Concept {id: cid})
                    RETURN c.id AS id, c.canonical_name AS name
                    """,
                    ids=list(all_ids),
                ).data()
            id_to_name = {r["id"]: r["name"] for r in result}

            for rel in relations_map.values():
                rel.source_name = id_to_name.get(rel.source_concept_id, rel.source_concept_id[:8])
                rel.target_name = id_to_name.get(rel.target_concept_id, rel.target_concept_id[:8])
        except Exception as exc:
            logger.warning("Failed to resolve relation names: %s", exc)
