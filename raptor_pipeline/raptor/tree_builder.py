"""RAPTOR tree builder — recursive clustering + summarisation."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

import numpy as np
from omegaconf import DictConfig
from sklearn.mixture import GaussianMixture

from raptor_pipeline.chunker.base import Chunk
from raptor_pipeline.embeddings.base import BaseEmbeddingProvider
from raptor_pipeline.summarizer.base import BaseSummarizer

logger = logging.getLogger(__name__)


@dataclass
class RaptorNode:
    """Node in the RAPTOR tree.

    Leaf nodes correspond to original chunks; higher-level nodes are summaries
    of clusters from the level below.

    Attributes:
        node_id:      Unique identifier.
        text:         Text content (original or summary).
        embedding:    Embedding vector.
        level:        Tree level (0 = leaf).
        children_ids: IDs of child nodes.
        article_id:   Source article ID.
        metadata:     Extra metadata.
    """

    node_id: str
    text: str
    embedding: list[float] = field(default_factory=list)
    level: int = 0
    children_ids: list[str] = field(default_factory=list)
    article_id: str = ""
    metadata: dict = field(default_factory=dict)


class RaptorTreeBuilder:
    """Builds a RAPTOR tree: leaves → clusters → summaries → repeat.

    Config parameters (from Hydra ``raptor`` section):
        max_levels:        Maximum depth of the tree.
        min_cluster_size:  Stop recursion when fewer nodes remain.
        reduction_factor:  Target ratio of nodes to clusters (e.g. 0.5).
        clustering_threshold: BIC threshold for GMM component selection.
    """

    def __init__(
        self,
        cfg: DictConfig,
        embedding_provider: BaseEmbeddingProvider,
        summarizer: BaseSummarizer,
    ) -> None:
        self.max_levels: int = cfg.get("max_levels", 3)
        self.min_cluster_size: int = cfg.get("min_cluster_size", 3)
        self.reduction_factor: float = cfg.get("reduction_factor", 0.5)
        self.clustering_threshold: float = cfg.get("clustering_threshold", 0.1)
        self.max_concurrency: int = cfg.get("max_concurrency", 4)
        self._embedder = embedding_provider
        self._summarizer = summarizer

    # ------------------------------------------------------------------
    def build(self, chunks: list[Chunk]) -> list[RaptorNode]:
        """Build the full RAPTOR tree from leaf chunks.

        Returns:
            Flat list of all nodes across all levels.
        """
        # Create leaf nodes
        all_nodes: list[RaptorNode] = []
        current_level_nodes: list[RaptorNode] = []

        leaf_texts = [c.text for c in chunks]
        leaf_embeddings = self._embedder.embed_texts(leaf_texts)

        for chunk, emb in zip(chunks, leaf_embeddings):
            node = RaptorNode(
                node_id=chunk.chunk_id,
                text=chunk.text,
                embedding=emb,
                level=0,
                article_id=chunk.article_id,
                metadata=chunk.metadata,
            )
            current_level_nodes.append(node)
            all_nodes.append(node)

        logger.info("RAPTOR: %d leaf nodes created", len(current_level_nodes))

        # Build upper levels
        for level in range(1, self.max_levels + 1):
            if len(current_level_nodes) <= self.min_cluster_size:
                logger.info(
                    "RAPTOR: stopping at level %d (%d nodes <= min_cluster_size=%d)",
                    level,
                    len(current_level_nodes),
                    self.min_cluster_size,
                )
                break

            clusters = self._cluster(current_level_nodes)
            if not clusters:
                break

            from concurrent.futures import ThreadPoolExecutor

            max_workers = self.max_concurrency
            next_level_nodes: list[RaptorNode] = []

            def process_cluster(cluster_nodes: list[RaptorNode]) -> RaptorNode:
                texts = [n.text for n in cluster_nodes]
                summary = self._summarizer.summarize(texts)
                emb = self._embedder.embed_texts([summary])[0]
                return RaptorNode(
                    node_id=str(uuid.uuid4()),
                    text=summary,
                    embedding=emb,
                    level=level,
                    children_ids=[n.node_id for n in cluster_nodes],
                    article_id=cluster_nodes[0].article_id,
                    metadata={"cluster_size": len(cluster_nodes)},
                )

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(process_cluster, clusters))

            next_level_nodes = results
            all_nodes.extend(next_level_nodes)

            logger.info(
                "RAPTOR level %d: %d clusters -> %d nodes",
                level,
                len(clusters),
                len(next_level_nodes),
            )
            current_level_nodes = next_level_nodes

        return all_nodes

    # ------------------------------------------------------------------
    def _cluster(
        self, nodes: list[RaptorNode]
    ) -> list[list[RaptorNode]] | None:
        """Cluster nodes using Gaussian Mixture Model."""
        embeddings = np.array([n.embedding for n in nodes])
        n = len(nodes)

        # Determine optimal number of clusters
        target_k = max(2, int(n * self.reduction_factor))
        max_k = min(target_k + 2, n - 1)
        min_k = max(2, target_k - 2)

        best_k = target_k
        best_bic = float("inf")
        for k in range(min_k, max_k + 1):
            try:
                gmm = GaussianMixture(
                    n_components=k,
                    covariance_type="full",
                    random_state=42,
                )
                gmm.fit(embeddings)
                bic = gmm.bic(embeddings)
                if bic < best_bic:
                    best_bic = bic
                    best_k = k
            except Exception:
                continue

        # Fit final model
        gmm = GaussianMixture(
            n_components=best_k,
            covariance_type="full",
            random_state=42,
        )
        labels = gmm.fit_predict(embeddings)

        clusters: dict[int, list[RaptorNode]] = {}
        for node, label in zip(nodes, labels):
            clusters.setdefault(int(label), []).append(node)

        # Filter out very small clusters
        valid = [
            c
            for c in clusters.values()
            if len(c) >= 2
        ]
        return valid if valid else None
