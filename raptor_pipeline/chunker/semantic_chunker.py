"""Semantic chunker — groups adjacent blocks by embedding similarity."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from omegaconf import DictConfig

from document_parser.text_extractor import flatten_blocks, render_block
from raptor_pipeline.chunker.base import BaseChunker, Chunk

if TYPE_CHECKING:
    from interfaces import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class SemanticChunker(BaseChunker):
    """Chunks document by semantic similarity between adjacent blocks.

    Algorithm:
      1. Render every block to text.
      2. Compute embeddings for each block.
      3. Calculate cosine similarity between consecutive blocks.
      4. Cut where similarity drops below *similarity_threshold*.
      5. Merge resulting groups shorter than *min_chunk_chars*.
    """

    def __init__(
        self,
        cfg: DictConfig,
        embedding_provider: BaseEmbeddingProvider,
    ) -> None:
        self.similarity_threshold: float = cfg.get("similarity_threshold", 0.5)
        self.min_chunk_chars: int = cfg.get("min_chunk_chars", 200)
        self.max_chunk_chars: int = cfg.get("max_chunk_chars", 2000)
        self._embedder = embedding_provider

    # ------------------------------------------------------------------
    def chunk(self, document: list[dict], article_id: str) -> list[Chunk]:
        flat = flatten_blocks(document)

        # Render text for every block, filter empty
        rendered: list[tuple[dict, str]] = []
        for b in flat:
            text = render_block(b)
            if text.strip():
                rendered.append((b, text.strip()))

        if not rendered:
            return []

        texts = [t for _, t in rendered]
        embeddings = self._embedder.embed_texts(texts)

        groups = self._group_by_similarity(rendered, embeddings)
        groups = self._merge_short(groups)
        return self._to_chunks(groups, article_id)

    # ------------------------------------------------------------------
    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        a_arr = np.array(a)
        b_arr = np.array(b)
        denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
        if denom == 0:
            return 0.0
        return float(np.dot(a_arr, b_arr) / denom)

    def _group_by_similarity(
        self,
        rendered: list[tuple[dict, str]],
        embeddings: list[list[float]],
    ) -> list[list[tuple[dict, str]]]:
        groups: list[list[tuple[dict, str]]] = [[rendered[0]]]
        for i in range(1, len(rendered)):
            sim = self._cosine_sim(embeddings[i - 1], embeddings[i])
            if sim >= self.similarity_threshold:
                groups[-1].append(rendered[i])
            else:
                groups.append([rendered[i]])
        return groups

    def _merge_short(
        self, groups: list[list[tuple[dict, str]]]
    ) -> list[list[tuple[dict, str]]]:
        merged: list[list[tuple[dict, str]]] = []
        buf: list[tuple[dict, str]] = []

        for grp in groups:
            buf.extend(grp)
            total = sum(len(t) for _, t in buf)
            if total >= self.min_chunk_chars:
                merged.append(buf)
                buf = []

        if buf:
            if merged:
                merged[-1].extend(buf)
            else:
                merged.append(buf)
        return merged

    def _to_chunks(
        self,
        groups: list[list[tuple[dict, str]]],
        article_id: str,
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        for i, grp in enumerate(groups, 1):
            text = "\n\n".join(t for _, t in grp)
            block_ids = [str(b.get("id", "")) for b, _ in grp if "id" in b]
            chunks.append(
                Chunk(
                    chunk_id=f"{article_id}_semchunk_{i}",
                    article_id=article_id,
                    text=text,
                    block_ids=block_ids,
                    level=0,
                    metadata={
                        "section_index": i,
                        "char_count": len(text),
                    },
                )
            )
        return chunks
