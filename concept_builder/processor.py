"""Cross-article concept processor — main orchestrator."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from tqdm import tqdm

from omegaconf import DictConfig

from concept_builder.article_selector import ArticleSelector
from concept_builder.concept_clusterer import ConceptClusterer
from concept_builder.keyword_describer import KeywordDescriber
from concept_builder.models import (
    ConceptNode,
    CrossRelation,
    DryRunReport,
    ExpandResult,
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
            # Get article name
            with self._gs._driver.session(database=self._gs._database) as session:
                result = session.run(
                    "MATCH (a:Article {id: $id}) RETURN a.article_name AS name",
                    id=aid,
                ).single()
                report.article_names[aid] = result["name"] if result else aid

            kws = self._load_article_keywords(aid)

            # Detect unprocessed (placeholder) articles:
            # exist as nodes but have no keywords (never run through raptor_pipeline)
            if not kws:
                report.unprocessed_articles.append(aid)
                report.keywords_per_article[aid] = 0
                report.raw_keywords_per_article[aid] = 0
                continue

            filtered = [k for k in kws if k.confidence >= self._min_confidence]
            report.keywords_per_article[aid] = len(filtered)
            report.raw_keywords_per_article[aid] = len(kws)
            report.total_keywords += len(filtered)

            # Count keywords that still need LLM description
            needing = sum(1 for k in filtered if not k.description)
            report.keywords_needing_description[aid] = needing
            report.total_needing_description += needing

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

        # Estimate LLM calls (only keywords needing description + clusters + relations)
        est_clusters = max(1, report.total_keywords // 3)
        report.estimated_llm_calls = report.total_needing_description + est_clusters + 1

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

        # ── Step 1: Load keywords, skip unprocessed articles ──
        all_contexts: list[KeywordContext] = []
        processed_articles: list[str] = []
        skipped_articles: list[str] = []

        for aid in tqdm(article_ids, desc="Loading keywords", unit="article"):
            kws = self._load_article_keywords(aid)
            if not kws:
                logger.warning(
                    "  ⚠️  Article '%s' — необработана (нет keywords), пропускаем",
                    aid,
                )
                skipped_articles.append(aid)
                continue

            filtered = [k for k in kws if k.confidence >= self._min_confidence]
            if not filtered:
                logger.warning(
                    "  ⚠️  Article '%s' — 0 keywords ≥ %.1f (total: %d), пропускаем",
                    aid, self._min_confidence, len(kws),
                )
                skipped_articles.append(aid)
                continue

            all_contexts.extend(filtered)
            processed_articles.append(aid)
            logger.info(
                "  Article '%s': %d keywords (≥%.1f confidence)",
                aid, len(filtered), self._min_confidence,
            )

        if skipped_articles:
            logger.warning(
                "  Пропущено %d статей (необработаны или нет keywords): %s",
                len(skipped_articles), skipped_articles,
            )

        if not all_contexts:
            logger.warning("No keywords found above confidence threshold")
            return {"concepts": 0, "relations": 0, "skipped_articles": skipped_articles}

        logger.info("  Total keywords for processing: %d", len(all_contexts))

        # ── Step 2: Generate descriptions (reuse cached) ──────
        need_description = [kc for kc in all_contexts if not kc.description]
        cached = len(all_contexts) - len(need_description)
        logger.info(
            "  Descriptions: %d cached, %d need LLM generation",
            cached, len(need_description),
        )
        for kc in tqdm(need_description, desc="Generating descriptions", unit="kw"):
            if self._describer:
                kc.description = self._describer.describe(
                    kc.word, kc.article_id, kc.chunk_ids,
                )
            if not kc.description:
                # Fallback: use word + category as description
                kc.description = f"{kc.word} ({kc.category})"

        # Save new descriptions back to Neo4j for future reuse
        new_descriptions = [
            kc for kc in need_description if kc.description
        ]
        if new_descriptions:
            self._save_keyword_descriptions(new_descriptions)
            logger.info("  Saved %d new keyword descriptions to Neo4j", len(new_descriptions))

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
        for cluster in tqdm(clusters, desc="Creating concepts", unit="concept"):
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

            # Get keywords with chunk_ids, confidence, and cached description
            kw_results = session.run(
                """
                MATCH (a:Article {id: $id})-[r:HAS_KEYWORD]->(k:Keyword)
                RETURN k.word AS word,
                       k.category AS category,
                       r.confidence AS confidence,
                       r.chunk_ids AS chunk_ids,
                       r.description AS description
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
                description=kw.get("description", "") or "",
            ))
        return contexts

    def _save_keyword_descriptions(self, contexts: list[KeywordContext]) -> None:
        """Persist keyword descriptions to HAS_KEYWORD.description in Neo4j."""
        with self._gs._driver.session(database=self._gs._database) as session:
            for kc in contexts:
                session.run(
                    """
                    MATCH (a:Article {id: $article_id})-[r:HAS_KEYWORD]->(k:Keyword {word: $word})
                    SET r.description = $description
                    """,
                    article_id=kc.article_id,
                    word=kc.word,
                    description=kc.description,
                )

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
                    ON CREATE SET concept.created_at = $created_at
                    SET concept.canonical_name = $name,
                        concept.concept_group_id = $group_id,
                        concept.domain = $domain,
                        concept.description = $description,
                        concept.source_articles = $articles,
                        concept.source_versions = $versions,
                        concept.keyword_words = $keyword_words,
                        concept.version = $version,
                        concept.is_active = $is_active,
                        concept.previous_version_id = $prev_id,
                        concept.updated_at = $updated_at
                    """,
                    id=c.id,
                    group_id=c.concept_group_id,
                    name=c.canonical_name,
                    domain=c.domain,
                    description=c.description,
                    articles=c.source_articles,
                    versions=json.dumps(c.source_versions),
                    keyword_words=c.keyword_words,
                    version=c.version,
                    is_active=c.is_active,
                    prev_id=c.previous_version_id or "",
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

    # ══════════════════════════════════════════════════════════
    # Expand — incremental concept building
    # ══════════════════════════════════════════════════════════

    def expand(
        self,
        concept_ids: list[str],
        article_ids: list[str],
        *,
        high_threshold: float = 0.85,
        low_threshold: float = 0.65,
        llm_confidence_threshold: float = 0.7,
    ) -> list[ExpandResult]:
        """Expand existing concepts with keywords from new articles.

        Returns list of ExpandResult, one per concept that had matches.
        User must call choose_expand_versions() after reviewing.
        """
        import numpy as np

        logger.info("═" * 60)
        logger.info("Expand: %d concepts × %d articles", len(concept_ids), len(article_ids))
        logger.info("  high_threshold=%.2f, low_threshold=%.2f", high_threshold, low_threshold)
        logger.info("═" * 60)

        # ── Phase 0: Load existing concepts + keywords ────────
        concepts = self._load_existing_concepts(concept_ids)
        if not concepts:
            logger.error("No concepts found for given IDs")
            return []

        logger.info("  Loaded %d concepts", len(concepts))

        all_keywords: list[KeywordContext] = []
        for aid in tqdm(article_ids, desc="Loading keywords", unit="article"):
            kws = self._load_article_keywords(aid)
            if not kws:
                logger.warning("  ⚠️  Article '%s' — нет keywords, пропускаем", aid)
                continue
            filtered = [k for k in kws if k.confidence >= self._min_confidence]
            all_keywords.extend(filtered)
            logger.info("  Article '%s': %d keywords", aid, len(filtered))

        if not all_keywords:
            logger.warning("No keywords found")
            return []

        # Generate descriptions + embeddings
        need_desc = [kc for kc in all_keywords if not kc.description]
        if need_desc:
            logger.info("  Generating %d descriptions...", len(need_desc))
            for kc in tqdm(need_desc, desc="Descriptions", unit="kw"):
                if self._describer:
                    kc.description = self._describer.describe(
                        kc.word, kc.article_id, kc.chunk_ids,
                    )
                if not kc.description:
                    kc.description = f"{kc.word} ({kc.category})"
            self._save_keyword_descriptions(need_desc)

        logger.info("  Computing keyword embeddings...")
        descriptions = [kc.description for kc in all_keywords]
        embeddings = self._embedder.embed_texts(descriptions)
        for kc, emb in zip(all_keywords, embeddings):
            kc.embedding = emb

        # ── Phase 1: Match keywords → concepts ───────────────
        logger.info("  Matching keywords to concepts...")
        direct_matches, llm_candidates, unmatched = self._match_to_concepts(
            all_keywords, concepts, high_threshold, low_threshold,
        )

        logger.info("  Direct matches: %d, LLM candidates: %d, Unmatched: %d",
                     sum(len(v) for v in direct_matches.values()),
                     sum(len(v) for v in llm_candidates.values()),
                     len(unmatched))

        results: list[ExpandResult] = []

        # ── Phase 2: Create v(N+1) — direct matches ──────────
        for concept in concepts:
            cid = concept.id
            directs = direct_matches.get(cid, [])
            candidates = llm_candidates.get(cid, [])

            if not directs and not candidates:
                continue

            result = ExpandResult(
                concept_id=cid,
                concept_name=concept.canonical_name,
                domain=concept.domain,
                original_version=concept.version,
                original=concept,
            )

            if directs:
                direct_kws = [kw for kw, sim in directs]
                result.direct_keywords = [(kw.word, sim) for kw, sim in directs]

                new_desc = self._regenerate_concept_description(
                    concept, direct_kws,
                )
                result.v_direct = concept.evolve(
                    direct_kws, new_description=new_desc,
                )
                logger.info(
                    "  💡 %s v%d → v%d (+%d direct)",
                    concept.canonical_name, concept.version,
                    result.v_direct.version, len(directs),
                )

            # ── Phase 3: LLM-verify candidates ───────────────
            if candidates:
                confirmed = []
                for kw, sim in tqdm(candidates, desc=f"LLM verify for {concept.canonical_name}", unit="kw"):
                    belongs, confidence, relationship = self._verify_keyword_belongs(
                        concept, kw,
                    )
                    if belongs and confidence >= llm_confidence_threshold:
                        confirmed.append((kw, confidence, relationship))
                        result.llm_keywords.append((kw.word, confidence, relationship))
                    else:
                        unmatched.append(kw)

                # ── Phase 4: Create v(N+2) — direct + LLM ────
                if confirmed:
                    base = result.v_direct or concept
                    llm_kws = [kw for kw, conf, rel in confirmed]
                    relationships = [rel for kw, conf, rel in confirmed]

                    new_desc = self._regenerate_concept_description(
                        base, llm_kws, relationships=relationships,
                    )
                    result.v_llm = base.evolve(
                        llm_kws, new_description=new_desc,
                    )
                    logger.info(
                        "  💡 %s v%d → v%d (+%d LLM-verified)",
                        concept.canonical_name, base.version,
                        result.v_llm.version, len(confirmed),
                    )

            results.append(result)

        # Return results for user review (phases 5-8 happen after user choice)
        # Also store unmatched for later clustering
        self._pending_unmatched = unmatched
        self._pending_concepts = concepts

        return results

    def finalize_expand(
        self,
        results: list[ExpandResult],
    ) -> dict:
        """Finalize expand after user has chosen versions.

        Stores chosen versions, clusters unmatched keywords,
        creates cross-relations. Phase 5-8.
        """
        unmatched = getattr(self, "_pending_unmatched", [])
        all_concepts = list(getattr(self, "_pending_concepts", []))

        active_concepts: list[ConceptNode] = []
        all_versions_to_store: list[ConceptNode] = []

        for r in results:
            if r.chosen_version is None or r.chosen_version == r.original_version:
                # User kept original, no changes
                active_concepts.append(r.original)
                continue

            # Deactivate old version
            r.original.is_active = False
            all_versions_to_store.append(r.original)

            if r.v_direct:
                if r.chosen_version == r.v_direct.version:
                    r.v_direct.is_active = True
                    all_versions_to_store.append(r.v_direct)
                    active_concepts.append(r.v_direct)
                else:
                    r.v_direct.is_active = False
                    all_versions_to_store.append(r.v_direct)

            if r.v_llm:
                if r.chosen_version == r.v_llm.version:
                    r.v_llm.is_active = True
                    all_versions_to_store.append(r.v_llm)
                    active_concepts.append(r.v_llm)
                else:
                    r.v_llm.is_active = False
                    all_versions_to_store.append(r.v_llm)

        # Store all versions
        if all_versions_to_store:
            self._store_concepts(all_versions_to_store)
            # Create EVOLVED_TO edges
            for r in results:
                if r.v_direct and r.chosen_version is not None:
                    self._store_evolved_to(r.original.id, r.v_direct.id)
                if r.v_llm:
                    base_id = r.v_direct.id if r.v_direct else r.original.id
                    self._store_evolved_to(base_id, r.v_llm.id)

        # ── Phase 6: Cluster unmatched → new concepts ─────────
        new_concepts: list[ConceptNode] = []
        if unmatched:
            logger.info("  Clustering %d unmatched keywords...", len(unmatched))

            # Ensure embeddings
            need_emb = [kc for kc in unmatched if kc.embedding is None]
            if need_emb:
                descs = [kc.description for kc in need_emb]
                embs = self._embedder.embed_texts(descs)
                for kc, emb in zip(need_emb, embs):
                    kc.embedding = emb

            clusters = self._clusterer.cluster(unmatched, self._similarity_threshold)
            for cluster in clusters:
                concept = self._create_concept_from_cluster(cluster)
                new_concepts.append(concept)

            if new_concepts:
                self._store_concepts(new_concepts)
                self._store_instance_of_edges(new_concepts)
                logger.info("  Created %d new concepts", len(new_concepts))

        # Update INSTANCE_OF for expanded concepts
        for r in results:
            if r.chosen_version is not None and r.chosen_version != r.original_version:
                chosen = r.v_direct if r.chosen_version == (r.v_direct.version if r.v_direct else -1) else r.v_llm
                if chosen:
                    new_kw_words = set(chosen.keyword_words) - set(r.original.keyword_words)
                    if new_kw_words:
                        self._store_instance_of_for_words(list(new_kw_words), chosen.id)

        # ── Phase 7: Cross-relations ──────────────────────────
        all_active = active_concepts + new_concepts
        relations: list[CrossRelation] = []
        if self._relation_builder and len(all_active) >= 2:
            logger.info("  Extracting cross-relations...")
            relations = self._relation_builder.extract(all_active)

        # Compute embeddings for new/updated concepts
        concepts_needing_emb = [c for c in (new_concepts + all_versions_to_store)
                                if c.is_active]
        if concepts_needing_emb:
            descs = [c.description for c in concepts_needing_emb]
            embs = self._embedder.embed_texts(descs)
            for c, emb in zip(concepts_needing_emb, embs):
                c.embedding = emb

        if relations:
            rel_descs = [r.description for r in relations]
            rel_embs = self._embedder.embed_texts(rel_descs)
            for r, emb in zip(relations, rel_embs):
                r.embedding = emb

        # ── Phase 8: Store ────────────────────────────────────
        if relations:
            self._store_relations(relations)
        self._store_concept_embeddings(
            [c for c in concepts_needing_emb if c.is_active],
            relations,
        )

        self._token_tracker.log_summary("expand")
        self._token_tracker.reset()

        return {
            "concepts_updated": sum(1 for r in results if r.chosen_version and r.chosen_version != r.original_version),
            "new_concepts": len(new_concepts),
            "relations": len(relations),
            "versions_stored": len(all_versions_to_store),
        }

    # ──────────────────────────────────────────────────────────
    # Expand helpers
    # ──────────────────────────────────────────────────────────

    def _load_existing_concepts(self, concept_ids: list[str]) -> list[ConceptNode]:
        """Load existing Concept nodes from Neo4j + embeddings from Qdrant."""
        concepts = []
        with self._gs._driver.session(database=self._gs._database) as session:
            for cid in concept_ids:
                result = session.run(
                    """
                    MATCH (c:Concept {id: $id})
                    RETURN c.id AS id, c.concept_group_id AS group_id,
                           c.canonical_name AS name, c.domain AS domain,
                           c.description AS description,
                           c.source_articles AS articles,
                           c.source_versions AS versions,
                           c.keyword_words AS keywords,
                           c.version AS version,
                           c.is_active AS is_active,
                           c.previous_version_id AS prev_id
                    """,
                    id=cid,
                ).single()

                if not result:
                    logger.warning("  Concept '%s' not found, skipping", cid)
                    continue

                versions = result.get("versions", "{}")
                if isinstance(versions, str):
                    try:
                        versions = json.loads(versions)
                    except (json.JSONDecodeError, TypeError):
                        versions = {}

                concept = ConceptNode(
                    id=result["id"],
                    concept_group_id=result.get("group_id") or result["id"],
                    canonical_name=result.get("name", ""),
                    domain=result.get("domain", ""),
                    description=result.get("description", ""),
                    source_articles=result.get("articles") or [],
                    source_versions=versions,
                    keyword_words=result.get("keywords") or [],
                    version=result.get("version") or 1,
                    is_active=result.get("is_active", True),
                    previous_version_id=result.get("prev_id"),
                )
                concepts.append(concept)

        # Load embeddings from Qdrant
        if concepts and self._vs:
            try:
                concepts_collection = self.cfg.stores.qdrant.get(
                    "concepts_collection", "concepts",
                )
                for concept in concepts:
                    from qdrant_client.models import Filter, FieldCondition, MatchValue
                    points = self._vs._client.scroll(
                        collection_name=concepts_collection,
                        scroll_filter=Filter(must=[
                            FieldCondition(key="concept_id", match=MatchValue(value=concept.id)),
                        ]),
                        limit=1,
                        with_vectors=True,
                        with_payload=False,
                    )[0]
                    if points:
                        concept.embedding = points[0].vector
            except Exception as exc:
                logger.warning("Failed to load concept embeddings: %s", exc)

        return concepts

    def _match_to_concepts(
        self,
        keywords: list[KeywordContext],
        concepts: list[ConceptNode],
        high_threshold: float,
        low_threshold: float,
    ) -> tuple[dict, dict, list]:
        """Match keywords to concepts by cosine similarity.

        Returns:
            (direct_matches, llm_candidates, unmatched)
        """
        import numpy as np
        from collections import defaultdict

        direct_matches: dict[str, list[tuple[KeywordContext, float]]] = defaultdict(list)
        llm_candidates: dict[str, list[tuple[KeywordContext, float]]] = defaultdict(list)
        unmatched: list[KeywordContext] = []

        concept_vecs = {}
        for c in concepts:
            if c.embedding:
                concept_vecs[c.id] = np.array(c.embedding, dtype=np.float32)

        if not concept_vecs:
            logger.warning("No concept embeddings available for matching")
            return {}, {}, keywords

        for kw in keywords:
            if kw.embedding is None:
                unmatched.append(kw)
                continue

            kw_vec = np.array(kw.embedding, dtype=np.float32)
            best_id = ""
            best_sim = -1.0

            for cid, cvec in concept_vecs.items():
                sim = float(np.dot(kw_vec, cvec) / (
                    np.linalg.norm(kw_vec) * np.linalg.norm(cvec) + 1e-8
                ))
                if sim > best_sim:
                    best_sim = sim
                    best_id = cid

            if best_sim >= high_threshold:
                direct_matches[best_id].append((kw, best_sim))
            elif best_sim >= low_threshold:
                llm_candidates[best_id].append((kw, best_sim))
            else:
                unmatched.append(kw)

        return dict(direct_matches), dict(llm_candidates), unmatched

    def _regenerate_concept_description(
        self,
        concept: ConceptNode,
        new_keywords: list[KeywordContext],
        *,
        relationships: list[str] | None = None,
    ) -> str:
        """Regenerate concept description via LLM, incorporating new keywords.

        If too many keywords, processes in batches.
        """
        if not self._describer:
            parts = [concept.description]
            for kc in new_keywords:
                parts.append(f"{kc.word}: {kc.description}")
            return "; ".join(parts)

        from raptor_pipeline.summarizer.llm_summarizer import _build_llm
        llm = _build_llm(self.cfg.llm)

        # Build keyword descriptions text
        kw_items = []
        for i, kc in enumerate(new_keywords):
            line = f"- {kc.word}: {kc.description}"
            if relationships and i < len(relationships):
                line += f" (связь: {relationships[i]})"
            kw_items.append(line)

        # Batch if needed (estimate ~100 chars/keyword)
        max_chars = int(self.cfg.get("max_prompt_tokens", 3000) * 2.5 * 0.6)
        batches = []
        current_batch = []
        current_len = 0
        for item in kw_items:
            if current_len + len(item) > max_chars and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_len = 0
            current_batch.append(item)
            current_len += len(item)
        if current_batch:
            batches.append(current_batch)

        current_description = concept.description

        for batch in batches:
            kw_text = "\n".join(batch)
            prompt = (
                f'Текущее описание концепта "{concept.canonical_name}":\n'
                f"{current_description}\n\n"
                f"Новые ключевые слова с описаниями:\n{kw_text}\n\n"
                f"Обнови описание концепта, сохранив его суть, "
                f"но уточнив с учётом новых ключевых слов.\n"
                f'Верни JSON: {{"description": "...", "domain": "..."}}'
            )
            try:
                response = llm.invoke(prompt)
                if self._token_tracker:
                    self._token_tracker.track(response, "expand_description")
                content = response.content if hasattr(response, "content") else str(response)
                parsed = self._parse_json_response(content)
                if parsed.get("description"):
                    current_description = parsed["description"]
            except Exception as exc:
                logger.warning("Failed to regenerate description: %s", exc)

        return current_description

    def _verify_keyword_belongs(
        self,
        concept: ConceptNode,
        keyword: KeywordContext,
    ) -> tuple[bool, float, str]:
        """LLM verification: does this keyword belong to this concept?

        Returns:
            (belongs, confidence, relationship_description)
        """
        if not self._describer:
            return False, 0.0, ""

        from raptor_pipeline.summarizer.llm_summarizer import _build_llm
        llm = _build_llm(self.cfg.llm)

        prompt = (
            f'Концепт: "{concept.canonical_name}" ({concept.domain})\n'
            f"Описание концепта: {concept.description}\n\n"
            f'Ключевое слово: "{keyword.word}"\n'
            f"Описание слова: {keyword.description}\n\n"
            f"Может ли это ключевое слово относиться к данному концепту?\n"
            f'Ответь JSON: {{"belongs": true/false, "confidence": 0.0-1.0, '
            f'"relationship": "описание как связаны"}}'
        )

        try:
            response = llm.invoke(prompt)
            if self._token_tracker:
                self._token_tracker.track(response, "expand_verify")
            content = response.content if hasattr(response, "content") else str(response)
            parsed = self._parse_json_response(content)
            return (
                bool(parsed.get("belongs", False)),
                float(parsed.get("confidence", 0.0)),
                str(parsed.get("relationship", "")),
            )
        except Exception as exc:
            logger.warning("LLM verification failed for '%s': %s", keyword.word, exc)
            return False, 0.0, ""

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from LLM response, handling markdown fences and think tags."""
        import re
        text = text.strip()
        text = re.sub(
            r'<(thought|think)>.*?</\1>', '', text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if "```" in text:
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                text = match.group(1)
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {}

    def _store_evolved_to(self, from_id: str, to_id: str) -> None:
        """Create EVOLVED_TO edge between concept versions."""
        with self._gs._driver.session(database=self._gs._database) as session:
            session.run(
                """
                MATCH (a:Concept {id: $from_id})
                MATCH (b:Concept {id: $to_id})
                MERGE (a)-[:EVOLVED_TO]->(b)
                """,
                from_id=from_id,
                to_id=to_id,
            )

    def _store_instance_of_for_words(
        self, words: list[str], concept_id: str,
    ) -> None:
        """Create INSTANCE_OF edges from specific Keyword words to a Concept."""
        with self._gs._driver.session(database=self._gs._database) as session:
            for word in words:
                session.run(
                    """
                    MATCH (k:Keyword {word: $word})
                    MATCH (c:Concept {id: $concept_id})
                    MERGE (k)-[:INSTANCE_OF]->(c)
                    """,
                    word=word,
                    concept_id=concept_id,
                )
