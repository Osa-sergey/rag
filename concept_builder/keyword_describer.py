"""Keyword describer — dual-context LLM descriptions for keywords."""
from __future__ import annotations

import logging
from typing import Any

from omegaconf import DictConfig

from interfaces import BaseKeywordDescriber
from raptor_pipeline.summarizer.llm_summarizer import _build_llm

logger = logging.getLogger(__name__)


class KeywordDescriber(BaseKeywordDescriber):
    """Generate keyword descriptions using dual-context strategy.

    For each keyword:
      1. Find max-level chunk (broad context from RAPTOR summary).
      2. Find leaf chunk (level=0) with highest confidence (details).
      3. Compose prompt with both contexts, limited to max_prompt_tokens.
      4. LLM generates a 1-2 sentence description.
    """

    def __init__(
        self,
        llm_cfg: DictConfig,
        prompt_cfg: DictConfig,
        *,
        vector_store: Any = None,
        embedder: Any = None,
        tracker: Any = None,
        max_prompt_tokens: int = 3000,
        chars_per_token: float = 2.5,
    ) -> None:
        self._llm = _build_llm(llm_cfg)
        self._template: str = prompt_cfg.get("template", "Опиши {keyword}")
        self._vector_store = vector_store
        self._embedder = embedder
        self._tracker = tracker
        self._max_prompt_tokens = max_prompt_tokens
        self._chars_per_token = chars_per_token

    def describe(
        self,
        keyword_word: str,
        article_id: str,
        chunk_ids: list[str],
    ) -> str:
        """Generate description using broad + detail contexts."""
        if not chunk_ids:
            logger.debug("No chunks for keyword '%s' in article '%s'", keyword_word, article_id)
            return ""

        # Retrieve chunk texts and levels from Qdrant
        broad_text, detail_text = self._get_dual_context(chunk_ids, article_id)

        # Truncate to fit token budget
        max_chars = int(self._max_prompt_tokens * self._chars_per_token)
        # Reserve ~40% for broad, ~40% for detail, ~20% for template
        ctx_budget = int(max_chars * 0.4)
        broad_text = broad_text[:ctx_budget] if broad_text else "(контекст недоступен)"
        detail_text = detail_text[:ctx_budget] if detail_text else "(контекст недоступен)"

        prompt = (
            self._template
            .replace("{keyword}", keyword_word)
            .replace("{broad_context}", broad_text)
            .replace("{detail_context}", detail_text)
        )

        try:
            response = self._llm.invoke(prompt)
            if self._tracker:
                self._tracker.track(response, "keyword_describer")
            content = response.content if hasattr(response, "content") else str(response)
            return content.strip()
        except Exception as exc:
            logger.warning("Failed to describe keyword '%s': %s", keyword_word, exc)
            return ""

    def _get_dual_context(
        self, chunk_ids: list[str], article_id: str,
    ) -> tuple[str, str]:
        """Get broad (max-level) and detail (leaf, max-confidence) contexts.

        Returns:
            (broad_text, detail_text)
        """
        if not self._vector_store:
            return "", ""

        # Search for points matching the given chunk_ids
        chunks_data: list[dict] = []
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
            # Get all points for this article
            all_points = self._vector_store._client.scroll(
                collection_name=self._vector_store._collection,
                scroll_filter=Filter(must=[
                    FieldCondition(key="article_id", match=MatchValue(value=article_id)),
                ]),
                limit=500,
                with_payload=True,
            )[0]  # scroll returns (points, next_offset)

            for point in all_points:
                payload = point.payload or {}
                if payload.get("node_id") in chunk_ids:
                    chunks_data.append({
                        "node_id": payload.get("node_id"),
                        "level": payload.get("level", 0),
                        "text": payload.get("text", ""),
                    })
        except Exception as exc:
            logger.warning("Failed to retrieve chunks: %s", exc)
            return "", ""

        if not chunks_data:
            return "", ""

        # Broad: max level
        max_level_chunk = max(chunks_data, key=lambda c: c["level"])
        broad_text = max_level_chunk["text"]

        # Detail: level=0 chunks, pick longest (closest to highest confidence)
        leaf_chunks = [c for c in chunks_data if c["level"] == 0]
        if leaf_chunks:
            detail_chunk = max(leaf_chunks, key=lambda c: len(c["text"]))
            detail_text = detail_chunk["text"]
        else:
            # Fallback to min-level chunk
            min_level_chunk = min(chunks_data, key=lambda c: c["level"])
            detail_text = min_level_chunk["text"]

        return broad_text, detail_text
