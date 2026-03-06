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

    # ------------------------------------------------------------------
    def init_stores(self) -> None:
        """Create collections / indexes if they don't exist yet."""
        self._vector_store.ensure_collection()
        self._graph_store.ensure_indexes()

    # ------------------------------------------------------------------
    def process_file(self, yaml_path: Path) -> dict[str, Any]:
        """Run the full pipeline on a single YAML file.

        Returns a summary dict with counts of chunks, nodes, keywords, etc.
        """
        data = load_yaml(yaml_path)
        article_id = data.get("article_id", yaml_path.stem)
        document = data.get("document", [])

        logger.info("> Processing article '%s' from %s", article_id, yaml_path.name)

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
        
        # 3.1: Extract raw keywords
        raw_keywords_by_node = {}
        all_raw_keywords = []
        
        from raptor_pipeline.knowledge_graph.base import Keyword
        from concurrent.futures import ThreadPoolExecutor

        max_workers = self.cfg.get("max_concurrency", 4)

        def extract_node_kws(node):
            kws = self._kw_extractor.extract(node.text, node.node_id)
            for k in kws:
                k.word = k.word.strip()
                if not (len(k.word) > 1 and k.word.isupper()):
                    k.word = k.word.lower()
            return node.node_id, kws

        logger.info("  + Extracting raw keywords from %d nodes (parallel, workers=%d)...", len(nodes), max_workers)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            kw_results = list(executor.map(extract_node_kws, nodes))

        for node_id, kws in kw_results:
            raw_keywords_by_node[node_id] = kws
            for k in kws:
                all_raw_keywords.append({"word": k.word, "category": k.category})

        # 3.2: Refine keywords globally
        logger.info("  + Refining %d raw keywords globally...", len(all_raw_keywords))
        refined_list = self._kw_refiner.refine(all_raw_keywords)
        
        raw_to_refined = {}
        all_refined_keywords: list[Keyword] = []
        
        for item in refined_list:
            refined_word = item.get("refined_word", "").strip()
            category = item.get("category", "other")
            if not refined_word:
                continue
            
            for orig in item.get("original_words", []):
                raw_to_refined[orig.strip()] = {"word": refined_word, "category": category}

        # 3.3: Map keywords to chunks and extract relations
        all_relations = []
        keywords_by_node: dict[str, list[str]] = {}
        
        nodes_with_refined_kws = []
        for node in nodes:
            node_refined_kws = []
            node_kw_words = set()
            
            for raw_kw in raw_keywords_by_node[node.node_id]:
                mapping = raw_to_refined.get(raw_kw.word)
                if mapping:
                    refined_word = mapping["word"]
                    if refined_word not in node_kw_words:
                        node_kw_words.add(refined_word)
                        refined_obj = Keyword(
                            word=refined_word, 
                            category=mapping["category"], 
                            confidence=raw_kw.confidence, 
                            chunk_id=node.node_id
                        )
                        node_refined_kws.append(refined_obj)
                        all_refined_keywords.append(refined_obj)
            
            keywords_by_node[node.node_id] = list(node_kw_words)
            if node_refined_kws:
                nodes_with_refined_kws.append((node, node_refined_kws))

        # Step 3.4: Extract Relations using REFINED keywords (parallel)
        def extract_node_rels(node_item):
            node, refined_kws = node_item
            rels = self._rel_extractor.extract(node.text, refined_kws, node.node_id)
            for r in rels:
                r.subject = r.subject.strip()
                r.object = r.object.strip()
                r.predicate = r.predicate.lower().strip()
            return rels

        logger.info("  + Extracting relations from %d nodes (parallel, workers=%d)...", len(nodes_with_refined_kws), max_workers)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            rel_results = list(executor.map(extract_node_rels, nodes_with_refined_kws))

        for rels in rel_results:
            all_relations.extend(rels)

        # Deduplicate refined keywords for reporting
        unique_kws = {k.word for k in all_refined_keywords}
        
        logger.info(
            "  + Final: %d unique keywords, %d relations from all tree levels",
            len(unique_kws),
            len(all_relations),
        )

        # ── Step 4: Store in Qdrant ───────────────────────────
        self._vector_store.upsert_nodes(nodes, keywords_by_node)
        logger.info("  + Stored %d nodes in Qdrant", len(nodes))

        # ── Step 5: Store in Neo4j ────────────────────────────
        self._graph_store.store_article(article_id)
        # We store all extracted instances; Neo4jGraphStore should handle merges
        self._graph_store.store_keywords(article_id, all_refined_keywords)
        self._graph_store.store_relations(article_id, all_relations)
        logger.info("  + Stored KG in Neo4j")

        return {
            "article_id": article_id,
            "chunks": len(chunks),
            "raptor_nodes": len(nodes),
            "keywords": len(all_refined_keywords),
            "unique_keywords": len(unique_kws),
            "relations": len(all_relations),
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
        return results

    # ------------------------------------------------------------------
    def close(self) -> None:
        """Clean up connections."""
        self._graph_store.close()
