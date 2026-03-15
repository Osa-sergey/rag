"""Cross-article concept processor — main orchestrator."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from omegaconf import DictConfig

from concept_builder.article_selector import ArticleSelector
from concept_builder.concept_clusterer import ConceptClusterer
from concept_builder.keyword_describer import KeywordDescriber
from concept_builder.models import (
    ConceptNode,
    CrossRelation,
    DryRunReport,
    KeywordContext,
)
from concept_builder.relation_builder import RelationBuilder
from raptor_pipeline.token_tracker import TokenTracker

logger = logging.getLogger(__name__)


class CrossArticleProcessor:
    """Orchestrate cross-article concept building.

    Steps:
      1. Select articles (BFS/DFS or explicit)
      2. Load keywords with context from Neo4j
      3. Generate descriptions (dual-context LLM)
      4. Compute embeddings of descriptions
      5. Cluster by cosine similarity → Concept groups
      6. LLM: generalize each cluster into a Concept
      7. LLM: extract cross-relations between Concepts
      8. Store in Neo4j + Qdrant
    """

    def __init__(
        self,
        cfg: DictConfig,
        *,
        graph_store: Any = None,
        vector_store: Any = None,
        embedder: Any = None,
        article_selector: ArticleSelector | None = None,
        keyword_describer: KeywordDescriber | None = None,
        concept_clusterer: ConceptClusterer | None = None,
        relation_builder: RelationBuilder | None = None,
    ) -> None:
        self.cfg = cfg
        self._gs = graph_store
        self._vs = vector_store
        self._embedder = embedder
        self._token_tracker = TokenTracker()

        self._selector = article_selector or ArticleSelector(graph_store)
        self._describer = keyword_describer
        self._clusterer = concept_clusterer or ConceptClusterer()
        self._relation_builder = relation_builder

        self._similarity_threshold: float = cfg.get("similarity_threshold", 0.85)
        self._min_confidence: float = cfg.get("min_keyword_confidence", 0.8)

    # ══════════════════════════════════════════════════════════
    # Dry Run
    # ══════════════════════════════════════════════════════════

    def dry_run(
        self,
        article_ids: list[str],
    ) -> DryRunReport:
        """Preview what would be processed without running LLM calls."""
        report = DryRunReport(articles=article_ids)

        for aid in article_ids:
            kws = self._load_article_keywords(aid)
            filtered = [k for k in kws if k.confidence >= self._min_confidence]
            report.keywords_per_article[aid] = len(filtered)
            report.raw_keywords_per_article[aid] = len(kws)
            report.total_keywords += len(filtered)

            # Confidence distribution for diagnostics
            high = sum(1 for k in kws if k.confidence >= 0.8)
            med = sum(1 for k in kws if 0.5 <= k.confidence < 0.8)
            low = sum(1 for k in kws if 0.0 < k.confidence < 0.5)
            null_count = sum(1 for k in kws if k.confidence == 0.0)
            report.confidence_distributions[aid] = {
                "high": high, "med": med, "low": low, "null": null_count,
            }

            # Sample confidence values for debugging
            report.sample_confidences[aid] = sorted(
                [k.confidence for k in kws], reverse=True,
            )[:10]

            # Get article name
            with self._gs._driver.session(database=self._gs._database) as session:
                result = session.run(
                    "MATCH (a:Article {id: $id}) RETURN a.article_name AS name",
                    id=aid,
                ).single()
                report.article_names[aid] = result["name"] if result else aid

        # Get references between selected articles
        id_set = set(article_ids)
        with self._gs._driver.session(database=self._gs._database) as session:
            refs = session.run(
                """
                MATCH (a:Article)-[r:REFERENCES]-(b:Article)
                WHERE a.id IN $ids AND b.id IN $ids AND a.id <> b.id
                RETURN DISTINCT
                    CASE WHEN a.id < b.id THEN a.id ELSE b.id END AS source,
                    CASE WHEN a.id < b.id THEN b.id ELSE a.id END AS target
                """,
                ids=article_ids,
            ).data()
            report.references = [(r["source"], r["target"]) for r in refs]

        # Estimate LLM calls
        est_clusters = max(1, report.total_keywords // 3)
        report.estimated_llm_calls = report.total_keywords + est_clusters + 1

        return report

    # ══════════════════════════════════════════════════════════
    # Process
    # ══════════════════════════════════════════════════════════

    def process(self, article_ids: list[str]) -> dict:
        """Run the full cross-article concept building pipeline.

        Returns:
            Summary dict with counts and created concepts.
        """
        logger.info("═" * 60)
        logger.info("Cross-Article Processor: %d articles", len(article_ids))
        logger.info("═" * 60)

        # ── Step 1: Load keywords ─────────────────────────────
        all_contexts: list[KeywordContext] = []
        for aid in article_ids:
            kws = self._load_article_keywords(aid)
            filtered = [k for k in kws if k.confidence >= self._min_confidence]
            all_contexts.extend(filtered)
            logger.info(
                "  Article '%s': %d keywords (≥%.1f confidence)",
                aid, len(filtered), self._min_confidence,
            )

        if not all_contexts:
            logger.warning("No keywords found above confidence threshold")
            return {"concepts": 0, "relations": 0}

        logger.info("  Total keywords for processing: %d", len(all_contexts))

        # ── Step 2: Generate descriptions ─────────────────────
        logger.info("  Generating keyword descriptions...")
        for kc in all_contexts:
            if not kc.description and self._describer:
                kc.description = self._describer.describe(
                    kc.word, kc.article_id, kc.chunk_ids,
                )
            if not kc.description:
                # Fallback: use word + category as description
                kc.description = f"{kc.word} ({kc.category})"

        # ── Step 3: Compute embeddings ────────────────────────
        logger.info("  Computing description embeddings...")
        descriptions = [kc.description for kc in all_contexts]
        embeddings = self._embedder.embed_texts(descriptions)
        for kc, emb in zip(all_contexts, embeddings):
            kc.embedding = emb

        # ── Step 4: Cluster ───────────────────────────────────
        logger.info("  Clustering keywords into concepts...")
        clusters = self._clusterer.cluster(
            all_contexts, self._similarity_threshold,
        )

        # ── Step 5: Create Concept nodes ──────────────────────
        logger.info("  Creating %d Concept nodes...", len(clusters))
        concepts: list[ConceptNode] = []
        for cluster in clusters:
            concept = self._create_concept_from_cluster(cluster)
            concepts.append(concept)

        # ── Step 6: Extract cross-relations ───────────────────
        relations: list[CrossRelation] = []
        if self._relation_builder and len(concepts) >= 2:
            logger.info("  Extracting cross-relations between %d concepts...", len(concepts))
            relations = self._relation_builder.extract(concepts)

        # ── Step 7: Compute concept embeddings ────────────────
        logger.info("  Computing concept embeddings...")
        concept_descriptions = [c.description for c in concepts]
        concept_embeddings = self._embedder.embed_texts(concept_descriptions)
        for c, emb in zip(concepts, concept_embeddings):
            c.embedding = emb

        # Compute relation embeddings
        if relations:
            rel_descriptions = [r.description for r in relations]
            rel_embeddings = self._embedder.embed_texts(rel_descriptions)
            for r, emb in zip(relations, rel_embeddings):
                r.embedding = emb

        # ── Step 8: Store ─────────────────────────────────────
        logger.info("  Storing concepts and relations...")
        self._store_concepts(concepts)
        self._store_relations(relations)
        self._store_instance_of_edges(concepts)
        self._store_concept_embeddings(concepts, relations)

        # ── Summary ───────────────────────────────────────────
        self._token_tracker.log_summary("cross_article")
        self._token_tracker.reset()

        summary = {
            "articles": article_ids,
            "total_keywords": len(all_contexts),
            "concepts_created": len(concepts),
            "relations_created": len(relations),
            "concepts": [
                {
                    "id": c.id,
                    "name": c.canonical_name,
                    "domain": c.domain,
                    "keywords": c.keyword_words,
                    "articles": c.source_articles,
                }
                for c in concepts
            ],
        }

        logger.info("═" * 60)
        logger.info(
            "Done: %d concepts, %d cross-relations from %d articles",
            len(concepts), len(relations), len(article_ids),
        )
        return summary

    # ══════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════

    def _load_article_keywords(self, article_id: str) -> list[KeywordContext]:
        """Load keywords for an article from Neo4j."""
        with self._gs._driver.session(database=self._gs._database) as session:
            # Get article version
            art_result = session.run(
                "MATCH (a:Article {id: $id}) RETURN a.version AS version",
                id=article_id,
            ).single()
            version = art_result["version"] if art_result else ""

            # Get keywords with chunk_ids and confidence
            kw_results = session.run(
                """
                MATCH (a:Article {id: $id})-[r:HAS_KEYWORD]->(k:Keyword)
                RETURN k.word AS word,
                       k.category AS category,
                       r.confidence AS confidence,
                       r.chunk_ids AS chunk_ids
                """,
                id=article_id,
            ).data()

        contexts = []
        for kw in kw_results:
            contexts.append(KeywordContext(
                word=kw["word"],
                article_id=article_id,
                version=version,
                category=kw.get("category", ""),
                confidence=kw.get("confidence", 0.0) or 0.0,
                chunk_ids=kw.get("chunk_ids", []) or [],
            ))
        return contexts

    def _create_concept_from_cluster(
        self, cluster: list[KeywordContext],
    ) -> ConceptNode:
        """Create a ConceptNode from a cluster of KeywordContexts.

        Uses LLM to generate summary if available, otherwise heuristic.
        """
        # Collect metadata
        all_words = list({kc.word for kc in cluster})
        all_articles = list({kc.article_id for kc in cluster})
        all_versions = {}
        for kc in cluster:
            if kc.article_id and kc.version:
                all_versions[kc.article_id] = kc.version

        # Most frequent word as canonical name
        word_counts: dict[str, int] = {}
        for kc in cluster:
            word_counts[kc.word] = word_counts.get(kc.word, 0) + 1
        canonical_name = max(word_counts, key=word_counts.get)

        # Try LLM summary
        description = ""
        domain = ""
        if self._describer and len(cluster) > 1:
            descriptions_text = "\n".join(
                f"- [{kc.article_id}] {kc.description}"
                for kc in cluster if kc.description
            )
            if descriptions_text:
                try:
                    from raptor_pipeline.summarizer.llm_summarizer import _build_llm
                    llm = _build_llm(self.cfg.llm)
                    template = self.cfg.prompts.concept_summary.get(
                        "template",
                        "Обобщи {keyword}: {descriptions}",
                    )
                    prompt = (
                        template
                        .replace("{keyword}", canonical_name)
                        .replace("{descriptions}", descriptions_text)
                    )
                    response = llm.invoke(prompt)
                    if self._token_tracker:
                        self._token_tracker.track(response, "concept_summary")
                    content = response.content if hasattr(response, "content") else str(response)

                    # Parse JSON response
                    import re
                    content = content.strip()
                    content = re.sub(
                        r'<(thought|think)>.*?</\1>', '', content,
                        flags=re.DOTALL | re.IGNORECASE,
                    )
                    if "```" in content:
                        match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
                        if match:
                            content = match.group(1)
                    parsed = json.loads(content)
                    description = parsed.get("description", "")
                    domain = parsed.get("domain", "")
                    if parsed.get("canonical_name"):
                        canonical_name = parsed["canonical_name"]
                except Exception as exc:
                    logger.debug("LLM concept summary failed: %s", exc)

        # Fallback description
        if not description:
            description = "; ".join(kc.description for kc in cluster[:3] if kc.description)
        if not domain:
            # Most common category as domain
            cat_counts: dict[str, int] = {}
            for kc in cluster:
                if kc.category:
                    cat_counts[kc.category] = cat_counts.get(kc.category, 0) + 1
            domain = max(cat_counts, key=cat_counts.get) if cat_counts else "general"

        return ConceptNode(
            canonical_name=canonical_name,
            domain=domain,
            description=description,
            source_articles=all_articles,
            source_versions=all_versions,
            keyword_words=all_words,
        )

    def _store_concepts(self, concepts: list[ConceptNode]) -> None:
        """Store Concept nodes in Neo4j."""
        with self._gs._driver.session(database=self._gs._database) as session:
            for c in concepts:
                session.run(
                    """
                    MERGE (concept:Concept {id: $id})
                    SET concept.canonical_name = $name,
                        concept.domain = $domain,
                        concept.description = $description,
                        concept.source_articles = $articles,
                        concept.source_versions = $versions,
                        concept.updated_at = $updated_at
                    ON CREATE SET concept.created_at = $created_at
                    """,
                    id=c.id,
                    name=c.canonical_name,
                    domain=c.domain,
                    description=c.description,
                    articles=c.source_articles,
                    versions=json.dumps(c.source_versions),
                    created_at=c.created_at,
                    updated_at=datetime.utcnow().isoformat(),
                )

    def _store_relations(self, relations: list[CrossRelation]) -> None:
        """Store CROSS_RELATED_TO edges in Neo4j."""
        with self._gs._driver.session(database=self._gs._database) as session:
            for r in relations:
                session.run(
                    """
                    MATCH (src:Concept {id: $src_id})
                    MATCH (tgt:Concept {id: $tgt_id})
                    MERGE (src)-[rel:CROSS_RELATED_TO {predicate: $predicate}]->(tgt)
                    SET rel.description = $description,
                        rel.source_articles = $articles,
                        rel.source_versions = $versions,
                        rel.confidence = $confidence
                    """,
                    src_id=r.source_concept_id,
                    tgt_id=r.target_concept_id,
                    predicate=r.predicate,
                    description=r.description,
                    articles=r.source_articles,
                    versions=json.dumps(r.source_versions),
                    confidence=r.confidence,
                )

    def _store_instance_of_edges(self, concepts: list[ConceptNode]) -> None:
        """Create INSTANCE_OF edges from Keywords to Concepts."""
        with self._gs._driver.session(database=self._gs._database) as session:
            for c in concepts:
                for word in c.keyword_words:
                    session.run(
                        """
                        MATCH (k:Keyword {word: $word})
                        MATCH (c:Concept {id: $concept_id})
                        MERGE (k)-[:INSTANCE_OF]->(c)
                        """,
                        word=word,
                        concept_id=c.id,
                    )

    def _store_concept_embeddings(
        self,
        concepts: list[ConceptNode],
        relations: list[CrossRelation],
    ) -> None:
        """Store concept and relation embeddings in Qdrant."""
        from qdrant_client.models import PointStruct

        # Concepts
        if concepts:
            concept_points = []
            for c in concepts:
                if c.embedding:
                    concept_points.append(PointStruct(
                        id=hash(c.id) % (2**63),
                        vector=c.embedding,
                        payload={
                            "concept_id": c.id,
                            "canonical_name": c.canonical_name,
                            "domain": c.domain,
                            "description": c.description,
                            "source_articles": c.source_articles,
                            "keyword_words": c.keyword_words,
                        },
                    ))

            if concept_points:
                concepts_collection = self.cfg.stores.qdrant.get(
                    "concepts_collection", "concepts",
                )
                self._vs._client.upsert(
                    collection_name=concepts_collection,
                    points=concept_points,
                )
                logger.info("Stored %d concept embeddings", len(concept_points))

        # Cross-relations
        if relations:
            rel_points = []
            for r in relations:
                if r.embedding:
                    rel_id = hash(f"{r.source_concept_id}:{r.target_concept_id}:{r.predicate}")
                    rel_points.append(PointStruct(
                        id=rel_id % (2**63),
                        vector=r.embedding,
                        payload={
                            "source_concept_id": r.source_concept_id,
                            "target_concept_id": r.target_concept_id,
                            "predicate": r.predicate,
                            "description": r.description,
                            "confidence": r.confidence,
                        },
                    ))

            if rel_points:
                rel_collection = self.cfg.stores.qdrant.get(
                    "cross_relations_collection", "cross_relations",
                )
                self._vs._client.upsert(
                    collection_name=rel_collection,
                    points=rel_points,
                )
                logger.info("Stored %d relation embeddings", len(rel_points))
