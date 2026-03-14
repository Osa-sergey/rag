"""Concept clusterer — group keywords by semantic similarity."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from interfaces import BaseConceptClusterer
from concept_builder.models import KeywordContext

logger = logging.getLogger(__name__)


class ConceptClusterer(BaseConceptClusterer):
    """Cluster keyword contexts into concept groups using cosine similarity.

    Same keyword in different domains may produce different descriptions
    and embeddings, so they end up in different clusters → different Concepts.
    """

    def cluster(
        self,
        keyword_contexts: list[KeywordContext],
        similarity_threshold: float = 0.85,
    ) -> list[list[KeywordContext]]:
        """Group keyword contexts by cosine similarity on description embeddings.

        Algorithm:
          1. Sort by word (alphabetical) for determinism.
          2. For each keyword, check similarity to existing cluster centroids.
          3. If similarity ≥ threshold → add to that cluster.
          4. Otherwise → create new cluster.
        """
        if not keyword_contexts:
            return []

        # Filter out items without embeddings
        items = [kc for kc in keyword_contexts if kc.embedding is not None]
        if not items:
            logger.warning("No keyword contexts with embeddings to cluster")
            return []

        # Sort by word for deterministic results
        items.sort(key=lambda kc: kc.word.lower())

        clusters: list[list[KeywordContext]] = []
        centroids: list[np.ndarray] = []

        for kc in items:
            kc_vec = np.array(kc.embedding, dtype=np.float32)

            best_idx = -1
            best_sim = -1.0

            for idx, centroid in enumerate(centroids):
                sim = self._cosine_similarity(kc_vec, centroid)
                if sim > best_sim:
                    best_sim = sim
                    best_idx = idx

            if best_sim >= similarity_threshold and best_idx >= 0:
                # Add to existing cluster
                clusters[best_idx].append(kc)
                # Update centroid (running average)
                n = len(clusters[best_idx])
                centroids[best_idx] = (
                    centroids[best_idx] * (n - 1) + kc_vec
                ) / n
            else:
                # New cluster
                clusters.append([kc])
                centroids.append(kc_vec.copy())

        logger.info(
            "Clustered %d keyword contexts into %d concept groups "
            "(threshold=%.2f)",
            len(items), len(clusters), similarity_threshold,
        )

        # Log cluster details
        for i, cluster in enumerate(clusters):
            words = {kc.word for kc in cluster}
            articles = {kc.article_id for kc in cluster}
            logger.debug(
                "  Cluster %d: words=%s, articles=%s",
                i, words, articles,
            )

        return clusters

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
