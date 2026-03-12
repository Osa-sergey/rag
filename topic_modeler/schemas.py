"""Pydantic configuration schemas for Topic Modeler.

Validates all parameters at startup so errors are caught before
training starts (which may take minutes).

Cross-field validations:
  - hdbscan.min_cluster_size >= bertopic.min_topic_size
  - umap.n_components < embeddings.embedding_dim
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Enums ─────────────────────────────────────────────────────

class UmapMetric(str, Enum):
    cosine = "cosine"
    euclidean = "euclidean"
    manhattan = "manhattan"
    correlation = "correlation"


class HdbscanMetric(str, Enum):
    euclidean = "euclidean"
    manhattan = "manhattan"
    cosine = "cosine"


class ClusterMethod(str, Enum):
    eom = "eom"
    leaf = "leaf"


class Device(str, Enum):
    cpu = "cpu"
    cuda = "cuda"
    mps = "mps"


# ── Sub-configs ───────────────────────────────────────────────

class UmapConfig(BaseModel):
    """UMAP — снижение размерности эмбеддингов."""
    n_neighbors: int = Field(15, ge=2, le=200, description="Число ближайших соседей")
    n_components: int = Field(5, ge=2, le=100, description="Размерность проекции")
    min_dist: float = Field(0.1, ge=0.0, le=1.0, description="Минимальная дистанция")
    metric: UmapMetric = Field(UmapMetric.cosine, description="Метрика расстояния")


class HdbscanConfig(BaseModel):
    """HDBSCAN — кластеризация."""
    min_cluster_size: int = Field(5, ge=2, le=500, description="Минимальный размер кластера")
    min_samples: int = Field(1, ge=1, le=100, description="Минимальная плотность")
    metric: HdbscanMetric = Field(HdbscanMetric.euclidean, description="Метрика расстояния")
    cluster_selection_method: ClusterMethod = Field(
        ClusterMethod.eom, description="Метод выбора кластеров"
    )


class VectorizerConfig(BaseModel):
    """CountVectorizer — токенизация для BERTopic."""
    min_df: int = Field(2, ge=1, description="Минимальная document frequency")
    ngram_range: list[int] = Field([1, 2], description="Диапазон N-грамм [min, max]")
    stop_words: Optional[str] = Field(None, description="Стоп-слова (null = без)")

    @field_validator("ngram_range")
    @classmethod
    def validate_ngram(cls, v: list[int]) -> list[int]:
        if len(v) != 2:
            raise ValueError(f"ngram_range должен быть [min, max], получено {len(v)} элементов")
        if v[0] < 1 or v[1] < v[0]:
            raise ValueError(f"ngram_range: min >= 1 и max >= min, получено {v}")
        return v


class BertopicConfig(BaseModel):
    """BERTopic — основные параметры модели."""
    language: str = Field("russian", description="Язык текстов")
    top_n_words: int = Field(15, ge=1, le=50, description="Слов на топик")
    min_topic_size: int = Field(3, ge=2, le=100, description="Минимальный размер топика")
    nr_topics: Optional[int] = Field(None, ge=2, description="Число топиков (null = авто)")


class KeyBERTConfig(BaseModel):
    top_n_words: int = Field(10, ge=1, le=50)


class MMRConfig(BaseModel):
    diversity: float = Field(0.3, ge=0.0, le=1.0, description="Разнообразие ключевых слов")


class RepresentationConfig(BaseModel):
    """Representation models — улучшение меток топиков."""
    use_keybert: bool = Field(True, description="Использовать KeyBERT")
    keybert: KeyBERTConfig = Field(default_factory=KeyBERTConfig)
    use_mmr: bool = Field(True, description="Использовать MMR")
    mmr: MMRConfig = Field(default_factory=MMRConfig)


class EmbeddingsConfig(BaseModel):
    """Настройки эмбеддинг-провайдера.

    _class_ указывает конкретную реализацию BaseEmbeddingProvider.
    """
    class_: str = Field(
        "raptor_pipeline.embeddings.providers.HuggingFaceEmbeddingProvider",
        alias="_class_",
        description="Dotted path к классу-реализации BaseEmbeddingProvider",
    )
    provider: str = Field("huggingface", description="Провайдер эмбеддингов")
    model_name: str = Field("sergeyzh/BERTA", description="Название модели")
    local_path: Optional[str] = Field(None, description="Локальный путь к модели")
    model_kwargs: dict = Field(default_factory=lambda: {"device": "cuda"})
    encode_kwargs: dict = Field(default_factory=lambda: {"normalize_embeddings": True})
    embedding_dim: int = Field(768, ge=1, description="Размерность эмбеддинга")

    model_config = {"populate_by_name": True}

    @property
    def device(self) -> str:
        return self.model_kwargs.get("device", "cpu")


class GraphStoreConfig(BaseModel):
    """Конфигурация графового хранилища.

    _class_ указывает конкретную реализацию BaseGraphStore.
    """
    class_: str = Field(
        "stores.graph_store.Neo4jGraphStore",
        alias="_class_",
        description="Dotted path к классу-реализации BaseGraphStore",
    )
    uri: str = Field("bolt://localhost:7687", description="URI подключения")
    user: str = Field("neo4j", description="Пользователь")
    password: str = Field(..., description="Пароль")
    database: str = Field("neo4j", description="Имя базы данных")

    model_config = {"populate_by_name": True}


class StoresConfig(BaseModel):
    graph_store: GraphStoreConfig


# ── Root config ───────────────────────────────────────────────

class TopicModelerConfig(BaseModel):
    """Корневая конфигурация Topic Modeler.

    Cross-field validations:
      - hdbscan.min_cluster_size >= bertopic.min_topic_size
      - umap.n_components < embeddings.embedding_dim
    """
    mode: str = Field("train", description="Режим: train | add_article")
    input_dir: str = Field("parsed_yaml", description="Директория с YAML-статьями")
    article_path: Optional[str] = Field(None, description="Путь к статье (add_article)")
    model_dir: str = Field("outputs/bertopic_model", description="Директория модели")
    csv_paths: list[str] = Field(default_factory=list, description="CSV с метаданными")

    umap: UmapConfig = Field(default_factory=UmapConfig)
    hdbscan: HdbscanConfig = Field(default_factory=HdbscanConfig)
    vectorizer: VectorizerConfig = Field(default_factory=VectorizerConfig)
    bertopic: BertopicConfig = Field(default_factory=BertopicConfig)
    representation: RepresentationConfig = Field(default_factory=RepresentationConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    stores: StoresConfig

    # Hydra defaults key — ignore it
    defaults: Optional[list] = Field(None, exclude=True)

    @model_validator(mode="after")
    def validate_cross_fields(self) -> "TopicModelerConfig":
        # Кластер не может быть меньше мин. размера топика
        if self.hdbscan.min_cluster_size < self.bertopic.min_topic_size:
            raise ValueError(
                f"hdbscan.min_cluster_size ({self.hdbscan.min_cluster_size}) "
                f"должен быть >= bertopic.min_topic_size ({self.bertopic.min_topic_size})"
            )
        # Проекция UMAP не может превышать размерность эмбеддинга
        if self.umap.n_components >= self.embeddings.embedding_dim:
            raise ValueError(
                f"umap.n_components ({self.umap.n_components}) "
                f"должен быть < embeddings.embedding_dim ({self.embeddings.embedding_dim})"
            )
        return self
