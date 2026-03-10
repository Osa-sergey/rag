"""BERTopic-based keyword extraction across document collections."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from omegaconf import DictConfig

from raptor_pipeline.knowledge_graph.base import Keyword

if TYPE_CHECKING:
    from raptor_pipeline.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class BERTopicKeywordExtractor:
    """Extract collection-level keywords using BERTopic.

    Unlike the LLM-based extractor (per-chunk), this operates on a
    collection of **full article texts** to discover global topics and
    their representative words.  Each topic's top words become keywords.

    The same embedding provider used by the rest of the pipeline is
    reused here for consistency.
    """

    def __init__(
        self,
        cfg: DictConfig,
        embedding_provider: BaseEmbeddingProvider,
    ) -> None:
        self._n_topics: str | int = cfg.get("n_topics", "auto")
        self._top_n_words: int = cfg.get("top_n_words", 10)
        self._min_topic_size: int = cfg.get("min_topic_size", 3)
        self._embedder = embedding_provider
        logger.info(
            "BERTopicKeywordExtractor ready (n_topics=%s, top_n=%d, min_size=%d)",
            self._n_topics, self._top_n_words, self._min_topic_size,
        )

    # ------------------------------------------------------------------
    def extract(
        self,
        texts: list[str],
        article_ids: list[str] | None = None,
    ) -> tuple[list[Keyword], dict[str, list[str]]]:
        """Run BERTopic on *texts* and return extracted keywords.

        Args:
            texts:       Full article texts (one string per article).
            article_ids: Optional parallel list of article IDs so that
                         keywords can be mapped back to source articles.

        Returns:
            A tuple of:
              - Flat list of Keyword objects (one per unique topic word).
              - Dict mapping article_id -> list of topic keywords found
                in that article.  Empty if *article_ids* is None.
        """
        from bertopic import BERTopic
        from sklearn.feature_extraction.text import CountVectorizer

        if len(texts) < self._min_topic_size:
            logger.warning(
                "BERTopic: only %d documents (< min_topic_size=%d), skipping",
                len(texts), self._min_topic_size,
            )
            return [], {}

        # Pre-compute embeddings using the shared provider
        logger.info("BERTopic: computing embeddings for %d documents...", len(texts))
        embeddings = self._embedder.embed_texts(texts)

        import numpy as np
        emb_array = np.array(embeddings)

        # Build model
        # Use a simple vectorizer that works with Russian
        vectorizer = CountVectorizer(
            stop_words=None,  # BERTopic handles this internally
            ngram_range=(1, 2),
        )

        n_topics = None if self._n_topics == "auto" else int(self._n_topics)

        topic_model = BERTopic(
            nr_topics=n_topics,
            top_n_words=self._top_n_words,
            min_topic_size=self._min_topic_size,
            vectorizer_model=vectorizer,
            calculate_probabilities=False,
            verbose=False,
        )

        logger.info("BERTopic: fitting model...")
        topics, _ = topic_model.fit_transform(texts, embeddings=emb_array)

        # Extract keywords from topics
        topic_info = topic_model.get_topics()
        all_keywords: list[Keyword] = []
        seen_words: set[str] = set()

        for topic_id, words_scores in topic_info.items():
            if topic_id == -1:  # outlier topic
                continue
            for word, score in words_scores:
                word_clean = word.strip().lower()
                if word_clean and word_clean not in seen_words and len(word_clean) > 1:
                    seen_words.add(word_clean)
                    all_keywords.append(Keyword(
                        word=word_clean,
                        category="bertopic",
                        confidence=round(max(0.0, min(1.0, score)), 3),
                        chunk_id=f"topic_{topic_id}",
                    ))

        logger.info(
            "BERTopic: found %d topics, %d unique keywords",
            len([t for t in topic_info if t != -1]),
            len(all_keywords),
        )

        # Map keywords back to articles
        article_keywords: dict[str, list[str]] = {}
        if article_ids:
            for idx, (topic_id, art_id) in enumerate(zip(topics, article_ids)):
                if topic_id == -1:
                    continue
                topic_words = [w for w, _ in topic_info.get(topic_id, [])]
                if art_id not in article_keywords:
                    article_keywords[art_id] = []
                for w in topic_words:
                    w_clean = w.strip().lower()
                    if w_clean and w_clean not in article_keywords[art_id]:
                        article_keywords[art_id].append(w_clean)

        return all_keywords, article_keywords
