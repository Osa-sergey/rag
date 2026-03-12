"""Common CLI commands shared across all modules: validate, show-config."""
from __future__ import annotations

from pathlib import Path
from typing import Type

import click
from pydantic import BaseModel

from cli_base.config_loader import load_config, load_raw_config


def add_common_commands(
    group: click.Group,
    config_dir: str | Path,
    config_name: str,
    schema_class: Type[BaseModel],
) -> None:
    """Register ``validate`` and ``show-config`` commands on a Click group.

    Args:
        group: The Click group to add commands to.
        config_dir: Path to Hydra config directory.
        config_name: Root config file name (without .yaml).
        schema_class: Pydantic model for validation.
    """

    @group.command("validate")
    @click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
    def validate_cmd(override: tuple[str, ...]) -> None:
        """Проверить конфигурацию без запуска.

        Загружает YAML, применяет overrides, валидирует через pydantic
        и выводит результат или ошибки.
        """
        cfg = load_config(config_dir, config_name, schema_class, overrides=override)
        click.echo("  Конфигурация валидна!\n")
        click.echo(cfg.model_dump_json(indent=2))

    @group.command("show-config")
    @click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
    def show_config_cmd(override: tuple[str, ...]) -> None:
        """Показать текущий YAML-конфиг (без валидации)."""
        yaml_str = load_raw_config(config_dir, config_name, overrides=override)
        click.echo(yaml_str)
