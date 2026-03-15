"""Concept clusterer — group keywords by semantic similarity.

Two implementations:
  - GreedyConceptClusterer: greedy single-pass cosine similarity
  - HdbscanConceptClusterer: HDBSCAN density-based clustering
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from interfaces import BaseConceptClusterer
from concept_builder.models import KeywordContext

logger = logging.getLogger(__name__)


class GreedyConceptClusterer(BaseConceptClusterer):
    """Cluster keyword contexts using greedy single-pass cosine similarity.

    Algorithm:
      1. Sort by word (alphabetical) for determinism.
      2. For each keyword, check similarity to existing cluster centroids.
      3. If similarity ≥ threshold → add to that cluster.
      4. Otherwise → create new cluster.

    Same keyword in different domains may produce different descriptions
    and embeddings, so they end up in different clusters → different Concepts.
    """

    def cluster(
        self,
        keyword_contexts: list[KeywordContext],
        similarity_threshold: float = 0.85,
    ) -> list[list[KeywordContext]]:
        if not keyword_contexts:
            return []

        items = [kc for kc in keyword_contexts if kc.embedding is not None]
        if not items:
            logger.warning("No keyword contexts with embeddings to cluster")
            return []

        items.sort(key=lambda kc: kc.word.lower())

        clusters: list[list[KeywordContext]] = []
        centroids: list[np.ndarray] = []

        for kc in items:
            kc_vec = np.array(kc.embedding, dtype=np.float32)

            best_idx = -1
            best_sim = -1.0

            for idx, centroid in enumerate(centroids):
                sim = _cosine_similarity(kc_vec, centroid)
                if sim > best_sim:
                    best_sim = sim
                    best_idx = idx

            if best_sim >= similarity_threshold and best_idx >= 0:
                clusters[best_idx].append(kc)
                n = len(clusters[best_idx])
                centroids[best_idx] = (
                    centroids[best_idx] * (n - 1) + kc_vec
                ) / n
            else:
                clusters.append([kc])
                centroids.append(kc_vec.copy())

        logger.info(
            "Greedy clustered %d keywords into %d groups (threshold=%.2f)",
            len(items), len(clusters), similarity_threshold,
        )
        _log_clusters(clusters)
        return clusters


class HdbscanConceptClusterer(BaseConceptClusterer):
    """Cluster keyword contexts using HDBSCAN density-based clustering.

    HDBSCAN is better at finding clusters of varying densities
    and doesn't require specifying the number of clusters.
    The similarity_threshold is mapped to HDBSCAN's min_cluster_size
    and cluster_selection_epsilon.

    Requires: pip install hdbscan
    """

    def __init__(
        self,
        min_cluster_size: int = 2,
        min_samples: int = 1,
        cluster_selection_epsilon: float = 0.15,
        metric: str = "euclidean",
    ) -> None:
        self._min_cluster_size = min_cluster_size
        self._min_samples = min_samples
        self._epsilon = cluster_selection_epsilon
        self._metric = metric

    def cluster(
        self,
        keyword_contexts: list[KeywordContext],
        similarity_threshold: float = 0.85,
    ) -> list[list[KeywordContext]]:
        if not keyword_contexts:
            return []

        items = [kc for kc in keyword_contexts if kc.embedding is not None]
        if not items:
            logger.warning("No keyword contexts with embeddings to cluster")
            return []

        try:
            import hdbscan
        except ImportError:
            logger.error(
                "hdbscan not installed. Install with: pip install hdbscan"
            )
            logger.warning("Falling back to greedy clustering")
            return GreedyConceptClusterer().cluster(
                keyword_contexts, similarity_threshold,
            )

        # Build embedding matrix
        vectors = np.array([kc.embedding for kc in items], dtype=np.float32)

        # Normalize for cosine distance
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        vectors_norm = vectors / norms

        # Convert similarity threshold to distance:
        # cosine_distance = 1 - cosine_similarity
        epsilon = 1.0 - similarity_threshold

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self._min_cluster_size,
            min_samples=self._min_samples,
            cluster_selection_epsilon=max(epsilon, self._epsilon),
            metric=self._metric,
            cluster_selection_method="eom",
        )

        labels = clusterer.fit_predict(vectors_norm)

        # Group by label (-1 = noise → each becomes its own cluster)
        cluster_map: dict[int, list[KeywordContext]] = {}
        noise_items: list[KeywordContext] = []

        for kc, label in zip(items, labels):
            if label == -1:
                noise_items.append(kc)
            else:
                cluster_map.setdefault(label, []).append(kc)

        clusters = list(cluster_map.values())
        # Noise items become singleton clusters
        for kc in noise_items:
            clusters.append([kc])

        n_real = len(cluster_map)
        n_noise = len(noise_items)
        logger.info(
            "HDBSCAN clustered %d keywords into %d groups "
            "(%d dense + %d noise/singleton, epsilon=%.3f)",
            len(items), len(clusters), n_real, n_noise, epsilon,
        )
        _log_clusters(clusters)
        return clusters


# ── Aliases ──────────────────────────────────────────────────

# Keep backward compatibility
ConceptClusterer = GreedyConceptClusterer


# ── Helpers ──────────────────────────────────────────────────

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _log_clusters(clusters: list[list[KeywordContext]]) -> None:
    """Log cluster details at DEBUG level."""
    for i, cluster in enumerate(clusters):
        words = {kc.word for kc in cluster}
        articles = {kc.article_id for kc in cluster}
        logger.debug(
            "  Cluster %d: words=%s, articles=%s",
            i, words, articles,
        )
