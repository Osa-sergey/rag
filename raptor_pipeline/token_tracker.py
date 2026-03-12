"""Thread-safe token usage tracker for LLM components.

Extracts token counts from LangChain AIMessage.response_metadata,
accumulates per-component, logs summaries, and appends CSV.

Supported providers:
  - OpenAI-compatible (ChatOpenAI / llama.cpp): response_metadata.token_usage
  - Ollama (ChatOllama): response_metadata.prompt_eval_count / eval_count
"""
from __future__ import annotations

import csv
import logging
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Accumulated token counts for one component."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    call_count: int = 0

    def __iadd__(self, other: TokenUsage) -> TokenUsage:
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.cached_tokens += other.cached_tokens
        self.total_tokens += other.total_tokens
        self.call_count += other.call_count
        return self


# Component names used as keys
COMPONENTS = (
    "summarizer",
    "keyword_extractor",
    "keyword_refiner",
    "relation_extractor",
)


def _extract_token_usage(response: Any) -> TokenUsage:
    """Extract token usage from a LangChain AIMessage response.

    Handles both OpenAI-compatible and Ollama response formats.
    Returns a zero TokenUsage if no token data is found.
    """
    meta = getattr(response, "response_metadata", None) or {}

    # ── OpenAI-compatible format ──────────────────────────────
    token_usage = meta.get("token_usage") or meta.get("usage") or {}
    if token_usage:
        prompt = token_usage.get("prompt_tokens", 0) or 0
        completion = token_usage.get("completion_tokens", 0) or 0
        total = token_usage.get("total_tokens", 0) or (prompt + completion)

        # Cached tokens (OpenAI): nested in prompt_tokens_details
        cached = 0
        details = token_usage.get("prompt_tokens_details") or {}
        if isinstance(details, dict):
            cached = details.get("cached_tokens", 0) or 0

        return TokenUsage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            cached_tokens=cached,
            total_tokens=total,
            call_count=1,
        )

    # ── Ollama format ─────────────────────────────────────────
    prompt = meta.get("prompt_eval_count", 0) or 0
    completion = meta.get("eval_count", 0) or 0
    if prompt or completion:
        return TokenUsage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            cached_tokens=0,
            total_tokens=prompt + completion,
            call_count=1,
        )

    return TokenUsage(call_count=1)


class TokenTracker:
    """Thread-safe per-component token accumulator.

    Usage::

        tracker = TokenTracker()
        # In each LLM component after invoke():
        tracker.track(response, "summarizer")

        # After processing an article:
        tracker.log_summary(article_id)
        tracker.save_csv("outputs/token_usage.csv", article_id, article_name)
        tracker.reset()
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._usage: dict[str, TokenUsage] = {c: TokenUsage() for c in COMPONENTS}

    def track(self, response: Any, component: str) -> TokenUsage:
        """Extract token usage from response and accumulate.

        Args:
            response: LangChain AIMessage or similar.
            component: One of COMPONENTS.

        Returns:
            TokenUsage for this single call.
        """
        usage = _extract_token_usage(response)
        with self._lock:
            if component not in self._usage:
                self._usage[component] = TokenUsage()
            self._usage[component] += usage
        return usage

    def get_usage(self, component: str) -> TokenUsage:
        """Get accumulated usage for a component."""
        with self._lock:
            return TokenUsage(**asdict(self._usage.get(component, TokenUsage())))

    def get_total(self) -> TokenUsage:
        """Get total usage across all components."""
        total = TokenUsage()
        with self._lock:
            for u in self._usage.values():
                total += u
        return total

    def summary_dict(self) -> dict[str, Any]:
        """Build a flat dict for logging / JSON output."""
        result: dict[str, Any] = {}
        with self._lock:
            for comp, usage in self._usage.items():
                prefix = comp
                result[f"{prefix}_prompt_tokens"] = usage.prompt_tokens
                result[f"{prefix}_completion_tokens"] = usage.completion_tokens
                result[f"{prefix}_cached_tokens"] = usage.cached_tokens
                result[f"{prefix}_total_tokens"] = usage.total_tokens
                result[f"{prefix}_calls"] = usage.call_count
        total = self.get_total()
        result["total_prompt_tokens"] = total.prompt_tokens
        result["total_completion_tokens"] = total.completion_tokens
        result["total_cached_tokens"] = total.cached_tokens
        result["total_tokens"] = total.total_tokens
        result["total_calls"] = total.call_count
        return result

    def log_summary(self, article_id: str) -> None:
        """Log a human-readable summary of token usage."""
        total = self.get_total()
        if total.total_tokens == 0 and total.call_count == 0:
            return

        logger.info(
            "  📊 Token usage for '%s': %d total "
            "(prompt=%d, completion=%d, cached=%d) in %d calls",
            article_id,
            total.total_tokens,
            total.prompt_tokens,
            total.completion_tokens,
            total.cached_tokens,
            total.call_count,
        )
        with self._lock:
            for comp, usage in self._usage.items():
                if usage.call_count > 0:
                    logger.info(
                        "      %-20s %6d tokens (%d prompt, %d completion, %d cached) [%d calls]",
                        comp,
                        usage.total_tokens,
                        usage.prompt_tokens,
                        usage.completion_tokens,
                        usage.cached_tokens,
                        usage.call_count,
                    )

    def save_csv(
        self,
        path: str | Path,
        article_id: str,
        article_name: str = "",
    ) -> None:
        """Append one row to a CSV file.

        Creates the file with headers if it doesn't exist yet.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        write_header = not path.exists()

        row = {"article_id": article_id, "article_name": article_name}
        row.update(self.summary_dict())

        fieldnames = list(row.keys())

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(row)

        logger.debug("  Token usage saved to %s", path)

    def reset(self) -> None:
        """Reset all counters (call between articles)."""
        with self._lock:
            for comp in self._usage:
                self._usage[comp] = TokenUsage()
