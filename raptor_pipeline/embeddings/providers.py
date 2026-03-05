"""Concrete embedding providers: DeepSeek API, Ollama (via LangChain)."""
from __future__ import annotations

import logging

from omegaconf import DictConfig

from raptor_pipeline.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class DeepSeekEmbeddingProvider(BaseEmbeddingProvider):
    """Embedding provider using DeepSeek API (OpenAI-compatible)."""

    def __init__(self, cfg: DictConfig) -> None:
        from langchain_openai import OpenAIEmbeddings

        self._model = OpenAIEmbeddings(
            model=cfg.get("model_name", "deepseek/deepseek-r1"),
            openai_api_key=cfg.get("api_key", ""),
            openai_api_base=cfg.get("base_url", "https://openrouter.ai/api/v1"),
        )
        self.embedding_dim: int = cfg.get("embedding_dim", 1536)
        logger.info(
            "DeepSeekEmbeddingProvider initialised (model=%s, dim=%d)",
            cfg.get("model_name"),
            self.embedding_dim,
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._model.embed_query(text)


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Embedding provider using a locally-running Ollama model."""

    def __init__(self, cfg: DictConfig) -> None:
        from langchain_ollama import OllamaEmbeddings

        self._model = OllamaEmbeddings(
            model=cfg.get("model_name", "nomic-embed-text"),
            base_url=cfg.get("base_url", "http://localhost:11434"),
        )
        self.embedding_dim: int = cfg.get("embedding_dim", 768)
        logger.info(
            "OllamaEmbeddingProvider initialised (model=%s, dim=%d)",
            cfg.get("model_name"),
            self.embedding_dim,
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._model.embed_query(text)

class HuggingFaceEmbeddingProvider(BaseEmbeddingProvider):
    """Embedding provider using local HuggingFace sentence-transformers."""

    def __init__(self, cfg: DictConfig) -> None:
        from langchain_huggingface import HuggingFaceEmbeddings

        self._model = HuggingFaceEmbeddings(
            model_name=cfg.get("model_name", "BAAI/bge-small-en-v1.5"),
            model_kwargs=cfg.get("model_kwargs", {"device": "cpu"}),
            encode_kwargs=cfg.get("encode_kwargs", {"normalize_embeddings": True}),
        )
        self.embedding_dim: int = cfg.get("embedding_dim", 384)
        logger.info(
            "HuggingFaceEmbeddingProvider initialised (model=%s, dim=%d)",
            cfg.get("model_name"),
            self.embedding_dim,
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._model.embed_query(text)

def create_embedding_provider(cfg: DictConfig) -> BaseEmbeddingProvider:
    """Factory — create an embedding provider from Hydra config.

    The config must contain a ``provider`` key (``deepseek`` | ``ollama`` | ``huggingface``).
    """
    provider = cfg.get("provider", "deepseek")
    if provider == "deepseek":
        return DeepSeekEmbeddingProvider(cfg)
    if provider == "ollama":
        return OllamaEmbeddingProvider(cfg)
    if provider == "huggingface":
        return HuggingFaceEmbeddingProvider(cfg)
    raise ValueError(f"Unknown embedding provider: {provider}")
