"""DI container for Voice Bot — mirrors raptor_pipeline pattern.

Flow: Hydra compose → Pydantic validate → DI container → bot startup
"""
from __future__ import annotations

from dependency_injector import containers, providers

from voice_bot.schemas import VoiceBotConfig


def _create_embedding_provider(cfg: VoiceBotConfig):
    """Create HuggingFace (BERTA) embedding provider from config."""
    from raptor_pipeline.embeddings.providers import HuggingFaceEmbeddingProvider
    return HuggingFaceEmbeddingProvider(cfg.embeddings)


def _create_transcriber(cfg: VoiceBotConfig):
    """Create GigaAM transcriber."""
    from voice_bot.transcriber import Transcriber
    tc = cfg.transcriber
    return Transcriber(
        model_name=tc.model_name,
        use_vad=tc.use_vad,
        vad_threshold=tc.vad_threshold,
        max_short_duration=tc.max_short_duration,
    )


def _create_intent_classifier(cfg: VoiceBotConfig, embedder):
    """Create intent classifier, loading intents from conf/intents/default.yaml."""
    from voice_bot.intent_classifier.classifier import IntentClassifier, IntentDef

    intents_cfg = cfg.intents  # dict from Hydra
    intent_list = intents_cfg.get("intents", [])
    threshold = float(intents_cfg.get("unknown_threshold", 0.35))

    if not intent_list:
        raise ValueError(
            "No intents defined in conf/intents/default.yaml. "
            "Add at least one intent with reference_phrases."
        )

    intents = [
        IntentDef(
            name=intent["name"],
            reference_phrases=list(intent["reference_phrases"]),
        )
        for intent in intent_list
    ]
    return IntentClassifier(embedder, intents, unknown_threshold=threshold)


def _create_category_classifier(cfg: VoiceBotConfig, embedder):
    """Create category classifier from config categories."""
    from voice_bot.intent_classifier.categories import CategoryClassifier, CategoryDef
    cats = [
        CategoryDef(
            name=c.name,
            display_name=c.display_name,
            examples=c.examples,
        )
        for c in cfg.categories.items
    ]
    return CategoryClassifier(embedder, cats)


def _create_extractor(cfg: VoiceBotConfig):
    """Create LLM extractor (legacy — used for old storage)."""
    from voice_bot.extractor import Extractor
    category_names = [c.display_name for c in cfg.categories.items]
    return Extractor(cfg.llm, category_names=category_names)


def _create_storage(cfg: VoiceBotConfig):
    """Create PostgreSQL storage (legacy logging)."""
    from voice_bot.storage import Storage
    return Storage(cfg.database)


# ── Firefly III components ────────────────────────────────────


def _create_firefly_config(cfg: VoiceBotConfig):
    """Parse firefly section into FireflyConfig."""
    from voice_bot.integrations.firefly_iii.schemas import FireflyConfig, AccountSynonymConfig
    firefly_dict = cfg.firefly or {}

    # Parse account_synonyms sub-section
    synonyms_raw = firefly_dict.get("account_synonyms", {})
    if isinstance(synonyms_raw, dict) and "synonyms" in synonyms_raw:
        synonyms_cfg = AccountSynonymConfig(synonyms=synonyms_raw["synonyms"])
    else:
        synonyms_cfg = AccountSynonymConfig(synonyms=synonyms_raw if isinstance(synonyms_raw, dict) else {})

    return FireflyConfig(
        base_url=firefly_dict.get("base_url", "http://localhost:9090"),
        token=firefly_dict.get("token", ""),
        default_source_account=firefly_dict.get("default_source_account", "Сбер расчетный счет"),
        account_synonyms=synonyms_cfg,
    )


def _create_firefly_client(firefly_cfg):
    """Create Firefly III API client."""
    from voice_bot.integrations.firefly_iii.client import FireflyClient
    return FireflyClient(firefly_cfg)


def _create_date_parser():
    """Create date parser."""
    from voice_bot.date_parser import DateParser
    return DateParser()


def _create_account_resolver(firefly_cfg, embedder):
    """Create account resolver with synonyms and embedding support."""
    from voice_bot.integrations.firefly_iii.account_resolver import AccountResolver
    return AccountResolver(
        synonyms=firefly_cfg.account_synonyms.synonyms,
        default_account=firefly_cfg.default_source_account,
        embedder=embedder,
    )


def _create_firefly_extractor(cfg: VoiceBotConfig):
    """Create Firefly-specific LLM extractor."""
    from voice_bot.integrations.firefly_iii.extractor import FireflyExtractor
    category_names = [c.display_name for c in cfg.categories.items]
    return FireflyExtractor(cfg.llm, category_names=category_names)


def _create_intent_registry(
    firefly_client,
    firefly_extractor,
    date_parser,
    account_resolver,
):
    """Create intent registry and register all Firefly III handlers."""
    from voice_bot.intent_classifier.registry import IntentRegistry
    from voice_bot.integrations.firefly_iii.handler import (
        FireflyExpenseHandler,
        FireflyTransferHandler,
        FireflyDepositHandler,
    )

    registry = IntentRegistry()
    registry.register(FireflyExpenseHandler(
        client=firefly_client,
        extractor=firefly_extractor,
        date_parser=date_parser,
        account_resolver=account_resolver,
    ))
    registry.register(FireflyTransferHandler(
        client=firefly_client,
        extractor=firefly_extractor,
        date_parser=date_parser,
        account_resolver=account_resolver,
    ))
    registry.register(FireflyDepositHandler(
        client=firefly_client,
        extractor=firefly_extractor,
        date_parser=date_parser,
        account_resolver=account_resolver,
    ))
    return registry


# ── Obsidian Tasks components ─────────────────────────────────


def _create_obsidian_vault(cfg: VoiceBotConfig):
    """Create Obsidian vault wrapper."""
    from voice_bot.integrations.obsidian_tasks.schemas import ObsidianConfig
    from voice_bot.integrations.obsidian_tasks.vault import ObsidianVault
    obs_dict = cfg.obsidian or {}
    obs_cfg = ObsidianConfig(
        vault_path=obs_dict.get("vault_path", ""),
        tasks_folder=obs_dict.get("tasks_folder", "Tasks"),
        daily_notes_folder=obs_dict.get("daily_notes_folder", "Daily"),
        default_date=obs_dict.get("default_date", "today"),
    )
    return ObsidianVault(obs_cfg)


def _create_task_extractor(cfg: VoiceBotConfig):
    """Create LLM task extractor."""
    from voice_bot.integrations.obsidian_tasks.extractor import TaskExtractor
    return TaskExtractor(cfg.llm)


class VoiceBotContainer(containers.DeclarativeContainer):
    """DI-контейнер для Voice Bot.

    Usage::

        container = VoiceBotContainer(config=validated_cfg)
        transcriber = container.transcriber()
        storage = container.storage()
        await storage.connect()
    """

    config = providers.Dependency(instance_of=VoiceBotConfig)

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

    # ── Extractor (Factory — stateless, legacy) ───────────────
    extractor = providers.Factory(
        _create_extractor, cfg=config,
    )

    # ── Storage (Singleton — connection pool, legacy) ─────────
    storage = providers.Singleton(
        _create_storage, cfg=config,
    )

    # ── Firefly III ───────────────────────────────────────────
    firefly_config = providers.Singleton(
        _create_firefly_config, cfg=config,
    )

    firefly_client = providers.Singleton(
        _create_firefly_client, firefly_cfg=firefly_config,
    )

    date_parser = providers.Singleton(_create_date_parser)

    account_resolver = providers.Singleton(
        _create_account_resolver,
        firefly_cfg=firefly_config,
        embedder=embedding_provider,
    )

    firefly_extractor = providers.Factory(
        _create_firefly_extractor, cfg=config,
    )

    intent_registry = providers.Singleton(
        _create_intent_registry,
        firefly_client=firefly_client,
        firefly_extractor=firefly_extractor,
        date_parser=date_parser,
        account_resolver=account_resolver,
    )

    # ── Obsidian Tasks ────────────────────────────────────────
    obsidian_vault = providers.Singleton(
        _create_obsidian_vault, cfg=config,
    )

    task_extractor = providers.Factory(
        _create_task_extractor, cfg=config,
    )
