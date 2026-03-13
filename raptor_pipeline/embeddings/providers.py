"""Concrete embedding providers: DeepSeek API, Ollama (via LangChain)."""
from __future__ import annotations

import logging
import threading

from omegaconf import DictConfig

from interfaces import BaseEmbeddingProvider

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
        self._embedding_dim: int = cfg.get("embedding_dim", 1536)
        logger.info(
            "DeepSeekEmbeddingProvider initialised (model=%s, dim=%d)",
            cfg.get("model_name"),
            self._embedding_dim,
        )

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

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
        self._embedding_dim: int = cfg.get("embedding_dim", 768)
        logger.info(
            "OllamaEmbeddingProvider initialised (model=%s, dim=%d)",
            cfg.get("model_name"),
            self._embedding_dim,
        )

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._model.embed_query(text)

class HuggingFaceEmbeddingProvider(BaseEmbeddingProvider):
    """Embedding provider using local HuggingFace sentence-transformers."""

    def __init__(self, cfg: DictConfig) -> None:
        from langchain_huggingface import HuggingFaceEmbeddings
        import os

        # Prefer local_path if set and directory exists; fallback to model_name (HF Hub download)
        local_path = cfg.get("local_path", None)
        if local_path and os.path.isdir(local_path):
            model_id = local_path
            logger.info("Loading HuggingFace model from local path: %s", local_path)
        else:
            model_id = cfg.get("model_name", "BAAI/bge-small-en-v1.5")
            if local_path:
                logger.warning(
                    "local_path '%s' not found, falling back to download '%s' from HuggingFace Hub",
                    local_path, model_id,
                )
            else:
                logger.info("No local_path set, downloading '%s' from HuggingFace Hub", model_id)

        self._model = HuggingFaceEmbeddings(
            model_name=model_id,
            model_kwargs=cfg.get("model_kwargs", {"device": "cpu"}),
            encode_kwargs=cfg.get("encode_kwargs", {"normalize_embeddings": True}),
        )
        self._embedding_dim: int = cfg.get("embedding_dim", 384)
        self._batch_size: int = cfg.get("embed_batch_size", 32)
        self._lock = threading.Lock()
        logger.info(
            "HuggingFaceEmbeddingProvider initialised (model=%s, dim=%d, batch=%d)",
            model_id,
            self._embedding_dim,
            self._batch_size,
        )

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed texts in batches to avoid GPU OOM on large articles.

        Uses a lock to serialise GPU access — MPS does not support
        concurrent operations from multiple threads.
        """
        if len(texts) <= self._batch_size:
            with self._lock:
                return self._model.embed_documents(texts)

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            with self._lock:
                all_embeddings.extend(self._model.embed_documents(batch))
        return all_embeddings

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
