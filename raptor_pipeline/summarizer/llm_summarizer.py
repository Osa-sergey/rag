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
