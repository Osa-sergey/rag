"""Abstract base classes and data models for chunking.

BaseChunker ABC re-exported from ``interfaces`` (canonical location).
Chunk dataclass stays here — it is a data model, not an interface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from interfaces import BaseChunker  # noqa: F401  — canonical ABC


@dataclass
class Chunk:
    """Single chunk of text from a document.

    Attributes:
        chunk_id:   Unique ID of the chunk (e.g. "article123_chunk_3").
        article_id: ID of the source article.
        text:       Rendered text content of the chunk.
        block_ids:  List of original block IDs that compose this chunk.
        level:      RAPTOR tree level (0 = leaf).
        metadata:   Extra metadata for storage/filtering.
    """

    chunk_id: str
    article_id: str
    text: str
    block_ids: list[str] = field(default_factory=list)
    level: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
