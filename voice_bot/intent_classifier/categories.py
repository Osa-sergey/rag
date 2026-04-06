"""Expense category classifier using embedding-based cosine similarity.

Maps free-form expense descriptions to predefined categories using
the same embedding model as the intent classifier.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

from voice_bot.intent_classifier.classifier import EmbeddingProvider

logger = logging.getLogger(__name__)


@dataclass
class CategoryDef:
    """Category with example descriptions for embedding computation."""

    name: str
    display_name: str
    examples: list[str]
    embedding: np.ndarray | None = field(default=None, repr=False)


class CategoryClassifier:
    """Classify expense descriptions into categories via cosine similarity.

    Usage::

        cats = [
            CategoryDef("food", "Еда", ["обед в кафе", "продукты"]),
            CategoryDef("transport", "Транспорт", ["такси", "метро"]),
        ]
        clf = CategoryClassifier(embedder, cats)
        category = clf.classify("заплатил за такси")
        # category.name == "transport"
    """

    def __init__(
        self,
        embedder: EmbeddingProvider,
        categories: list[CategoryDef],
        *,
        fallback_category: str = "other",
    ) -> None:
        self._embedder = embedder
        self._categories = categories
        self._fallback = fallback_category

        self._build_category_embeddings()

    def classify(self, text: str) -> CategoryDef:
        """Return the best-matching category for a text description."""
        query_emb = np.array(self._embedder.embed_query(text))

        best_cat = self._categories[0]
        best_score = -1.0

        for cat in self._categories:
            sim = self._cosine_similarity(query_emb, cat.embedding)
            if sim > best_score:
                best_score = sim
                best_cat = cat

        logger.debug(
            "Category '%s' (%.3f) for text: '%s'",
            best_cat.name,
            best_score,
            text[:80],
        )
        return best_cat

    def get_all_scores(self, text: str) -> list[tuple[CategoryDef, float]]:
        """Return all categories ranked by similarity."""
        query_emb = np.array(self._embedder.embed_query(text))
        results = []
        for cat in self._categories:
            sim = self._cosine_similarity(query_emb, cat.embedding)
            results.append((cat, float(sim)))
        return sorted(results, key=lambda x: x[1], reverse=True)

    # ── Internal ──────────────────────────────────────────────

    def _build_category_embeddings(self) -> None:
        """Pre-compute mean embeddings for each category."""
        for cat in self._categories:
            if not cat.examples:
                logger.warning("Category '%s' has no examples, skipping", cat.name)
                continue

            vecs = self._embedder.embed_texts(cat.examples)
            cat.embedding = np.mean(vecs, axis=0)
            norm = np.linalg.norm(cat.embedding)
            if norm > 0:
                cat.embedding = cat.embedding / norm

            logger.info(
                "Category '%s': %d examples → embedding",
                cat.name,
                len(cat.examples),
            )

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))
