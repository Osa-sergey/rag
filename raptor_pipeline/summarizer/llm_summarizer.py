"""LLM-based summariser using LangChain (DeepSeek / Ollama / llama.cpp)."""
from __future__ import annotations

import logging

from omegaconf import DictConfig

from raptor_pipeline.summarizer.base import BaseSummarizer

logger = logging.getLogger(__name__)


def _build_llm(cfg: DictConfig):
    """Build a LangChain LLM / ChatModel from Hydra config."""
    provider = cfg.get("provider", "deepseek")
    if provider == "deepseek":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=cfg.get("model_name", "deepseek/deepseek-r1"),
            openai_api_key=cfg.get("api_key", ""),
            openai_api_base=cfg.get("base_url", "https://openrouter.ai/api/v1"),
            temperature=cfg.get("temperature", 0.3),
            max_tokens=cfg.get("max_tokens", 1024),
            default_headers={
                "HTTP-Referer": "https://github.com/langchain-ai/langchain",
                "X-Title": "RAPTOR Pipeline",
            },
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=cfg.get("model_name", "deepseek-r1:7b"),
            base_url=cfg.get("base_url", "http://localhost:11434"),
            temperature=cfg.get("temperature", 0.3),
            num_predict=cfg.get("max_tokens", 1024),
            format=cfg.get("format"),
        )
    if provider == "llama_cpp":
        from langchain_openai import ChatOpenAI

        # llama-server exposes an OpenAI-compatible API.
        # Use --parallel N on the server for true continuous batching.
        return ChatOpenAI(
            model=cfg.get("model_name", "gemma-3-12b-it"),
            openai_api_key="no-key-required",
            openai_api_base=cfg.get("base_url", "http://localhost:8080/v1"),
            temperature=cfg.get("temperature", 0.1),
            max_tokens=cfg.get("max_tokens", 2048),
        )
    raise ValueError(f"Unknown LLM provider: {provider}")


class LLMSummarizer(BaseSummarizer):
    """Summarises groups of text chunks using an LLM.

    The prompt template is loaded from the Hydra config section
    ``prompts.summarize``.
    """

    def __init__(self, cfg: DictConfig, prompt_cfg: DictConfig, *, tracker=None) -> None:
        self._llm = _build_llm(cfg)
        self._tracker = tracker
        self._template: str = prompt_cfg.get(
            "template",
            (
                "Ты — аналитический ассистент.  Прочитай следующие тексты и "
                "напиши краткое резюме, сохраняя ключевые идеи и факты.\n\n"
                "{text}\n\n"
                "Резюме:"
            ),
        )
        self._prompt_version: str = prompt_cfg.get("version", "1.0")
        logger.info(
            "LLMSummarizer ready (prompt v%s, provider=%s)",
            self._prompt_version,
            cfg.get("provider"),
        )

    def summarize(self, texts: list[str]) -> str:
        combined = "\n---\n".join(texts)
        prompt = self._template.replace("{text}", combined)
        response = self._llm.invoke(prompt)
        if self._tracker:
            self._tracker.track(response, "summarizer")
        # LangChain ChatModel returns AIMessage; plain LLM returns str
        if hasattr(response, "content"):
            return response.content.strip()
        return str(response).strip()

    def summarize_token_aware(
        self,
        texts: list[str],
        *,
        max_tokens: int = 3500,
        overflow_strategy: str = "multi_stage",
        chars_per_token: float = 2.5,
    ) -> str | None:
        """Summarize with a token-length pre-check.

        If the combined text fits within *max_tokens*, delegates to
        :meth:`summarize`.  Otherwise applies *overflow_strategy*:

        * ``"multi_stage"`` – split texts into groups that fit within
          *max_tokens*, summarize each group, then recursively summarize
          the intermediate summaries until the result fits.
        * ``"levels_only"`` – return ``None`` as a signal to the caller
          to drop orphan leaves and retry with L1–LN nodes only.
        """
        from raptor_pipeline.token_utils import estimate_tokens

        combined = "\n---\n".join(texts)
        total_tokens = estimate_tokens(combined, chars_per_token)

        logger.info(
            "  + Token check: %d tokens (max %d, strategy=%s)",
            total_tokens, max_tokens, overflow_strategy,
        )

        if total_tokens <= max_tokens:
            return self.summarize(texts)

        # ── Overflow handling ──────────────────────────────────
        if overflow_strategy == "levels_only":
            logger.info(
                "  + Token overflow (%d > %d): signalling levels_only fallback",
                total_tokens, max_tokens,
            )
            return None

        # ── multi_stage (default) ─────────────────────────────
        logger.info(
            "  + Token overflow (%d > %d): applying multi-stage summarization",
            total_tokens, max_tokens,
        )
        return self._multi_stage_summarize(texts, max_tokens, chars_per_token)

    def _multi_stage_summarize(
        self,
        texts: list[str],
        max_tokens: int,
        chars_per_token: float,
    ) -> str:
        """Split *texts* into token-budget groups and summarize in stages."""
        from raptor_pipeline.token_utils import estimate_tokens

        max_chars = int(max_tokens * chars_per_token)
        separator = "\n---\n"
        sep_len = len(separator)

        # Greedily pack texts into groups that fit within max_chars
        groups: list[list[str]] = []
        current_group: list[str] = []
        current_len = 0

        for text in texts:
            text_len = len(text)
            # Length the group would become after appending this text
            added_len = (sep_len + text_len) if current_group else text_len

            if current_group and current_len + added_len > max_chars:
                groups.append(current_group)
                current_group = [text]
                current_len = text_len
            else:
                current_group.append(text)
                current_len += added_len

        if current_group:
            groups.append(current_group)

        logger.info(
            "  + Multi-stage: split %d texts into %d groups",
            len(texts), len(groups),
        )

        # Summarize each group
        stage_summaries: list[str] = []
        for i, group in enumerate(groups):
            logger.info(
                "    ↳ group %d/%d: %d texts, ~%d tokens",
                i + 1, len(groups), len(group),
                estimate_tokens(separator.join(group), chars_per_token),
            )
            summary = self.summarize(group)
            stage_summaries.append(summary)

        # If only 1 group resulted, we're done
        if len(stage_summaries) == 1:
            return stage_summaries[0]

        # Check if intermediate summaries fit within budget
        merged = separator.join(stage_summaries)
        merged_tokens = estimate_tokens(merged, chars_per_token)

        if merged_tokens <= max_tokens:
            logger.info(
                "  + Multi-stage final: %d intermediate summaries "
                "(%d tokens) → final summarization",
                len(stage_summaries), merged_tokens,
            )
            return self.summarize(stage_summaries)

        # Recurse if still too long
        logger.info(
            "  + Multi-stage: intermediate summaries still %d tokens "
            "(> %d), recursing...",
            merged_tokens, max_tokens,
        )
        return self._multi_stage_summarize(
            stage_summaries, max_tokens, chars_per_token,
        )

