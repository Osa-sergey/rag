"""Pydantic configuration schemas and data models for Voice Expense Bot.

Config hierarchy mirrors raptor_pipeline: Hydra YAML → Pydantic validation → DI.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enums ─────────────────────────────────────────────────────


class LLMProvider(str, Enum):
    llama_cpp = "llama_cpp"
    ollama = "ollama"


class EmbeddingProviderType(str, Enum):
    huggingface = "huggingface"
    ollama = "ollama"


# ── Sub-configs ───────────────────────────────────────────────


class TranscriberConfig(BaseModel):
    """GigaAM transcriber configuration."""

    model_name: str = "v3_e2e_rnnt"
    use_vad: bool = True
    vad_threshold: float = Field(0.5, ge=0.0, le=1.0, description="Silero VAD порог")
    max_short_duration: float = Field(
        25.0, ge=1.0, description="Макс. длина для short-form (секунды)"
    )

    class Config:
        extra = "allow"


class LLMConfig(BaseModel):
    """LLM provider configuration (llama-cpp / Ollama)."""

    provider: LLMProvider = LLMProvider.llama_cpp
    model_name: str = "gemma-3-12b-it"
    base_url: str = "http://localhost:8080/v1"
    api_key: Optional[str] = None
    temperature: float = Field(0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(2048, ge=1)

    class Config:
        extra = "allow"


class EmbeddingsConfig(BaseModel):
    """Embedding provider configuration (BERTA by default)."""

    provider: EmbeddingProviderType = EmbeddingProviderType.huggingface
    model_name: str = "sergeyzh/BERTA"
    local_path: Optional[str] = None
    embedding_dim: int = Field(768, ge=1)
    model_kwargs: dict[str, Any] = Field(
        default_factory=lambda: {"device": "cpu"}
    )
    encode_kwargs: dict[str, Any] = Field(
        default_factory=lambda: {"normalize_embeddings": True}
    )

    class Config:
        extra = "allow"


class DatabaseConfig(BaseModel):
    """PostgreSQL configuration."""

    host: str = "localhost"
    port: int = Field(5432, ge=1, le=65535)
    user: str = "postgres"
    password: str = "password"
    database: str = "expenses"
    schema_name: str = "voice_expenses"

    class Config:
        extra = "allow"

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class TelegramConfig(BaseModel):
    """Telegram bot configuration."""

    bot_token: str = ""

    class Config:
        extra = "allow"


class CategoryDef(BaseModel):
    """Single expense category definition with example descriptions."""

    name: str
    display_name: str
    examples: list[str] = Field(default_factory=list)


class CategoriesConfig(BaseModel):
    """All expense categories for embedding-based classification."""

    items: list[CategoryDef] = Field(default_factory=lambda: [
        CategoryDef(
            name="food",
            display_name="Еда",
            examples=["обед в кафе", "продукты в магазине", "ужин в ресторане", "кофе"],
        ),
        CategoryDef(
            name="transport",
            display_name="Транспорт",
            examples=["такси", "метро", "бензин", "каршеринг", "автобус"],
        ),
        CategoryDef(
            name="entertainment",
            display_name="Развлечения",
            examples=["кино", "концерт", "бар", "игры", "подписка"],
        ),
        CategoryDef(
            name="clothing",
            display_name="Одежда",
            examples=["футболка", "джинсы", "кроссовки", "куртка"],
        ),
        CategoryDef(
            name="health",
            display_name="Здоровье",
            examples=["аптека", "врач", "анализы", "стоматолог", "лекарства"],
        ),
        CategoryDef(
            name="communication",
            display_name="Связь",
            examples=["мобильная связь", "интернет", "оплата телефона"],
        ),
        CategoryDef(
            name="housing",
            display_name="Жильё",
            examples=["аренда", "коммунальные", "ремонт", "мебель"],
        ),
        CategoryDef(
            name="other",
            display_name="Другое",
            examples=["подарок", "штраф", "прочие расходы"],
        ),
    ])

    class Config:
        extra = "allow"


# ── Root config ───────────────────────────────────────────────


class VoiceExpenseConfig(BaseModel):
    """Root configuration for Voice Expense Bot.

    Validated at startup; all sub-configs are expanded from
    Hydra defaults composition.
    """

    log_level: str = "INFO"
    log_file: Optional[str] = Field(None, description="Путь к файлу логов JSON (None = только консоль)")

    transcriber: TranscriberConfig = Field(default_factory=TranscriberConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    categories: CategoriesConfig = Field(default_factory=CategoriesConfig)

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"log_level must be one of {valid}, got '{v}'")
        return v.upper()

    class Config:
        extra = "allow"


# ── Data models ───────────────────────────────────────────────


class Expense(BaseModel):
    """Structured expense record extracted from voice message."""

    amount: float = Field(..., description="Сумма траты")
    currency: str = Field("RUB", description="Валюта")
    category: str = Field(..., description="Категория расхода")
    description: str = Field(..., description="Краткое описание покупки")
    date: str = Field(..., description="Дата в формате YYYY-MM-DD")


class Transfer(BaseModel):
    """Structured transfer record extracted from voice message."""

    amount: float = Field(..., description="Сумма перевода")
    currency: str = Field("RUB", description="Валюта")
    from_person: str = Field(..., description="Кто переводит")
    to_person: str = Field(..., description="Кому переводят")
    date: str = Field(..., description="Дата в формате YYYY-MM-DD")
    description: str = Field("", description="Описание перевода")


class ClassificationResult(BaseModel):
    """Intent classification result."""

    intent: Literal["expense", "transfer", "unknown"]
    confidence: float = Field(..., ge=0.0, le=1.0)
