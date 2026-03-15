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

    def __init__(self, cfg: DictConfig, prompt_cfg: DictConfig, *, tracker=None) -> None:
        self._llm = _build_llm(cfg)
        self._tracker = tracker
        # Use LangChain Structured Output (include_raw=True for token tracking)
        self._structured_llm = self._llm.with_structured_output(KeywordListSO, include_raw=True)
        
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

    def _clean_json_text(self, text: str) -> str:
        """Strip markdown code blocks and reasoning tags."""
        import re
        text = text.strip()
        # Remove reasoning/thinking tags (e.g. <thought>...</thought> or <think>...</think>)
        text = re.sub(r'<(thought|think)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove markdown code blocks
        if "```" in text:
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(1)
            else:
                text = text.replace("```json", "").replace("```", "")
        return text.strip()

    def extract(self, text: str, chunk_id: str = "") -> list[Keyword]:
        prompt = (
            self._template
            .replace("{text}", text)
            .replace("{max_keywords}", str(self._max_keywords))
        )
        
        try:
            # 1. Try primary structured output
            so_result = self._structured_llm.invoke(prompt)
            # include_raw=True returns {'raw': AIMessage, 'parsed': Pydantic, 'parsing_error': ...}
            raw_msg = so_result.get("raw") if isinstance(so_result, dict) else None
            result: KeywordListSO | None = (
                so_result.get("parsed") if isinstance(so_result, dict) else so_result
            )
            if self._tracker and raw_msg is not None:
                self._tracker.track(raw_msg, "keyword_extractor")
            if result and result.keywords:
                return self._parse_so_result(result, chunk_id)
            
            # 2. Fallback: Manual parse if SO returned empty or failed
            return self._manual_fallback(prompt, chunk_id)
        except Exception as exc:
            logger.debug("SO Keyword extraction failed: %s. Trying manual fallback...", exc)
            return self._manual_fallback(prompt, chunk_id)

    def _manual_fallback(self, prompt: str, chunk_id: str) -> list[Keyword]:
        try:
            raw_response = self._llm.invoke(prompt)
            if self._tracker:
                self._tracker.track(raw_response, "keyword_extractor")
            content = raw_response.content if hasattr(raw_response, "content") else str(raw_response)
            clean_content = self._clean_json_text(content)
            
            parsed = json.loads(clean_content)
            if isinstance(parsed, list):
                result = KeywordListSO(keywords=parsed)
            elif isinstance(parsed, dict):
                if "keywords" in parsed:
                    result = KeywordListSO(keywords=parsed["keywords"])
                else:
                    # If it's a dict but doesn't have 'keywords' key, it might be a single item or something else
                    logger.warning("JSON dict missing 'keywords' key: %s", parsed.keys())
                    return []
            else:
                return []
            return self._parse_so_result(result, chunk_id)
        except Exception as exc:
            logger.warning("Manual fallback keyword extraction failed: %s", exc)
            return []

    def _parse_so_result(self, result: KeywordListSO, chunk_id: str) -> list[Keyword]:
        keywords: list[Keyword] = []
        for item in result.keywords:
            if isinstance(item, dict):
                word = item.get('word', '')
                category = item.get('category', 'other')
                confidence = item.get('confidence', 1.0)
            else:
                word = getattr(item, 'word', '')
                category = getattr(item, 'category', 'other')
                confidence = getattr(item, 'confidence', 1.0)
            
            kw = Keyword(
                word=str(word).strip(),
                category=str(category),
                confidence=float(confidence),
                chunk_id=chunk_id,
            )
            if kw.word and kw.confidence >= self._confidence_threshold:
                keywords.append(kw)
        return keywords[: self._max_keywords]
