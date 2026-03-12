"""CLI entry point for RAPTOR Pipeline (Click + Hydra + Pydantic + DI wiring).

Architecture:
  Click handler (thin)  → parse CLI args, load config, init container
  Business function     → @inject receives ready objects via Provide[]

Usage:
    python -m raptor_pipeline --help
    python -m raptor_pipeline run
    python -m raptor_pipeline run --input-file 957000.yaml
    python -m raptor_pipeline validate
    python -m raptor_pipeline show-config
"""
from __future__ import annotations

import logging
import json
import sys
from pathlib import Path

import click
from dependency_injector.wiring import Provide, inject

from cli_base import add_common_commands, load_config
from raptor_pipeline.schemas import RaptorPipelineConfig

# Force UTF-8 for Windows console
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

CONFIG_DIR = Path(__file__).parent / "conf"
CONFIG_NAME = "config"

_container = None


def _init_container(cfg: RaptorPipelineConfig):
    """Create, wire, and return the DI container."""
    global _container
    from raptor_pipeline.containers import RaptorPipelineContainer
    _container = RaptorPipelineContainer(config=cfg)
    _container.wire(modules=[__name__])
    return _container


# ══════════════════════════════════════════════════════════════
# Business logic — @inject + Provide[]
# ══════════════════════════════════════════════════════════════

@inject
def _do_run(cfg: RaptorPipelineConfig, pipeline=Provide["pipeline"]):
    """Запуск пайплайна — получает RaptorPipeline через DI."""
    pipeline.init_stores()

    input_dir = Path(cfg.input_dir)

    if cfg.input_file:
        path = input_dir / cfg.input_file
        result = pipeline.process_file(path)
        click.echo(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        results = pipeline.process_directory(input_dir)
        click.echo(f"Обработано файлов: {len(results)}")
        for r in results:
            click.echo(f"  {r}")

    pipeline.close()


# ══════════════════════════════════════════════════════════════
# Click handlers (thin)
# ══════════════════════════════════════════════════════════════

@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Подробный вывод (DEBUG)")
def cli(verbose: bool) -> None:
    """RAPTOR Pipeline — индексация документов в графовое + векторное хранилище."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-7s  %(name)s: %(message)s",
    )


# ── validate / show-config (из cli_base) ──────────────────────
add_common_commands(cli, CONFIG_DIR, CONFIG_NAME, RaptorPipelineConfig)


# ── run ───────────────────────────────────────────────────────

@cli.command()
@click.option("--input-dir", default=None, help="Директория с YAML-файлами")
@click.option("--input-file", default=None, help="Один файл из input_dir")
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def run(input_dir, input_file, override):
    """Запустить RAPTOR пайплайн (полный или один файл).

    \\b
    Примеры:
      python -m raptor_pipeline run
      python -m raptor_pipeline run --input-file 957000.yaml
      python -m raptor_pipeline run --input-dir my_yamls/
      python -m raptor_pipeline run -o "chunker.type=semantic"
    """
    overrides = {}
    if input_dir:
        overrides["input_dir"] = input_dir
    if input_file:
        overrides["input_file"] = input_file

    cfg = load_config(CONFIG_DIR, CONFIG_NAME, RaptorPipelineConfig,
                      overrides=override, **overrides)
    _init_container(cfg)
    _do_run(cfg)


if __name__ == "__main__":
    cli()
