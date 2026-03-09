from omegaconf import DictConfig
import logging

from raptor_pipeline.knowledge_graph.base import RefinedKeywordListSO
from raptor_pipeline.summarizer.llm_summarizer import _build_llm

logger = logging.getLogger(__name__)


class LLMKeywordRefiner:
    """Refine a list of keywords to merge synonyms and fix categories using Structured Output."""

    def __init__(self, cfg: DictConfig, prompt_cfg: DictConfig) -> None:
        llm = _build_llm(cfg)
        self._structured_llm = llm.with_structured_output(RefinedKeywordListSO)
        
        self._template: str = prompt_cfg.get(
            "template",
            "У тебя есть сырой список ключевых слов. Объедини синонимы и исправь категории.\nСырые слова: {raw_keywords}"
        )
        logger.info("LLMKeywordRefiner ready (SO enabled)")

    def refine(self, raw_keywords: list[dict[str, str]]) -> list[dict]:
        """Takes a list of dicts with 'word' and 'category'. 
        Returns parsed list of refined items:
        [
            {"refined_word": "...", "category": "...", "original_words": ["...", "..."]}
        ]
        """
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
            result: RefinedKeywordListSO = self._structured_llm.invoke(prompt)
            if not result or not result.items:
                return []
            
            # Convert back to list of dicts for compatibility
            return [
                {
                    "refined_word": item.refined_word,
                    "category": item.category,
                    "original_words": item.original_words
                }
                for item in result.items
            ]
        except Exception as exc:
            logger.error("SO Keyword Refiner failed: %s", exc)
            return []
