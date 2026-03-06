"""Data models and abstract bases for knowledge graph extraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from pydantic import BaseModel, Field


class KeywordSO(BaseModel):
    """Structured output for a single keyword."""
    word: str = Field(description="Текст ключевого слова или фразы")
    category: str = Field(description="Категория (technology, method, concept, tool, framework, person, organisation, metric, other)")
    confidence: float = Field(default=1.0, description="Уверенность извлечения (0-1)")

class KeywordListSO(BaseModel):
    """List of keywords."""
    keywords: List[KeywordSO]


class RelationSO(BaseModel):
    """Structured output for a single relation triple."""
    subject: str = Field(description="Субъект (сущность из списка ключевых слов)")
    predicate: str = Field(description="Тип связи (глагол или описание отношения)")
    object: str = Field(description="Объект (сущность из списка ключевых слов)")
    confidence: float = Field(default=1.0, description="Уверенность извлечения (0-1)")

class RelationListSO(BaseModel):
    """List of relations."""
    relations: List[RelationSO]


class RefinedKeywordSO(BaseModel):
    """Structured output for a refined keyword."""
    refined_word: str = Field(description="Правильный, нормализованный термин")
    category: str = Field(description="Уточненная категория")
    original_words: List[str] = Field(description="Список исходных слов, которые были объединены")

class RefinedKeywordListSO(BaseModel):
    """List of refined keywords."""
    items: List[RefinedKeywordSO]


@dataclass
class Keyword:
    """Extracted keyword or key-phrase.

    Attributes:
        word:       The keyword text.
        category:   Optional category (e.g. "technology", "concept").
        confidence: Extraction confidence 0–1.
        chunk_id:   ID of the source chunk.
    """

    word: str
    category: str = ""
    confidence: float = 1.0
    chunk_id: str = ""


@dataclass
class Relation:
    """Extracted subject-predicate-object triple.

    Attributes:
        subject:    Subject entity / keyword.
        predicate:  Relationship type (verb / label).
        object:     Object entity / keyword.
        confidence: Extraction confidence 0–1.
        chunk_id:   ID of the source chunk.
    """

    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    chunk_id: str = ""


class BaseKeywordExtractor(ABC):
    @abstractmethod
    def extract(self, text: str, chunk_id: str = "") -> list[Keyword]:
        ...


class BaseRelationExtractor(ABC):
    @abstractmethod
    def extract(
        self,
        text: str,
        keywords: list[Keyword],
        chunk_id: str = "",
    ) -> list[Relation]:
        """Extract relations, using *keywords* as context hints."""
        ...
