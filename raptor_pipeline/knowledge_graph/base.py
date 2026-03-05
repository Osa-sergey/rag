"""Data models and abstract bases for knowledge graph extraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


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
