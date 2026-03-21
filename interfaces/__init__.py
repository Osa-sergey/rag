"""Public API for all abstract base classes.

Import via::

    from interfaces import BaseGraphStore, BaseChunker, ...

Internal layout — one file per domain::

    interfaces/
        embeddings.py       — BaseEmbeddingProvider
        stores.py           — BaseGraphStore, BaseVectorStore
        chunker.py          — BaseChunker
        summarizer.py       — BaseSummarizer
        knowledge_graph.py  — BaseKeywordExtractor, BaseKeywordRefiner, BaseRelationExtractor
        vault_parser.py     — BaseVaultParser, BaseNoteEditor, BaseDailyNoteEditor, BaseWellnessEditor
        concept_builder.py  — BaseArticleSelector, BaseKeywordDescriber, BaseConceptClusterer, BaseConceptInspector
"""

# ── Embeddings / Stores ──────────────────────────────────────
from interfaces.embeddings import BaseEmbeddingProvider
from interfaces.stores import BaseGraphStore, BaseVectorStore

# ── RAPTOR pipeline ──────────────────────────────────────────
from interfaces.chunker import BaseChunker
from interfaces.summarizer import BaseSummarizer
from interfaces.knowledge_graph import (
    BaseKeywordExtractor,
    BaseKeywordRefiner,
    BaseRelationExtractor,
)

# ── Vault parser ─────────────────────────────────────────────
from interfaces.vault_parser import (
    BaseVaultParser,
    BaseNoteEditor,
    BaseDailyNoteEditor,
    BaseWellnessEditor,
)

# ── Concept builder ──────────────────────────────────────────
from interfaces.concept_builder import (
    BaseArticleSelector,
    BaseKeywordDescriber,
    BaseConceptClusterer,
    BaseConceptInspector,
)

__all__ = [
    # Embeddings / Stores
    "BaseEmbeddingProvider",
    "BaseGraphStore",
    "BaseVectorStore",
    # RAPTOR pipeline
    "BaseChunker",
    "BaseSummarizer",
    "BaseKeywordExtractor",
    "BaseKeywordRefiner",
    "BaseRelationExtractor",
    # Vault parser
    "BaseVaultParser",
    "BaseNoteEditor",
    "BaseDailyNoteEditor",
    "BaseWellnessEditor",
    # Concept builder
    "BaseArticleSelector",
    "BaseKeywordDescriber",
    "BaseConceptClusterer",
    "BaseConceptInspector",
]
