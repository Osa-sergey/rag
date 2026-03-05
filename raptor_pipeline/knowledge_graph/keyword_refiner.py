"""LLM-based global keyword refiner."""
from __future__ import annotations

import json
import logging

from omegaconf import DictConfig

from raptor_pipeline.summarizer.llm_summarizer import _build_llm

logger = logging.getLogger(__name__)


class LLMKeywordRefiner:
    """Refine a list of keywords to merge synonyms and fix categories."""

    def __init__(self, cfg: DictConfig, prompt_cfg: DictConfig) -> None:
        self._llm = _build_llm(cfg)
        self._template: str = prompt_cfg.get(
            "template",
            "Верни JSON: [{\"refined_word\": \"...\", \"category\": \"...\", \"original_words\": [\"...\"]}]\nСырые слова: {raw_keywords}"
        )
        logger.info("LLMKeywordRefiner ready")

    def refine(self, raw_keywords: list[dict[str, str]]) -> list[dict]:
        """Takes a list of dicts with 'word' and 'category'. 
        Returns parsed JSON from LLM:
        [
            {"refined_word": "...", "category": "...", "original_words": ["...", "..."]}
        ]
        """
        # Deduplicate the input list to reduce prompt size
        unique_raw = {}
        for kw in raw_keywords:
            word = kw["word"]
            if word not in unique_raw:
                unique_raw[word] = kw["category"]

        raw_text_list = "\n".join([f"- {w} ({c})" for w, c in unique_raw.items()])
        
        prompt = self._template.replace("{raw_keywords}", raw_text_list)
        
        try:
            response = self._llm.invoke(prompt)
            raw_output = response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            logger.error("LLM Refiner failed to generate response: %s", exc)
            return []

        try:
            cleaned = raw_output.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            items = json.loads(cleaned)
            return items
        except Exception as exc:
            logger.warning("Failed to parse refiner JSON: %s | raw: %s", exc, raw_output[:200])
            return []
