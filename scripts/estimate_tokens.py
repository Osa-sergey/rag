"""Dry-run token estimation: real pipeline + fake LLMs.

Runs RAPTOR pipeline on 100 random articles from parsed_yaml/
with real chunking & embeddings but fake LLM calls that
return realistic text + token usage metadata.

Usage:
    python scripts/estimate_tokens.py
"""
from __future__ import annotations

import json
import logging
import random
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# Fix Windows console encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s: %(message)s",
)
logger = logging.getLogger("estimate_tokens")

# ── Fake AIMessage -------------------------------------------------------

class FakeAIMessage:
    """Mimics LangChain AIMessage with response_metadata for token tracking."""

    def __init__(self, content: str, prompt_tokens: int, completion_tokens: int):
        self.content = content
        self.response_metadata = {
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "prompt_tokens_details": {"cached_tokens": 0},
            }
        }


def _estimate_prompt_tokens(text: str) -> int:
    """Rough token estimate: ~1 token per 3.5 chars for Russian text."""
    return max(10, len(text) // 4)


# ── Fake LLM class -------------------------------------------------------

class FakeLLM:
    """Drop-in replacement for LangChain ChatModel.

    Returns FakeAIMessage with completion tokens = 75%±5% of max_tokens.
    """

    def __init__(self, max_tokens: int = 2048):
        self._max_tokens = max_tokens

    def _completion_tokens(self) -> int:
        """75% ± 5% of max_tokens."""
        base = int(self._max_tokens * 0.75)
        jitter = int(self._max_tokens * 0.05)
        return max(20, base + random.randint(-jitter, jitter))

    def invoke(self, prompt) -> FakeAIMessage:
        prompt_text = str(prompt)
        prompt_tokens = _estimate_prompt_tokens(prompt_text)
        completion_tokens = self._completion_tokens()

        return FakeAIMessage(
            content="Это фейковое резюме для оценки токенов. "
                    "Текст содержит основные идеи исходного документа.",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def with_structured_output(self, schema):
        """Return self — structured output calls go through invoke too."""
        return self


class FakeLLMForKeywords(FakeLLM):
    """Fake LLM that returns JSON keyword output (75% of max_keywords)."""

    def __init__(self, max_tokens: int = 2048, max_keywords: int = 5):
        super().__init__(max_tokens)
        self._kw_count = max(1, int(max_keywords * 0.75))

    def invoke(self, prompt) -> FakeAIMessage:
        prompt_tokens = _estimate_prompt_tokens(str(prompt))
        completion_tokens = self._completion_tokens()

        keywords = [
            {"word": f"keyword_{i}", "category": "technology", "confidence": 0.9}
            for i in range(self._kw_count)
        ]
        content = json.dumps({"keywords": keywords})

        return FakeAIMessage(content=content,
                             prompt_tokens=prompt_tokens,
                             completion_tokens=completion_tokens)


class FakeLLMForRelations(FakeLLM):
    """Fake LLM that returns JSON relation output (75% of max_relations)."""

    def __init__(self, max_tokens: int = 2048, max_relations: int = 10):
        super().__init__(max_tokens)
        self._rel_count = max(1, int(max_relations * 0.75))

    def invoke(self, prompt) -> FakeAIMessage:
        prompt_tokens = _estimate_prompt_tokens(str(prompt))
        completion_tokens = self._completion_tokens()

        relations = [
            {"subject": f"subj_{i}", "predicate": "связан_с",
             "object": f"obj_{i}", "confidence": 0.85}
            for i in range(self._rel_count)
        ]
        content = json.dumps({"relations": relations})

        return FakeAIMessage(content=content,
                             prompt_tokens=prompt_tokens,
                             completion_tokens=completion_tokens)


class FakeLLMForRefiner(FakeLLM):
    """Fake LLM that returns refined keywords JSON."""

    def invoke(self, prompt) -> FakeAIMessage:
        prompt_tokens = _estimate_prompt_tokens(str(prompt))
        completion_tokens = self._completion_tokens()

        refined = [
            {"canonical": f"keyword_{i}", "category": "technology",
             "original_words": [f"keyword_{i}"]}
            for i in range(4)
        ]
        content = json.dumps(refined)

        return FakeAIMessage(content=content,
                             prompt_tokens=prompt_tokens,
                             completion_tokens=completion_tokens)


# ── Patched _build_llm ---------------------------------------------------

_COMPONENT_COUNTER = {"call": 0}

def _fake_build_llm(cfg):
    """Replace _build_llm: return FakeLLM with max_tokens from config."""
    max_tokens = cfg.get("max_tokens", 2048)
    return FakeLLM(max_tokens=max_tokens)


# ── Mock stores -----------------------------------------------------------

class MockVectorStore:
    def ensure_collection(self): pass
    def upsert_nodes(self, *a, **kw): pass

class MockGraphStore:
    def ensure_indexes(self): pass
    def store_article(self, *a, **kw): pass
    def store_keywords(self, *a, **kw): pass
    def store_relations(self, *a, **kw): pass
    def store_links(self, *a, **kw): pass
    def close(self): pass


# ── Main ------------------------------------------------------------------

def main():
    from hydra import compose, initialize_config_dir
    from omegaconf import OmegaConf

    CONFIG_DIR = str(Path(__file__).resolve().parent.parent / "raptor_pipeline" / "conf")

    logger.info("Loading config...")
    with initialize_config_dir(config_dir=CONFIG_DIR, version_base=None):
        cfg = compose(config_name="config")

    # Find all YAML files
    input_dir = Path(cfg.get("input_dir", "parsed_yaml"))
    if not input_dir.is_absolute():
        input_dir = Path(__file__).resolve().parent.parent / input_dir
    all_files = sorted(input_dir.glob("*.yaml"))
    logger.info("Found %d YAML files in %s", len(all_files), input_dir)

    # Sample 100 random files (or all if < 25)
    sample_size = min(25, len(all_files))
    sample_files = random.sample(all_files, sample_size)
    logger.info("Sampled %d files for estimation", sample_size)

    # Patch _build_llm in ALL modules that import it
    with patch("raptor_pipeline.summarizer.llm_summarizer._build_llm", _fake_build_llm), \
         patch("raptor_pipeline.knowledge_graph.keyword_extractor._build_llm", _fake_build_llm), \
         patch("raptor_pipeline.knowledge_graph.keyword_refiner._build_llm", _fake_build_llm), \
         patch("raptor_pipeline.knowledge_graph.relation_extractor._build_llm", _fake_build_llm):

        from raptor_pipeline.pipeline import RaptorPipeline

        logger.info("Creating pipeline with REAL embeddings + FAKE LLMs...")
        pipeline = RaptorPipeline(
            cfg,
            vector_store=MockVectorStore(),
            graph_store=MockGraphStore(),
        )

        # Override token output path
        pipeline._token_output_path = "outputs/token_estimation_dry_run.csv"

        results = []
        total_start = time.time()

        for i, yaml_path in enumerate(sample_files, 1):
            try:
                logger.info("─── [%d/%d] %s ───", i, sample_size, yaml_path.name)
                result = pipeline.process_file(yaml_path)
                results.append(result)
            except Exception as exc:
                logger.error("Failed %s: %s", yaml_path.name, exc)

        elapsed = time.time() - total_start

    # ── Report ──────────────────────────────────────────────────
    if not results:
        logger.error("No results!")
        return

    # Aggregate token stats
    total_tokens_all = 0
    total_calls_all = 0
    component_totals = {}

    for r in results:
        tu = r.get("token_usage", {})
        total_tokens_all += tu.get("total_tokens", 0)
        total_calls_all += tu.get("total_calls", 0)

        for key, val in tu.items():
            if key.endswith("_tokens") or key.endswith("_calls"):
                component_totals[key] = component_totals.get(key, 0) + val

    n = len(results)
    avg_tokens = total_tokens_all / n
    avg_calls = total_calls_all / n
    avg_chunks = sum(r["chunks"] for r in results) / n
    avg_nodes = sum(r["raptor_nodes"] for r in results) / n
    avg_keywords = sum(r["keywords"] for r in results) / n
    avg_relations = sum(r["relations"] for r in results) / n

    print("\n" + "═" * 60)
    print(f"  DRY-RUN TOKEN ESTIMATION ({n} articles)")
    print("═" * 60)
    print(f"  Avg chunks/article:      {avg_chunks:.1f}")
    print(f"  Avg RAPTOR nodes/article:{avg_nodes:.1f}")
    print(f"  Avg keywords/article:    {avg_keywords:.1f}")
    print(f"  Avg relations/article:   {avg_relations:.1f}")
    print(f"  Avg LLM calls/article:   {avg_calls:.1f}")
    print(f"  Avg tokens/article:      {avg_tokens:.0f}")
    print()
    print("  Per-component averages:")
    for comp in ["summarizer", "keyword_extractor", "keyword_refiner", "relation_extractor"]:
        pt = component_totals.get(f"{comp}_prompt_tokens", 0) / n
        ct = component_totals.get(f"{comp}_completion_tokens", 0) / n
        tt = component_totals.get(f"{comp}_total_tokens", 0) / n
        calls = component_totals.get(f"{comp}_calls", 0) / n
        print(f"    {comp:25s} {tt:8.0f} tok/article "
              f"(p={pt:.0f} c={ct:.0f}) [{calls:.1f} calls]")
    print()
    print(f"  TOTAL across {n} articles: {total_tokens_all:,} tokens in {total_calls_all:,} calls")
    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"  CSV saved: outputs/token_estimation_dry_run.csv")
    print("═" * 60)


if __name__ == "__main__":
    main()
