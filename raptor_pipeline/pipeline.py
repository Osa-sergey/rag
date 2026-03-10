"""RAPTOR pipeline orchestrator — ties all modules together."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from omegaconf import DictConfig

from document_parser.text_extractor import load_yaml
from raptor_pipeline.chunker.base import Chunk
from raptor_pipeline.chunker.hybrid_chunker import HybridChunker
from raptor_pipeline.chunker.section_chunker import SectionChunker
from raptor_pipeline.chunker.semantic_chunker import SemanticChunker
from raptor_pipeline.embeddings.providers import create_embedding_provider
from raptor_pipeline.knowledge_graph.keyword_extractor import LLMKeywordExtractor
from raptor_pipeline.knowledge_graph.keyword_refiner import LLMKeywordRefiner
from raptor_pipeline.knowledge_graph.relation_extractor import LLMRelationExtractor
from raptor_pipeline.raptor.tree_builder import RaptorNode, RaptorTreeBuilder
from raptor_pipeline.stores.graph_store import Neo4jGraphStore
from raptor_pipeline.stores.vector_store import QdrantVectorStore
from raptor_pipeline.summarizer.llm_summarizer import LLMSummarizer
from raptor_pipeline.knowledge_graph.link_parser import (
    extract_links_from_text,
    parse_article_version,
    ExtractedLink,
)

logger = logging.getLogger(__name__)


class RaptorPipeline:
    """End-to-end RAPTOR pipeline: YAML → chunks → tree → stores.

    Execution steps:
      1. Load YAML document(s)
      2. Chunk text  (section or semantic chunker)
      3. Build RAPTOR tree (embed → cluster → summarise → repeat)
      4. Extract keywords & relations
      5. Store embeddings + metadata in Qdrant
      6. Store knowledge graph in Neo4j
    """

    def __init__(self, cfg: DictConfig) -> None:
        self.cfg = cfg

        # Embedding provider (shared by chunker, RAPTOR, stores)
        self._embedder = create_embedding_provider(cfg.embeddings)

        # Chunker
        chunker_type = cfg.chunker.get("type", "section")
        if chunker_type == "semantic":
            self._chunker = SemanticChunker(cfg.chunker, self._embedder)
        elif chunker_type == "hybrid":
            self._chunker = HybridChunker(cfg.chunker, self._embedder)
        else:
            self._chunker = SectionChunker(cfg.chunker)

        # Summariser
        self._summarizer = LLMSummarizer(cfg.summarizer, cfg.prompts.summarize)

        # RAPTOR tree builder
        self._tree_builder = RaptorTreeBuilder(
            cfg.raptor, self._embedder, self._summarizer
        )

        # Knowledge graph extractors
        self._kw_extractor = LLMKeywordExtractor(
            cfg.knowledge_graph, cfg.prompts.keywords
        )
        self._kw_refiner = LLMKeywordRefiner(
            cfg.knowledge_graph, cfg.prompts.refine_keywords
        )
        self._rel_extractor = LLMRelationExtractor(
            cfg.knowledge_graph, cfg.prompts.relations
        )

        # Stores
        self._vector_store = QdrantVectorStore(cfg.stores.qdrant)
        self._graph_store = Neo4jGraphStore(cfg.stores.neo4j)

        # BERTopic (optional, runs across multiple articles)
        self._use_bertopic: bool = cfg.get("use_bertopic", False)
        self._bertopic_extractor = None
        if self._use_bertopic:
            from raptor_pipeline.knowledge_graph.bertopic_extractor import BERTopicKeywordExtractor
            self._bertopic_extractor = BERTopicKeywordExtractor(
                cfg.bertopic, self._embedder,
            )

        # Parallelism & batching
        self._max_workers: int = cfg.get("max_concurrency", 8)
        self._batch_size: int = cfg.get("batch_size", 8)

    # ------------------------------------------------------------------
    def init_stores(self) -> None:
        """Create collections / indexes if they don't exist yet."""
        self._vector_store.ensure_collection()
        self._graph_store.ensure_indexes()

    # ------------------------------------------------------------------
    @staticmethod
    def _run_in_batches(func, items: list, batch_size: int, max_workers: int) -> list:
        """Execute *func* over *items* in controlled batches.

        Each batch of up to *batch_size* items is processed in parallel
        using a ThreadPoolExecutor with *max_workers* threads.  The next
        batch starts only after the current one completes, which prevents
        flooding the LLM server with too many simultaneous requests.

        Returns a flat list of results in the same order as *items*.
        """
        from concurrent.futures import ThreadPoolExecutor

        all_results: list = []
        total = len(items)
        n_batches = (total + batch_size - 1) // batch_size

        for batch_idx in range(n_batches):
            start = batch_idx * batch_size
            end = min(start + batch_size, total)
            batch = items[start:end]

            logger.debug(
                "    batch %d/%d  (%d items, workers=%d)",
                batch_idx + 1, n_batches, len(batch), max_workers,
            )

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                batch_results = list(executor.map(func, batch))
            all_results.extend(batch_results)

        return all_results

    # ------------------------------------------------------------------
    def process_file(self, yaml_path: Path) -> dict[str, Any]:
        """Run the full pipeline on a single YAML file.

        Returns a summary dict with counts of chunks, nodes, keywords, etc.
        """
        from raptor_pipeline.knowledge_graph.base import Keyword

        data = load_yaml(yaml_path)
        article_id = data.get("article_id", yaml_path.stem)
        document = data.get("document", [])

        # Parse version from filename
        article_name, version = parse_article_version(yaml_path.name)

        logger.info(
            "> Processing article '%s' (name='%s', version='%s') from %s",
            article_id, article_name, version, yaml_path.name,
        )

        # ── Step 1: Chunking ──────────────────────────────────
        chunks: list[Chunk] = self._chunker.chunk(document, article_id)
        logger.info("  + %d chunks created", len(chunks))

        if not chunks:
            logger.warning("  No chunks produced, skipping article")
            return {"article_id": article_id, "chunks": 0}

        # ── Step 2: RAPTOR tree ───────────────────────────────
        nodes: list[RaptorNode] = self._tree_builder.build(chunks)
        logger.info("  + RAPTOR tree: %d total nodes", len(nodes))

        # ── Step 3: Knowledge graph extraction (Hierarchical) ──
        logger.info("  + Extracting Knowledge Graph from %d nodes...", len(nodes))

        max_text_chars: int = self.cfg.get("max_text_chars", 2000)

        # 3.0: Extract links from all nodes BEFORE keyword extraction.
        # Link display texts become protected keywords (not refiner-editable).
        all_article_links: list[ExtractedLink] = []
        link_keywords_by_node: dict[str, list[Keyword]] = {}

        for node in nodes:
            node_links = extract_links_from_text(node.text)
            # Tag each link with its source chunk
            for lnk in node_links:
                lnk.source_chunk_ids.append(node.node_id)
            all_article_links.extend(node_links)
            link_kws = []
            for lnk in node_links:
                # Use display text as atomic keyword
                display = lnk.display.strip()
                if display and len(display) > 1:
                    link_kws.append(Keyword(
                        word=display,
                        category="reference",
                        confidence=1.0,
                        chunk_id=node.node_id,
                    ))
            link_keywords_by_node[node.node_id] = link_kws

        # Deduplicate article-level links, merging source_chunk_ids
        seen_link_targets: dict[str, ExtractedLink] = {}
        unique_links: list[ExtractedLink] = []
        for lnk in all_article_links:
            key = f"{lnk.target_article_id.lower()}#{lnk.section}"
            if key not in seen_link_targets:
                seen_link_targets[key] = lnk
                unique_links.append(lnk)
            else:
                # Merge source chunk IDs into existing link
                existing = seen_link_targets[key]
                for cid in lnk.source_chunk_ids:
                    if cid not in existing.source_chunk_ids:
                        existing.source_chunk_ids.append(cid)

        if unique_links:
            logger.info("  + Extracted %d unique links from text", len(unique_links))
            for lnk in unique_links:
                logger.info(
                    "    %s → target='%s' section='%s' display='%s'",
                    lnk.link_type, lnk.target, lnk.section, lnk.display,
                )

        # 3.1: Extract raw keywords ─── batched parallel ───────
        def _extract_node_kws(node: RaptorNode):
            orig_len = len(node.text)
            text = node.text[:max_text_chars]
            if orig_len > max_text_chars:
                logger.debug(
                    "    [kw] node %s truncated: %d -> %d chars",
                    node.node_id, orig_len, max_text_chars,
                )
            kws = self._kw_extractor.extract(text, node.node_id)
            for k in kws:
                k.word = k.word.strip()
                if not (len(k.word) > 1 and k.word.isupper()):
                    k.word = k.word.lower()
            return node.node_id, kws

        logger.info(
            "  + Extracting raw keywords from %d nodes "
            "(batch_size=%d, workers=%d, max_text=%d chars)...",
            len(nodes), self._batch_size, self._max_workers, max_text_chars,
        )
        kw_results = self._run_in_batches(
            _extract_node_kws, nodes,
            self._batch_size, self._max_workers,
        )

        raw_keywords_by_node: dict[str, list] = {}
        all_raw_keywords: list[dict] = []
        # Set of protected keywords (from links) — not sent to refiner
        protected_keywords: set[str] = set()

        for node_id, kws in kw_results:
            # Merge link-based keywords with LLM-extracted keywords
            link_kws = link_keywords_by_node.get(node_id, [])
            combined = list(kws) + link_kws
            raw_keywords_by_node[node_id] = combined
            for k in combined:
                all_raw_keywords.append({"word": k.word, "category": k.category})
                if k.category == "reference":
                    protected_keywords.add(k.word.lower())

        # 3.2: Refine keywords globally — skip protected (link) keywords
        refiner_input = [
            kw for kw in all_raw_keywords
            if kw["word"].lower() not in protected_keywords
        ]
        logger.info(
            "  + Refining %d keywords globally (%d protected link-keywords skipped)...",
            len(refiner_input), len(protected_keywords),
        )
        refined_list = self._kw_refiner.refine(refiner_input)

        # Build mapping: original_word (lowercased) -> refined info.
        # Both sides are lowercased to avoid case-mismatch between
        # the extractor output and the refiner's `original_words`.
        raw_to_refined: dict[str, dict] = {}
        all_refined_keywords: list[Keyword] = []
        # Track which raw keywords were merged into each refined keyword
        refined_originals: dict[str, list[str]] = {}  # refined_word -> [raw words]

        for item in refined_list:
            refined_word = item.get("refined_word", "").strip()
            category = item.get("category", "other")
            if not refined_word:
                continue
            orig_words = item.get("original_words", [])
            for orig in orig_words:
                key = orig.strip().lower()
                raw_to_refined[key] = {"word": refined_word, "category": category}
            # Accumulate all originals for this refined word
            rw_key = refined_word.lower()
            if rw_key not in refined_originals:
                refined_originals[rw_key] = []
            for o in orig_words:
                o_stripped = o.strip()
                if o_stripped and o_stripped not in refined_originals[rw_key]:
                    refined_originals[rw_key].append(o_stripped)

        logger.info(
            "  + Refiner produced %d items, raw_to_refined map has %d entries",
            len(refined_list), len(raw_to_refined),
        )

        # 3.3: Map keywords to chunks.
        # If a raw keyword has no match in raw_to_refined (refiner
        # dropped it or returned a different spelling), use the raw
        # keyword as-is instead of silently losing it.
        keywords_by_node: dict[str, list[str]] = {}
        nodes_with_refined_kws: list[tuple] = []
        unmatched_count = 0

        for node in nodes:
            node_refined_kws: list[Keyword] = []
            node_kw_words: set[str] = set()

            for raw_kw in raw_keywords_by_node[node.node_id]:
                lookup_key = raw_kw.word.lower()
                mapping = raw_to_refined.get(lookup_key)

                if mapping:
                    word = mapping["word"]
                    category = mapping["category"]
                else:
                    # Fallback — keep the raw keyword as-is
                    word = raw_kw.word
                    category = raw_kw.category
                    unmatched_count += 1

                if word not in node_kw_words:
                    node_kw_words.add(word)
                    # Lookup which raw words were merged into this refined word
                    originals = refined_originals.get(word.lower(), [])
                    refined_obj = Keyword(
                        word=word,
                        category=category,
                        confidence=raw_kw.confidence,
                        chunk_id=node.node_id,
                        original_words=originals if originals else None,
                    )
                    node_refined_kws.append(refined_obj)
                    all_refined_keywords.append(refined_obj)

            keywords_by_node[node.node_id] = list(node_kw_words)
            if node_refined_kws:
                nodes_with_refined_kws.append((node, node_refined_kws))

        if unmatched_count:
            logger.warning(
                "  ! %d raw keywords had no match in refiner output "
                "(kept as-is)", unmatched_count,
            )

        # 3.4: Extract relations ─── batched parallel ──────────
        def _extract_node_rels(node_item):
            node, refined_kws = node_item
            orig_len = len(node.text)
            text = node.text[:max_text_chars]
            if orig_len > max_text_chars:
                logger.debug(
                    "    [rel] node %s truncated: %d -> %d chars",
                    node.node_id, orig_len, max_text_chars,
                )
            rels = self._rel_extractor.extract(text, refined_kws, node.node_id)
            for r in rels:
                r.subject = r.subject.strip()
                r.object = r.object.strip()
                r.predicate = r.predicate.lower().strip()
            return rels

        logger.info(
            "  + Extracting relations from %d nodes "
            "(batch_size=%d, workers=%d)...",
            len(nodes_with_refined_kws), self._batch_size, self._max_workers,
        )
        rel_results = self._run_in_batches(
            _extract_node_rels, nodes_with_refined_kws,
            self._batch_size, self._max_workers,
        )

        all_relations = []
        for rels in rel_results:
            all_relations.extend(rels)

        # Deduplicate refined keywords for reporting
        unique_kws = {k.word for k in all_refined_keywords}

        logger.info(
            "  + Final: %d unique keywords, %d relations from all tree levels",
            len(unique_kws),
            len(all_relations),
        )

        # ── Step 4: Article summary from RAPTOR tree ──────────
        # Collect root nodes (not a child of any other node).
        # Also collect leaf nodes that no summary covers — these
        # would be lost if we only looked at the top-level roots.
        all_children_ids: set[str] = set()
        for n in nodes:
            all_children_ids.update(n.children_ids)

        root_nodes = [n for n in nodes if n.node_id not in all_children_ids]
        # Separate: roots that are summaries vs orphan leaves
        summary_root_nodes = [n for n in root_nodes if n.level > 0]
        orphan_leaf_nodes = [n for n in root_nodes if n.level == 0]
        summary_texts = [n.text for n in summary_root_nodes]
        orphan_leaves = [n.text for n in orphan_leaf_nodes]

        all_summary_parts = summary_texts + orphan_leaves

        # Detailed logging: breakdown by type and level
        if summary_root_nodes or orphan_leaf_nodes:
            level_counts: dict[int, int] = {}
            for n in summary_root_nodes:
                level_counts[n.level] = level_counts.get(n.level, 0) + 1
            level_str = ", ".join(
                f"L{lv}: {cnt}" for lv, cnt in sorted(level_counts.items())
            )
            logger.info(
                "  + Article summary sources: %d total — "
                "%d summary nodes (%s) + %d orphan leaf chunks",
                len(all_summary_parts),
                len(summary_root_nodes),
                level_str if level_str else "none",
                len(orphan_leaf_nodes),
            )
            for n in summary_root_nodes:
                logger.info(
                    "    📝 [summary L%d] %s (%d chars, %d children)",
                    n.level, n.node_id, len(n.text), len(n.children_ids),
                )
            for n in orphan_leaf_nodes:
                logger.info(
                    "    📄 [orphan leaf] %s (%d chars)",
                    n.node_id, len(n.text),
                )

        if len(all_summary_parts) == 1:
            article_summary = all_summary_parts[0]
        elif all_summary_parts:
            logger.info(
                "  + Summarizing %d sources into final article summary...",
                len(all_summary_parts),
            )
            article_summary = self._summarizer.summarize(all_summary_parts)
        else:
            article_summary = ""

        logger.info("  + Article summary: %d chars", len(article_summary))

        # ── Step 5: Store in Qdrant ───────────────────────────
        self._vector_store.upsert_nodes(nodes, keywords_by_node)
        logger.info("  + Stored %d nodes in Qdrant", len(nodes))

        # ── Step 6: Store in Neo4j ────────────────────────────
        self._graph_store.store_article(
            article_id,
            summary=article_summary,
            article_name=article_name,
            version=version,
        )
        self._graph_store.store_keywords(article_id, all_refined_keywords)
        self._graph_store.store_relations(article_id, all_relations)
        if unique_links:
            self._graph_store.store_links(article_id, unique_links, version=version)
            logger.info("  + Stored %d cross-article links in Neo4j", len(unique_links))
        logger.info("  + Stored KG in Neo4j")

        return {
            "article_id": article_id,
            "article_name": article_name,
            "version": version,
            "chunks": len(chunks),
            "raptor_nodes": len(nodes),
            "keywords": len(all_refined_keywords),
            "unique_keywords": len(unique_kws),
            "relations": len(all_relations),
            "links": [
                {
                    "type": lnk.link_type,
                    "target": lnk.target,
                    "section": lnk.section,
                    "display": lnk.display,
                    "source_chunk_ids": lnk.source_chunk_ids,
                }
                for lnk in unique_links
            ],
            "article_summary": article_summary[:200] + "..." if len(article_summary) > 200 else article_summary,
        }

    # ------------------------------------------------------------------
    def process_directory(self, input_dir: Path, pattern: str = "*.yaml") -> list[dict]:
        """Batch-process all YAML files in a directory."""
        results = []
        files = sorted(input_dir.glob(pattern))
        logger.info("Found %d files in %s", len(files), input_dir)

        for path in files:
            try:
                result = self.process_file(path)
                results.append(result)
            except Exception:
                logger.exception("Failed to process %s", path.name)

        # ── BERTopic: collection-level keyword extraction ─────
        if self._use_bertopic and self._bertopic_extractor and results:
            self._run_bertopic(input_dir, files, results)

        return results

    # ------------------------------------------------------------------
    def _run_bertopic(
        self, input_dir: Path, files: list[Path], results: list[dict]
    ) -> None:
        """Run BERTopic on full article texts and store keywords."""
        from document_parser.text_extractor import load_yaml, flatten_blocks, render_block
        from raptor_pipeline.knowledge_graph.base import Keyword

        logger.info("BERTopic: loading full article texts...")
        article_texts: list[str] = []
        article_ids: list[str] = []

        for path in files:
            try:
                data = load_yaml(path)
                article_id = data.get("article_id", path.stem)
                document = data.get("document", [])
                blocks = flatten_blocks(document)
                full_text = "\n\n".join(
                    render_block(b) for b in blocks
                    if render_block(b).strip()
                )
                if full_text.strip():
                    article_texts.append(full_text)
                    article_ids.append(article_id)
            except Exception:
                logger.exception("BERTopic: failed to read %s", path.name)

        if len(article_texts) < 3:
            logger.warning(
                "BERTopic: only %d articles with text, need at least 3. Skipping.",
                len(article_texts),
            )
            return

        bt_keywords, article_kw_map = self._bertopic_extractor.extract(
            article_texts, article_ids,
        )

        # Store BERTopic keywords per article in Neo4j
        for art_id, kw_words in article_kw_map.items():
            kw_objects = [
                Keyword(word=w, category="bertopic", confidence=0.8, chunk_id="bertopic")
                for w in kw_words
            ]
            self._graph_store.store_keywords(art_id, kw_objects)

        logger.info(
            "BERTopic: stored %d collection-level keywords across %d articles",
            len(bt_keywords), len(article_kw_map),
        )

    # ------------------------------------------------------------------
    def close(self) -> None:
        """Clean up connections."""
        self._graph_store.close()
