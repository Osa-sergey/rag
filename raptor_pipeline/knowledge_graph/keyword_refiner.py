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

        unique_items = list(unique_raw.items())
        max_batch = 50
        total_batches = (len(unique_items) + max_batch - 1) // max_batch

        # ── Pass 1: Refine each batch independently ──────────
        pass1_results: list[dict] = []
        for i in range(0, len(unique_items), max_batch):
            batch = unique_items[i : i + max_batch]
            logger.info(
                "  Refiner pass 1 — batch %d/%d (%d keywords)...",
                i // max_batch + 1, total_batches, len(batch),
            )
            batch_result = self._refine_batch(batch)
            pass1_results.extend(batch_result)

        if not pass1_results:
            return []

        # ── Pass 2: Cross-batch dedup ────────────────────────
        # Collect all refined words from pass 1 and run a final
        # merge so that synonyms from different batches get unified.
        refined_words = {}
        for item in pass1_results:
            w = item.get("refined_word", "").strip()
            if w:
                key = w.lower()
                if key not in refined_words:
                    refined_words[key] = item.get("category", "other")

        # Only run pass 2 if there are enough words to potentially merge
        if len(refined_words) <= max_batch:
            # Small enough — do one final dedup pass
            logger.info(
                "  Refiner pass 2 — cross-batch dedup (%d refined words)...",
                len(refined_words),
            )
            pass2_items = list(refined_words.items())
            pass2_results = self._refine_batch(pass2_items)

            if pass2_results:
                return self._merge_passes(pass1_results, pass2_results)
        else:
            # Too many — run pass 2 in batches too, but with larger batch
            pass2_items = list(refined_words.items())
            large_batch = 100
            pass2_results: list[dict] = []
            total_p2 = (len(pass2_items) + large_batch - 1) // large_batch
            for i in range(0, len(pass2_items), large_batch):
                batch = pass2_items[i : i + large_batch]
                logger.info(
                    "  Refiner pass 2 — batch %d/%d (%d refined words)...",
                    i // large_batch + 1, total_p2, len(batch),
                )
                batch_result = self._refine_batch(batch)
                pass2_results.extend(batch_result)

            if pass2_results:
                return self._merge_passes(pass1_results, pass2_results)

        return pass1_results

    def _merge_passes(
        self, pass1: list[dict], pass2: list[dict]
    ) -> list[dict]:
        """Merge pass-2 results back: rewrite original_words to point
        through to the raw keywords from pass 1."""
        # Build pass-1 mapping: refined_word -> list of original_words
        p1_originals: dict[str, list[str]] = {}
        for item in pass1:
            rw = item.get("refined_word", "").strip().lower()
            for orig in item.get("original_words", []):
                p1_originals.setdefault(rw, []).append(orig)

        merged: list[dict] = []
        for item in pass2:
            rw2 = item.get("refined_word", "").strip()
            cat2 = item.get("category", "other")
            # Collect ALL raw original_words from pass-1 items that
            # pass-2 merged together
            all_originals: list[str] = []
            for p2_orig in item.get("original_words", []):
                key = p2_orig.strip().lower()
                if key in p1_originals:
                    all_originals.extend(p1_originals[key])
                else:
                    all_originals.append(p2_orig)

            merged.append({
                "refined_word": rw2,
                "category": cat2,
                "original_words": list(dict.fromkeys(all_originals)),  # dedup, keep order
            })

        logger.info(
            "  Refiner: pass1 produced %d items, pass2 merged to %d",
            len(pass1), len(merged),
        )
        return merged

    def _refine_batch(self, batch: list[tuple[str, str]]) -> list[dict]:
        """Refine a single batch of (word, category) tuples."""
        raw_text_list = "\n".join([f"- {w} ({c})" for w, c in batch])
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
