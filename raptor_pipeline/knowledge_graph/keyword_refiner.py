import json
import logging
import re
from omegaconf import DictConfig

from raptor_pipeline.knowledge_graph.base import BaseKeywordRefiner
from raptor_pipeline.summarizer.llm_summarizer import _build_llm

logger = logging.getLogger(__name__)


class LLMKeywordRefiner(BaseKeywordRefiner):
    """Refine keywords: merge synonyms, fix categories.

    Uses a single raw LLM call (no structured output) with robust
    multi-strategy JSON parsing for maximum compatibility with
    different models (gemma3, qwen3, etc.).
    """

    def __init__(self, cfg: DictConfig, prompt_cfg: DictConfig) -> None:
        self._llm = _build_llm(cfg)
        self._template: str = prompt_cfg.get(
            "template",
            "У тебя есть сырой список ключевых слов. Объедини синонимы и исправь категории.\nСырые слова: {raw_keywords}",
        )
        logger.info("LLMKeywordRefiner ready")

    # ── Public API ────────────────────────────────────────────

    def refine(self, raw_keywords: list[dict[str, str]]) -> list[dict]:
        if not raw_keywords:
            return []

        # Deduplicate
        unique_raw: dict[str, str] = {}
        for kw in raw_keywords:
            word = kw["word"]
            if word not in unique_raw:
                unique_raw[word] = kw.get("category", "other")

        unique_items = list(unique_raw.items())
        max_batch = 50
        total_batches = (len(unique_items) + max_batch - 1) // max_batch

        # ── Pass 1: Refine each batch ────────────────────────
        pass1_results: list[dict] = []
        for i in range(0, len(unique_items), max_batch):
            batch = unique_items[i : i + max_batch]
            batch_num = i // max_batch + 1
            logger.info(
                "  Refiner pass 1 — batch %d/%d (%d keywords)...",
                batch_num, total_batches, len(batch),
            )
            batch_result = self._refine_batch(batch)
            logger.info("    -> got %d refined items", len(batch_result))
            pass1_results.extend(batch_result)

        if not pass1_results:
            return []

        # ── Pass 2: Cross-batch dedup ────────────────────────
        refined_words: dict[str, str] = {}
        for item in pass1_results:
            w = item.get("refined_word", "").strip()
            if w:
                key = w.lower()
                if key not in refined_words:
                    refined_words[key] = item.get("category", "other")

        if len(refined_words) <= max_batch:
            logger.info(
                "  Refiner pass 2 — cross-batch dedup (%d refined words)...",
                len(refined_words),
            )
            pass2_results = self._refine_batch(list(refined_words.items()))
            if pass2_results:
                return self._merge_passes(pass1_results, pass2_results)
        else:
            pass2_items = list(refined_words.items())
            large_batch = 100
            pass2_results_all: list[dict] = []
            total_p2 = (len(pass2_items) + large_batch - 1) // large_batch
            for i in range(0, len(pass2_items), large_batch):
                batch = pass2_items[i : i + large_batch]
                logger.info(
                    "  Refiner pass 2 — batch %d/%d (%d words)...",
                    i // large_batch + 1, total_p2, len(batch),
                )
                batch_result = self._refine_batch(batch)
                pass2_results_all.extend(batch_result)
            if pass2_results_all:
                return self._merge_passes(pass1_results, pass2_results_all)

        return pass1_results

    # ── Internals ─────────────────────────────────────────────

    def _refine_batch(self, batch: list[tuple[str, str]]) -> list[dict]:
        """Refine a single batch — one LLM call, robust parsing."""
        raw_text_list = "\n".join([f"- {w} ({c})" for w, c in batch])
        prompt = self._template.replace("{raw_keywords}", raw_text_list)

        try:
            response = self._llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            logger.debug(
                "Refiner raw LLM response (%d chars): %.500s",
                len(content), content,
            )
            items = self._parse_response(content)
            return items
        except Exception as exc:
            logger.warning("Refiner batch failed: %s", exc)
            return []

    def _parse_response(self, content: str) -> list[dict]:
        """Multi-strategy JSON extraction from LLM response."""
        content = content.strip()

        # 1. Strip thinking/reasoning tags
        content = re.sub(
            r"<(thought|think|reasoning)>.*?</\1>",
            "", content, flags=re.DOTALL | re.IGNORECASE,
        )

        # 2. Try to extract JSON from markdown code blocks
        md_match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
        if md_match:
            content = md_match.group(1).strip()
            logger.debug("Refiner: extracted JSON from markdown code block")

        # 3. Try direct parse
        parsed = self._try_parse_json(content)
        if parsed is not None:
            result = self._normalize_parsed(parsed)
            logger.debug("Refiner: strategy 3 (direct parse) -> %d items", len(result))
            return result

        # 4. Try to find first [ ... ] in the text
        bracket_match = re.search(r"\[.*\]", content, re.DOTALL)
        if bracket_match:
            parsed = self._try_parse_json(bracket_match.group(0))
            if parsed is not None:
                result = self._normalize_parsed(parsed)
                logger.debug("Refiner: strategy 4 (bracket extract) -> %d items", len(result))
                return result

        # 5. Try to find first { ... } and wrap in array
        brace_match = re.search(r"\{.*\}", content, re.DOTALL)
        if brace_match:
            parsed = self._try_parse_json("[" + brace_match.group(0) + "]")
            if parsed is not None:
                result = self._normalize_parsed(parsed)
                logger.debug("Refiner: strategy 5 (brace wrap) -> %d items", len(result))
                return result

        logger.warning(
            "Refiner: could not parse response (%d chars). First 500: %s",
            len(content), content[:500],
        )
        return []

    @staticmethod
    def _try_parse_json(text: str):
        """Try to parse JSON, return None on failure."""
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            # Try fixing common issues: trailing commas
            cleaned = re.sub(r",\s*([}\]])", r"\1", text)
            try:
                return json.loads(cleaned)
            except (json.JSONDecodeError, ValueError):
                return None

    @staticmethod
    def _normalize_parsed(parsed) -> list[dict]:
        """Normalize parsed JSON into list[dict] format."""
        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict):
            # Could be {"items": [...]} or {"keywords": [...]} etc.
            items = (
                parsed.get("items")
                or parsed.get("keywords")
                or parsed.get("refined_keywords")
                or parsed.get("results")
                or parsed.get("data")
                or [parsed]
            )
        else:
            return []

        result = []
        for item in items:
            if not isinstance(item, dict):
                continue
            refined = (
                item.get("refined_word")
                or item.get("word")
                or item.get("term")
                or ""
            )
            category = item.get("category", "other")
            originals = (
                item.get("original_words")
                or item.get("originals")
                or item.get("original")
                or []
            )
            if isinstance(originals, str):
                originals = [originals]

            if refined.strip():
                result.append({
                    "refined_word": refined.strip(),
                    "category": category,
                    "original_words": originals,
                })
        return result

    # ── Cross-batch merge ─────────────────────────────────────

    def _merge_passes(
        self, pass1: list[dict], pass2: list[dict]
    ) -> list[dict]:
        """Rewrite original_words through both passes."""
        p1_originals: dict[str, list[str]] = {}
        for item in pass1:
            rw = item.get("refined_word", "").strip().lower()
            for orig in item.get("original_words", []):
                p1_originals.setdefault(rw, []).append(orig)

        merged: list[dict] = []
        for item in pass2:
            rw2 = item.get("refined_word", "").strip()
            cat2 = item.get("category", "other")
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
                "original_words": list(dict.fromkeys(all_originals)),
            })

        logger.info(
            "  Refiner: pass1=%d items -> pass2 merged to %d",
            len(pass1), len(merged),
        )
        return merged
