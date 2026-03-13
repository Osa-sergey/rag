"""DI container for Voice Expense Bot — mirrors raptor_pipeline pattern.

Flow: Hydra compose → Pydantic validate → DI container → bot startup
"""
from __future__ import annotations

from dependency_injector import containers, providers

from voice_expense_bot.schemas import VoiceExpenseConfig


def _create_embedding_provider(cfg: VoiceExpenseConfig):
    """Create HuggingFace (BERTA) embedding provider from config."""
    from raptor_pipeline.embeddings.providers import HuggingFaceEmbeddingProvider
    return HuggingFaceEmbeddingProvider(cfg.embeddings)


def _create_transcriber(cfg: VoiceExpenseConfig):
    """Create GigaAM transcriber."""
    from voice_expense_bot.transcriber import Transcriber
    tc = cfg.transcriber
    return Transcriber(
        model_name=tc.model_name,
        use_vad=tc.use_vad,
        vad_threshold=tc.vad_threshold,
        max_short_duration=tc.max_short_duration,
    )


def _create_intent_classifier(cfg: VoiceExpenseConfig, embedder):
    """Create intent classifier with expense/transfer intents."""
    from intent_classifier.classifier import IntentClassifier, IntentDef
    intents = [
        IntentDef(
            name="expense",
            reference_phrases=[
                "потратил деньги", "купил", "заплатил за обед", "стоило",
                "расход", "трата", "оплатил", "цена", "оплата",
                "потратил 500 рублей на еду", "купил продукты в магазине",
                "заплатил за такси", "оплатил подписку",
            ],
        ),
        IntentDef(
            name="transfer",
            reference_phrases=[
                "перевёл деньги", "перевод", "отдал долг", "должен",
                "скинул на карту", "отправил перевод",
                "перевёл Саше 2000 рублей", "скинул другу 500",
                "отдал Маше долг за обед",
            ],
        ),
    ]
    return IntentClassifier(embedder, intents, unknown_threshold=0.35)


def _create_category_classifier(cfg: VoiceExpenseConfig, embedder):
    """Create category classifier from config categories."""
    from intent_classifier.categories import CategoryClassifier, CategoryDef
    cats = [
        CategoryDef(
            name=c.name,
            display_name=c.display_name,
            examples=c.examples,
        )
        for c in cfg.categories.items
    ]
    return CategoryClassifier(embedder, cats)


def _create_extractor(cfg: VoiceExpenseConfig):
    """Create LLM extractor."""
    from voice_expense_bot.extractor import Extractor
    category_names = [c.display_name for c in cfg.categories.items]
    return Extractor(cfg.llm, category_names=category_names)


def _create_storage(cfg: VoiceExpenseConfig):
    """Create PostgreSQL storage."""
    from voice_expense_bot.storage import Storage
    return Storage(cfg.database)


class VoiceExpenseContainer(containers.DeclarativeContainer):
    """DI-контейнер для Voice Expense Bot.

    Usage::

        container = VoiceExpenseContainer(config=validated_cfg)
        transcriber = container.transcriber()
        storage = container.storage()
        await storage.connect()
    """

    config = providers.Dependency(instance_of=VoiceExpenseConfig)

    # ── Embedding Provider (Resource = lazy Singleton) ────────
    embedding_provider = providers.Resource(
        _create_embedding_provider, cfg=config,
    )

    # ── Transcriber (Singleton — heavy model loading) ─────────
    transcriber = providers.Singleton(
        _create_transcriber, cfg=config,
    )

    # ── Classifiers (Singleton — pre-computed embeddings) ─────
    intent_classifier = providers.Singleton(
        _create_intent_classifier, cfg=config, embedder=embedding_provider,
    )
    category_classifier = providers.Singleton(
        _create_category_classifier, cfg=config, embedder=embedding_provider,
    )

    # ── Extractor (Factory — stateless) ───────────────────────
    extractor = providers.Factory(
        _create_extractor, cfg=config,
    )

    # ── Storage (Singleton — connection pool) ─────────────────
    storage = providers.Singleton(
        _create_storage, cfg=config,
    )
