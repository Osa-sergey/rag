"""CLI entry point for Topic Modeler (Click + Hydra + Pydantic + DI wiring).

Architecture:
  Click handler (thin)  → parse CLI args, load config, init container
  Business function     → @inject receives ready objects via Provide[]

Usage:
    python -m topic_modeler --help
    python -m topic_modeler train --device cuda --min-cluster-size 3
    python -m topic_modeler add-article parsed_yaml/957000.yaml
    python -m topic_modeler validate
    python -m topic_modeler show-config
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
from dependency_injector.wiring import Provide, inject

from cli_base import add_common_commands, load_config
from cli_base.logging import setup_logging
from topic_modeler.schemas import TopicModelerConfig

CONFIG_DIR = Path(__file__).parent / "conf"
CONFIG_NAME = "config"

# Container instance — initialized once per CLI invocation
_container = None


def _init_container(cfg: TopicModelerConfig):
    """Create, wire, and return the DI container."""
    global _container
    from topic_modeler.containers import TopicModelerContainer
    _container = TopicModelerContainer(config=cfg)
    _container.wire(modules=[__name__])
    return _container


# ══════════════════════════════════════════════════════════════
# Business logic — @inject + Provide[]
# Эти функции НЕ знают про Click, конфиги, CLI-аргументы.
# Они получают готовые объекты через DI wiring.
# ══════════════════════════════════════════════════════════════

@inject
def _do_train(
    input_dir: Path,
    csv_paths: list[Path],
    modeler=Provide["topic_modeler"],
) -> dict:
    """Обучить модель — получает TopicModeler через DI."""
    try:
        return modeler.train(input_dir=input_dir, csv_paths=csv_paths)
    finally:
        modeler.close()


@inject
def _do_add_article(
    article_path: Path,
    csv_paths: list[Path] | None,
    modeler=Provide["topic_modeler"],
) -> dict:
    """Предсказать топик — получает TopicModeler через DI."""
    try:
        return modeler.add_article(article_path, csv_paths)
    finally:
        modeler.close()


# ══════════════════════════════════════════════════════════════
# Click handlers (thin) — parse CLI → config → container → call
# ══════════════════════════════════════════════════════════════

@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Подробный вывод (DEBUG)")
def cli(verbose: bool) -> None:
    """Topic Modeler -- BERTopic для Habr-статей.

    Тематическое моделирование статей: обучение, предсказание топиков,
    обогащение графа знаний Neo4j.
    """
    cli.verbose = verbose


@cli.command()
@click.option("--input-dir", default=None,
              help="Директория с YAML-статьями  [yaml: input_dir]")
@click.option("--model-dir", default=None,
              help="Куда сохранить модель  [yaml: model_dir]")
@click.option("--device", type=click.Choice(["cpu", "cuda", "mps"]), default=None,
              help="Устройство для эмбеддингов  [yaml: embeddings.model_kwargs.device]")
@click.option("--min-cluster-size", type=int, default=None,
              help="HDBSCAN: мин. размер кластера  [yaml: hdbscan.min_cluster_size]")
@click.option("--nr-topics", type=int, default=None,
              help="Число топиков (null=авто)  [yaml: bertopic.nr_topics]")
@click.option("--override", "-o", multiple=True,
              help="Hydra override (key=value), можно несколько")
def train(input_dir, model_dir, device, min_cluster_size, nr_topics, override):
    """Обучить BERTopic на всех статьях.

    \b
    Примеры:
      python -m topic_modeler train
      python -m topic_modeler train --device cuda --min-cluster-size 3
      python -m topic_modeler train -o "umap.n_neighbors=10"
    """
    # 1. Собрать overrides из Click-опций
    click_overrides = {}
    if input_dir is not None:
        click_overrides["input_dir"] = input_dir
    if model_dir is not None:
        click_overrides["model_dir"] = model_dir
    if device is not None:
        click_overrides["embeddings.model_kwargs.device"] = device
    if min_cluster_size is not None:
        click_overrides["hdbscan.min_cluster_size"] = min_cluster_size
    if nr_topics is not None:
        click_overrides["bertopic.nr_topics"] = nr_topics

    # 2. Load + validate config
    cfg = load_config(CONFIG_DIR, CONFIG_NAME, TopicModelerConfig,
                      overrides=override, **click_overrides)
    level = "DEBUG" if getattr(cli, "verbose", False) else cfg.log_level
    setup_logging(level=level, log_file=cfg.log_file)

    # 3. Init container + wire
    _init_container(cfg)

    # 4. Call business logic (TopicModeler injected via Provide[])
    result = _do_train(
        input_dir=Path(cfg.input_dir),
        csv_paths=[Path(p) for p in cfg.csv_paths],
    )
    click.echo(f"\nОбучение завершено: {result}")


@cli.command("add-article")
@click.argument("article_path", type=click.Path())
@click.option("--model-dir", default=None,
              help="Директория с сохранённой моделью  [yaml: model_dir]")
@click.option("--override", "-o", multiple=True,
              help="Hydra override (key=value)")
def add_article(article_path, model_dir, override):
    """Предсказать топик для новой статьи.

    \b
    Примеры:
      python -m topic_modeler add-article parsed_yaml/957000.yaml
      python -m topic_modeler add-article myfile.yaml --model-dir models/v2
    """
    # 1. Overrides
    click_overrides = {}
    if model_dir is not None:
        click_overrides["model_dir"] = model_dir

    # 2. Config
    cfg = load_config(CONFIG_DIR, CONFIG_NAME, TopicModelerConfig,
                      overrides=override, **click_overrides)
    level = "DEBUG" if getattr(cli, "verbose", False) else cfg.log_level
    setup_logging(level=level, log_file=cfg.log_file)

    # 3. Container
    _init_container(cfg)

    # 4. Call (TopicModeler injected)
    csv_paths = [Path(p) for p in cfg.csv_paths] if cfg.csv_paths else None
    result = _do_add_article(
        article_path=Path(article_path),
        csv_paths=csv_paths,
    )
    click.echo(f"\nРезультат: {result}")


# ── Common commands ───────────────────────────────────────────

add_common_commands(cli, CONFIG_DIR, CONFIG_NAME, TopicModelerConfig)


if __name__ == "__main__":
    cli()
