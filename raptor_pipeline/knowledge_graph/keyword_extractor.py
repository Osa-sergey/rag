"""LLM-based keyword extraction."""
from __future__ import annotations

import json
import logging

from omegaconf import DictConfig

from raptor_pipeline.knowledge_graph.base import BaseKeywordExtractor, Keyword, KeywordListSO
from raptor_pipeline.summarizer.llm_summarizer import _build_llm

logger = logging.getLogger(__name__)


class LLMKeywordExtractor(BaseKeywordExtractor):
    """Extract keywords from text using an LLM with Structured Output.
    """

    def __init__(self, cfg: DictConfig, prompt_cfg: DictConfig) -> None:
        llm = _build_llm(cfg)
        # Use LangChain Structured Output
        self._structured_llm = llm.with_structured_output(KeywordListSO)
        
        self._max_keywords: int = cfg.get("max_keywords", 15)
        self._confidence_threshold: float = cfg.get("confidence_threshold", 0.5)
        self._template: str = prompt_cfg.get(
            "template",
            "Извлеки ключевые слова из текста:\n{text}"
        )
        self._prompt_version: str = prompt_cfg.get("version", "1.0")
        logger.info(
            "LLMKeywordExtractor ready (SO enabled, v%s)",
            self._prompt_version
        )

    def extract(self, text: str, chunk_id: str = "") -> list[Keyword]:
        prompt = (
            self._template
            .replace("{text}", text)
            .replace("{max_keywords}", str(self._max_keywords))
        )
        
        try:
            result: KeywordListSO = self._structured_llm.invoke(prompt)
            if not result or not result.keywords:
                return []

            keywords: list[Keyword] = []
            for item in result.keywords:
                kw = Keyword(
                    word=item.word.strip(),
                    category=item.category,
                    confidence=item.confidence,
                    chunk_id=chunk_id,
                )
                if kw.word and kw.confidence >= self._confidence_threshold:
                    keywords.append(kw)
            return keywords[: self._max_keywords]
        except Exception as exc:
            logger.warning("SO Keyword extraction failed: %s", exc)
            return []
