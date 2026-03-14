"""Abstract base classes (contracts) for all swappable components.

All ABCs live here so that any module can import them without
circular dependencies on concrete implementations.

Concrete implementations can be swapped via ``_class_`` field in YAML config,
validated at runtime by ``cli_base.class_resolver.resolve_class()``.
"""
from interfaces.base import (
    BaseArticleSelector,
    BaseChunker,
    BaseConceptClusterer,
    BaseConceptInspector,
    BaseDailyNoteEditor,
    BaseEmbeddingProvider,
    BaseGraphStore,
    BaseKeywordDescriber,
    BaseKeywordExtractor,
    BaseKeywordRefiner,
    BaseNoteEditor,
    BaseRelationExtractor,
    BaseSummarizer,
    BaseVaultParser,
    BaseVectorStore,
    BaseWellnessEditor,
)

__all__ = [
    "BaseArticleSelector",
    "BaseChunker",
    "BaseConceptClusterer",
    "BaseConceptInspector",
    "BaseDailyNoteEditor",
    "BaseEmbeddingProvider",
    "BaseGraphStore",
    "BaseKeywordDescriber",
    "BaseKeywordExtractor",
    "BaseKeywordRefiner",
    "BaseNoteEditor",
    "BaseRelationExtractor",
    "BaseSummarizer",
    "BaseVaultParser",
    "BaseVectorStore",
    "BaseWellnessEditor",
]

