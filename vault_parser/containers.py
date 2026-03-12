"""DI container for Vault Parser — with wiring + config-driven class replacement.

Flow:
  Click CLI → Hydra compose → pydantic validate → DI container → services

Features:
  - Config-driven class replacement via parser_class / editor_class
  - Base class validation (issubclass check vs BaseVaultParser / BaseNoteEditor)
  - Wiring: @inject + Provide[] on Click commands
"""
from __future__ import annotations

from pathlib import Path

from dependency_injector import containers, providers

from cli_base.class_resolver import resolve_class
from vault_parser.schemas import VaultParserConfig


def _create_parser(cfg: VaultParserConfig):
    """Resolve parser class from config and instantiate."""
    from interfaces import BaseVaultParser
    cls = resolve_class(cfg.parser_class, BaseVaultParser)
    v = cfg.vault
    return cls(
        v.path,
        daily_subdir=v.daily_dir,
        weekly_subdir=v.weekly_dir,
        monthly_subdir=v.monthly_dir,
        people_dir=v.people_dir,
    )


def _create_editor(cfg: VaultParserConfig):
    """Resolve editor class from config and instantiate."""
    from interfaces import BaseDailyNoteEditor
    cls = resolve_class(cfg.editor_class, BaseDailyNoteEditor)
    daily_dir = Path(cfg.vault.path) / cfg.vault.daily_dir
    return cls(daily_dir)


class VaultParserContainer(containers.DeclarativeContainer):
    """DI-контейнер для Vault Parser.

    Принимает провалидированный VaultParserConfig (pydantic).
    Классы parser и editor резолвятся из parser_class / editor_class в конфиге.

    Usage:
        container = VaultParserContainer(config=validated_cfg)
        container.wire(modules=[vault_parser.__main__])
        parser = container.parser()
    """

    config = providers.Dependency(instance_of=VaultParserConfig)

    # ── VaultParser (Factory, class from config) ──────────────
    # parser_class: vault_parser.parser.VaultParser
    # Validated: issubclass(cls, BaseVaultParser)
    parser = providers.Factory(
        _create_parser,
        cfg=config,
    )

    # ── DailyNoteEditor (Factory, class from config) ──────────
    # editor_class: vault_parser.writer.editor.DailyNoteEditor
    # Validated: issubclass(cls, BaseNoteEditor)
    editor = providers.Factory(
        _create_editor,
        cfg=config,
    )
