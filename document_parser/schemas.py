"""Pydantic configuration schemas for Document Parser."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class DocumentParserConfig(BaseModel):
    """Root configuration for document_parser CLI.

    Validated at startup via Hydra + Pydantic.
    """

    # Директория для выходных YAML-файлов (результат парсинга)
    output_dir: str = Field("parsed_yaml", description="Директория для сохранения YAML")

    # Входной файл (CSV / Markdown / YAML — зависит от команды)
    input_file: Optional[str] = Field(None, description="Входной файл для обработки")

    # Колонка с HTML-контентом при парсинге CSV
    html_column: str = Field("content_html", description="Имя колонки с HTML в CSV")

    # Директория для извлечённых ассетов (images/links)
    assets_dir: str = Field("assets", description="Директория для images/links YAML")

    # Уровень логирования
    log_level: str = "INFO"
    log_file: Optional[str] = Field(None, description="Путь к файлу логов JSON (None = только консоль)")

    @field_validator("input_file", mode="before")
    @classmethod
    def _coerce_to_str(cls, v):
        """Hydra parses numeric CLI values as int; coerce to str."""
        if v is not None:
            return str(v)
        return v

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"log_level must be one of {valid}, got '{v}'")
        return v.upper()

    class Config:
        extra = "allow"
