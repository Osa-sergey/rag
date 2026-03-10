"""TopicModeler — BERTopic-based topic discovery for Habr articles.

Two modes:
  train        — Fit BERTopic on all articles, save model, update Neo4j.
  add_article  — Predict topic for a new article using saved model.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from omegaconf import DictConfig

from document_parser.text_extractor import load_yaml, flatten_blocks, render_block
from stores.graph_store import Neo4jGraphStore
from topic_modeler.metadata_loader import ArticleMeta, load_metadata

logger = logging.getLogger(__name__)


class TopicModeler:
    """BERTopic wrapper for cross-article topic modelling."""

    def __init__(self, cfg: DictConfig) -> None:
        self._cfg = cfg

        # Embedding provider (reuse raptor_pipeline's provider)
        from raptor_pipeline.embeddings.providers import create_embedding_provider
        self._embedder = create_embedding_provider(cfg.embeddings)

        # Graph store
        self._graph_store = Neo4jGraphStore(cfg.stores.neo4j)
        self._graph_store.ensure_indexes()

        # Paths
        self._model_dir = Path(cfg.get("model_dir", "outputs/bertopic_model"))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def train(
        self,
        input_dir: Path,
        csv_paths: list[Path],
    ) -> dict:
        """Fit BERTopic on all articles, store topics in Neo4j, save model."""

        # 1. Load texts
        texts, article_ids = self._load_article_texts(input_dir)
        if len(texts) < 3:
            logger.error("Need at least 3 articles to train BERTopic, got %d", len(texts))
            return {"error": "too_few_articles", "count": len(texts)}

        logger.info("Loaded %d article texts for training", len(texts))

        # 2. Load & store metadata
        meta_map = load_metadata(csv_paths)
        matched = 0
        for art_id in article_ids:
            meta = meta_map.get(art_id)
            if meta:
                self._store_meta(art_id, meta)
                matched += 1
        logger.info("Metadata: matched %d / %d articles from CSV", matched, len(article_ids))

        # 3. Compute embeddings
        logger.info("Computing embeddings for %d articles...", len(texts))
        embeddings = np.array(self._embedder.embed_texts(texts))

        # 4. Build & fit BERTopic
        topic_model = self._build_topic_model()
        logger.info("Fitting BERTopic model...")
        topics, probs = topic_model.fit_transform(texts, embeddings=embeddings)

        # 5. Store topics in Neo4j
        topic_info = topic_model.get_topics()
        n_topics = 0
        for topic_id, words_scores in topic_info.items():
            if topic_id == -1:
                continue
            top_words = [w for w, _ in words_scores[:15]]
            label = " | ".join(top_words[:3])
            self._graph_store.store_topic(topic_id, label, top_words)
            n_topics += 1

        # 6. Link articles to topics
        for art_id, topic_id in zip(article_ids, topics):
            if topic_id == -1:
                continue
            self._graph_store.link_article_to_topic(art_id, int(topic_id))

        # 7. Save model
        self._model_dir.mkdir(parents=True, exist_ok=True)
        topic_model.save(
            str(self._model_dir),
            serialization="safetensors",
            save_ctfidf=True,
            save_embedding_model=False,
        )
        logger.info("Model saved to %s", self._model_dir)

        # 8. Summary
        outliers = sum(1 for t in topics if t == -1)
        logger.info(
            "BERTopic training complete: %d topics, %d articles assigned, %d outliers",
            n_topics, len(topics) - outliers, outliers,
        )

        return {
            "n_articles": len(texts),
            "n_topics": n_topics,
            "n_assigned": len(topics) - outliers,
            "n_outliers": outliers,
            "model_dir": str(self._model_dir),
        }

    # ------------------------------------------------------------------
    def add_article(self, yaml_path: Path, csv_paths: list[Path] | None = None) -> dict:
        """Predict topic for a new article using a saved model."""
        from bertopic import BERTopic

        # 1. Load model
        if not self._model_dir.exists():
            logger.error("No saved model found at %s. Run train first.", self._model_dir)
            return {"error": "no_model"}

        logger.info("Loading model from %s ...", self._model_dir)
        topic_model = BERTopic.load(str(self._model_dir))

        # 2. Load article text
        text, article_id = self._load_single_article(yaml_path)
        if not text:
            return {"error": "empty_text", "article_id": article_id}

        # 3. Metadata
        if csv_paths:
            meta_map = load_metadata(csv_paths)
            meta = meta_map.get(article_id)
            if meta:
                self._store_meta(article_id, meta)

        # 4. Compute embedding & predict
        embedding = np.array(self._embedder.embed_texts([text]))
        topics, probs = topic_model.transform([text], embeddings=embedding)
        topic_id = int(topics[0])

        if topic_id == -1:
            logger.warning("Article %s classified as outlier (topic -1)", article_id)
            return {"article_id": article_id, "topic_id": -1, "topic_label": "outlier"}

        # 5. Store link
        self._graph_store.link_article_to_topic(article_id, topic_id)

        # 6. Get topic label
        topic_words = topic_model.get_topic(topic_id)
        top_words = [w for w, _ in topic_words[:5]] if topic_words else []
        label = " | ".join(top_words[:3])

        logger.info("Article %s → Topic %d (%s)", article_id, topic_id, label)
        return {
            "article_id": article_id,
            "topic_id": topic_id,
            "topic_label": label,
            "topic_keywords": top_words,
        }

    # ------------------------------------------------------------------
    def close(self) -> None:
        self._graph_store.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_article_texts(self, input_dir: Path) -> tuple[list[str], list[str]]:
        """Load full article texts from parsed_yaml directory."""
        texts: list[str] = []
        article_ids: list[str] = []

        files = sorted(input_dir.glob("*.yaml"))
        logger.info("Found %d YAML files in %s", len(files), input_dir)

        # Deduplicate by article_id (keep first occurrence)
        seen_ids: set[str] = set()

        for path in files:
            try:
                data = load_yaml(path)
                article_id = str(data.get("article_id", path.stem))
                if article_id in seen_ids:
                    continue

                document = data.get("document", [])
                blocks = flatten_blocks(document)
                full_text = "\n\n".join(
                    render_block(b) for b in blocks
                    if render_block(b).strip()
                )
                if full_text.strip():
                    texts.append(full_text)
                    article_ids.append(article_id)
                    seen_ids.add(article_id)
            except Exception:
                logger.exception("Failed to read %s", path.name)

        return texts, article_ids

    def _load_single_article(self, yaml_path: Path) -> tuple[str, str]:
        """Load text and article_id from a single YAML file."""
        data = load_yaml(yaml_path)
        article_id = str(data.get("article_id", yaml_path.stem))
        document = data.get("document", [])
        blocks = flatten_blocks(document)
        full_text = "\n\n".join(
            render_block(b) for b in blocks
            if render_block(b).strip()
        )
        return full_text, article_id

    def _store_meta(self, article_id: str, meta: ArticleMeta) -> None:
        """Store article metadata in Neo4j."""
        self._graph_store.store_article_metadata(article_id, {
            "author": meta.author,
            "reading_time": meta.reading_time,
            "complexity": meta.complexity,
            "labels": meta.labels,
            "tags": meta.tags,
            "hubs": meta.hubs,
        })

    def _build_topic_model(self):
        """Build BERTopic with configurable sub-components."""
        from bertopic import BERTopic
        from umap import UMAP
        from hdbscan import HDBSCAN
        from sklearn.feature_extraction.text import CountVectorizer

        cfg = self._cfg

        # UMAP
        umap_cfg = cfg.get("umap", {})
        umap_model = UMAP(
            n_neighbors=umap_cfg.get("n_neighbors", 15),
            n_components=umap_cfg.get("n_components", 5),
            min_dist=umap_cfg.get("min_dist", 0.1),
            metric=umap_cfg.get("metric", "cosine"),
            random_state=42,
        )

        # HDBSCAN
        hdbscan_cfg = cfg.get("hdbscan", {})
        hdbscan_model = HDBSCAN(
            min_cluster_size=hdbscan_cfg.get("min_cluster_size", 5),
            min_samples=hdbscan_cfg.get("min_samples", 1),
            metric=hdbscan_cfg.get("metric", "euclidean"),
            cluster_selection_method=hdbscan_cfg.get("cluster_selection_method", "eom"),
            prediction_data=True,
        )

        # Vectorizer
        vec_cfg = cfg.get("vectorizer", {})
        ngram_range = tuple(vec_cfg.get("ngram_range", [1, 2]))
        vectorizer_model = CountVectorizer(
            min_df=vec_cfg.get("min_df", 2),
            ngram_range=ngram_range,
            stop_words=vec_cfg.get("stop_words", None),
        )

        # Representation models
        representation_models = {}
        rep_cfg = cfg.get("representation", {})
        if rep_cfg.get("use_keybert", True):
            from bertopic.representation import KeyBERTInspired
            kb_cfg = rep_cfg.get("keybert", {})
            representation_models["KeyBERT"] = KeyBERTInspired(
                top_n_words=kb_cfg.get("top_n_words", 10),
            )
        if rep_cfg.get("use_mmr", True):
            from bertopic.representation import MaximalMarginalRelevance
            mmr_cfg = rep_cfg.get("mmr", {})
            representation_models["MMR"] = MaximalMarginalRelevance(
                diversity=mmr_cfg.get("diversity", 0.3),
            )

        # BERTopic
        bt_cfg = cfg.get("bertopic", {})
        nr_topics = bt_cfg.get("nr_topics", None)

        topic_model = BERTopic(
            language=bt_cfg.get("language", "russian"),
            nr_topics=nr_topics,
            top_n_words=bt_cfg.get("top_n_words", 15),
            min_topic_size=bt_cfg.get("min_topic_size", 3),
            umap_model=umap_model,
            hdbscan_model=hdbscan_model,
            vectorizer_model=vectorizer_model,
            representation_model=representation_models if representation_models else None,
            calculate_probabilities=False,
            verbose=True,
        )

        return topic_model
