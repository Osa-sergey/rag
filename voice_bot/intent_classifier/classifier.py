"""Embedding-based intent classifier.

Uses BERTA (or any sentence-transformer) to compute cosine similarity
between input text and pre-computed reference embeddings for each intent.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

logger = logging.getLogger(__name__)


# ── Contracts ─────────────────────────────────────────────────


class EmbeddingProvider(Protocol):
    """Minimal embedding interface (compatible with raptor's BaseEmbeddingProvider)."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


@dataclass
class IntentDef:
    """Definition of a single intent with reference phrases."""

    name: str
    reference_phrases: list[str]
    embedding: np.ndarray | None = field(default=None, repr=False)


@dataclass
class ClassificationResult:
    """Result of intent classification."""

    intent: str
    confidence: float
    scores: dict[str, float] = field(default_factory=dict)


# ── Classifier ────────────────────────────────────────────────


class IntentClassifier:
    """Classify text intent via cosine similarity to reference embeddings.

    Usage::

        intents = [
            IntentDef("expense", ["потратил", "купил", "заплатил за обед"]),
            IntentDef("transfer", ["перевёл деньги", "скинул 500 рублей"]),
        ]
        clf = IntentClassifier(embedding_provider, intents)
        result = clf.classify("сегодня потратил 300 на кофе")
        # result.intent == "expense", result.confidence ≈ 0.85
    """

    def __init__(
        self,
        embedder: EmbeddingProvider,
        intents: list[IntentDef],
        *,
        unknown_threshold: float = 0.35,
    ) -> None:
        self._embedder = embedder
        self._intents = intents
        self._unknown_threshold = unknown_threshold

        # Pre-compute mean embeddings per intent
        self._build_reference_embeddings()

    # ── Public API ────────────────────────────────────────────

    def classify(self, text: str) -> ClassificationResult:
        """Classify a single text and return the best-matching intent."""
        query_emb = np.array(self._embedder.embed_query(text))

        scores: dict[str, float] = {}
        for intent in self._intents:
            sim = self._cosine_similarity(query_emb, intent.embedding)
            scores[intent.name] = float(sim)

        best_name = max(scores, key=scores.get)  # type: ignore[arg-type]
        best_score = scores[best_name]

        if best_score < self._unknown_threshold:
            return ClassificationResult(
                intent="unknown", confidence=1.0 - best_score, scores=scores,
            )

        return ClassificationResult(
            intent=best_name, confidence=best_score, scores=scores,
        )

    # ── Internal ──────────────────────────────────────────────

    def _build_reference_embeddings(self) -> None:
        """Compute mean embedding for each intent from reference phrases."""
        for intent in self._intents:
            if not intent.reference_phrases:
                raise ValueError(f"Intent '{intent.name}' has no reference phrases")

            vecs = self._embedder.embed_texts(intent.reference_phrases)
            intent.embedding = np.mean(vecs, axis=0)
            # Normalize
            norm = np.linalg.norm(intent.embedding)
            if norm > 0:
                intent.embedding = intent.embedding / norm

            logger.info(
                "Intent '%s': %d reference phrases → embedding dim %d",
                intent.name,
                len(intent.reference_phrases),
                len(intent.embedding),
            )

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))
