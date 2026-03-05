"""LLM-based keyword extraction."""
from __future__ import annotations

import json
import logging

from omegaconf import DictConfig

from raptor_pipeline.knowledge_graph.base import BaseKeywordExtractor, Keyword
from raptor_pipeline.summarizer.llm_summarizer import _build_llm

logger = logging.getLogger(__name__)


class LLMKeywordExtractor(BaseKeywordExtractor):
    """Extract keywords from text using an LLM.

    The prompt is loaded from ``prompts.keywords`` Hydra config section.
    """

    def __init__(self, cfg: DictConfig, prompt_cfg: DictConfig) -> None:
        self._llm = _build_llm(cfg)
        self._max_keywords: int = cfg.get("max_keywords", 15)
        self._confidence_threshold: float = cfg.get("confidence_threshold", 0.5)
        self._template: str = prompt_cfg.get(
            "template",
            (
                "Извлеки из текста до {max_keywords} ключевых слов или фраз.\n"
                "Для каждого укажи категорию (technology, concept, method, "
                "tool, person, organisation, other) и уверенность (0–1).\n"
                "Верни JSON-массив объектов "
                '[{{"word": "...", "category": "...", "confidence": 0.X}}].\n\n'
                "Текст:\n{text}\n\n"
                "JSON:"
            ),
        )
        self._prompt_version: str = prompt_cfg.get("version", "1.0")
        logger.info(
            "LLMKeywordExtractor ready (prompt v%s, max_keywords=%d)",
            self._prompt_version,
            self._max_keywords,
        )

    def extract(self, text: str, chunk_id: str = "") -> list[Keyword]:
        prompt = (
            self._template
            .replace("{text}", text)
            .replace("{max_keywords}", str(self._max_keywords))
        )
        response = self._llm.invoke(prompt)
        raw = response.content if hasattr(response, "content") else str(response)

        keywords: list[Keyword] = []
        try:
            # Try to parse JSON from response (may contain markdown fences)
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            items = json.loads(cleaned)
            for item in items:
                kw = Keyword(
                    word=item.get("word", "").strip(),
                    category=item.get("category", "other"),
                    confidence=float(item.get("confidence", 1.0)),
                    chunk_id=chunk_id,
                )
                if kw.word and kw.confidence >= self._confidence_threshold:
                    keywords.append(kw)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("Failed to parse keyword JSON: %s | raw: %s", exc, raw[:200])

        return keywords[: self._max_keywords]
