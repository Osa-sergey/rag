import json
import logging
from omegaconf import DictConfig
import logging

from raptor_pipeline.knowledge_graph.base import RefinedKeywordListSO
from raptor_pipeline.summarizer.llm_summarizer import _build_llm

logger = logging.getLogger(__name__)


class LLMKeywordRefiner:
    """Refine a list of keywords to merge synonyms and fix categories using Structured Output."""

    def __init__(self, cfg: DictConfig, prompt_cfg: DictConfig) -> None:
        self._llm = _build_llm(cfg)
        self._structured_llm = self._llm.with_structured_output(RefinedKeywordListSO)
        
        self._template: str = prompt_cfg.get(
            "template",
            "У тебя есть сырой список ключевых слов. Объедини синонимы и исправь категории.\nСырые слова: {raw_keywords}"
        )
        logger.info("LLMKeywordRefiner ready (SO enabled)")

    def _clean_json_text(self, text: str) -> str:
        """Strip markdown code blocks and reasoning tags."""
        import re
        text = text.strip()
        # Remove reasoning/thinking tags
        text = re.sub(r'<(thought|think)>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove markdown code blocks
        if "```" in text:
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(1)
            else:
                text = text.replace("```json", "").replace("```", "")
        return text.strip()

    def refine(self, raw_keywords: list[dict[str, str]]) -> list[dict]:
        if not raw_keywords:
            return []

        # Deduplicate the input list to reduce prompt size
        unique_raw = {}
        for kw in raw_keywords:
            word = kw["word"]
            if word not in unique_raw:
                unique_raw[word] = kw.get("category", "other")

        raw_text_list = "\n".join([f"- {w} ({c})" for w, c in unique_raw.items()])
        prompt = self._template.replace("{raw_keywords}", raw_text_list)
        
        try:
            # 1. Try primary structured output
            result: RefinedKeywordListSO = self._structured_llm.invoke(prompt)
            if result and result.items:
                return self._parse_so_result(result)
            
            # 2. Fallback: Manual parse
            return self._manual_fallback(prompt)
        except Exception as exc:
            logger.debug("SO Keyword Refiner failed: %s. Trying manual fallback...", exc)
            return self._manual_fallback(prompt)

    def _manual_fallback(self, prompt: str) -> list[dict]:
        try:
            raw_response = self._llm.invoke(prompt)
            content = raw_response.content if hasattr(raw_response, "content") else str(raw_response)
            clean_content = self._clean_json_text(content)
            
            parsed = json.loads(clean_content)
            if isinstance(parsed, list):
                result = RefinedKeywordListSO(items=parsed)
            elif isinstance(parsed, dict):
                if "items" in parsed:
                    result = RefinedKeywordListSO(items=parsed["items"])
                else:
                    return []
            else:
                return []
            return self._parse_so_result(result)
        except Exception as exc:
            logger.warning("Manual fallback keyword refiner failed: %s", exc)
            return []

    def _parse_so_result(self, result: RefinedKeywordListSO) -> list[dict]:
        return [
            {
                "refined_word": getattr(item, 'refined_word', item.get('refined_word', '')),
                "category": getattr(item, 'category', item.get('category', 'other')),
                "original_words": getattr(item, 'original_words', item.get('original_words', []))
            }
            for item in result.items
        ]
