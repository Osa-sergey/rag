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

import json
import logging
import sys
from pathlib import Path

import click
from dependency_injector.wiring import Provide, inject

from cli_base import add_common_commands, load_config
from cli_base.logging import setup_logging
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
    # Logging will be fully configured after config is loaded (in each command).
    # Here we just store the verbose flag for later use.
    cli.verbose = verbose


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
    level = "DEBUG" if getattr(cli, "verbose", False) else cfg.log_level
    setup_logging(level=level, log_file=cfg.log_file)
    _init_container(cfg)
    _do_run(cfg)


# ── inspect-tree ──────────────────────────────────────────────

def _list_articles_qdrant(cfg: RaptorPipelineConfig) -> None:
    """Show all article_ids available in Qdrant."""
    from qdrant_client import QdrantClient

    client = QdrantClient(host=cfg.stores.qdrant.host, port=cfg.stores.qdrant.port)
    collection = cfg.stores.qdrant.collection_name

    points, _ = client.scroll(
        collection_name=collection,
        with_payload=["article_id"],
        with_vectors=False,
        limit=10_000,
    )
    article_ids: dict[str, int] = {}
    for p in points:
        aid = p.payload.get("article_id", "?")
        article_ids[aid] = article_ids.get(aid, 0) + 1

    if not article_ids:
        click.echo("Нет данных в Qdrant.")
        return

    click.echo(f"\nСтатьи в Qdrant (коллекция '{collection}'):")
    click.echo("=" * 50)
    for aid in sorted(article_ids):
        click.echo(f"  {aid}  ({article_ids[aid]} nodes)")
    click.echo("=" * 50)
    click.echo(f"Всего: {len(article_ids)} статей, {sum(article_ids.values())} nodes")


def _list_articles_neo4j(cfg: RaptorPipelineConfig) -> None:
    """Show all articles available in Neo4j."""
    from neo4j import GraphDatabase

    n_cfg = cfg.stores.neo4j
    driver = GraphDatabase.driver(n_cfg.uri, auth=(n_cfg.user, n_cfg.password))

    with driver.session(database=n_cfg.database) as session:
        result = session.run(
            "MATCH (a:Article) "
            "OPTIONAL MATCH (a)-[r:HAS_KEYWORD]->(k:Keyword) "
            "RETURN a.id AS id, a.article_name AS name, "
            "       a.summary IS NOT NULL AS has_summary, "
            "       count(DISTINCT k) AS kw_count "
            "ORDER BY a.id"
        )
        articles = list(result)

    driver.close()

    if not articles:
        click.echo("Нет статей в Neo4j.")
        return

    click.echo(f"\nСтатьи в Neo4j:")
    click.echo("=" * 60)
    for art in articles:
        name = art.get("name") or ""
        name_str = f"  ({name})" if name else ""
        summary_flag = " 📋" if art.get("has_summary") else ""
        kw_count = art.get("kw_count", 0)
        click.echo(f"  {art['id']}{name_str}  — {kw_count} keywords{summary_flag}")
    click.echo("=" * 60)
    click.echo(f"Всего: {len(articles)} статей")


@cli.command("inspect-tree")
@click.option("--article-id", default=None, help="Фильтр по article_id")
@click.option("--full-text", is_flag=True, help="Показать полный текст нод")
@click.option("--list-articles", is_flag=True, help="Показать список статей в хранилищах")
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def inspect_tree(article_id, full_text, list_articles, override):
    """Визуализация RAPTOR-дерева из Qdrant.

    \\b
    Примеры:
      python -m raptor_pipeline inspect-tree
      python -m raptor_pipeline inspect-tree --article-id 986380
      python -m raptor_pipeline inspect-tree --full-text
      python -m raptor_pipeline inspect-tree --list-articles
    """
    overrides = {}
    if article_id is not None:
        overrides["article_id"] = str(article_id)
    if full_text:
        overrides["full_text"] = "true"

    cfg = load_config(CONFIG_DIR, CONFIG_NAME, RaptorPipelineConfig,
                      overrides=override, **overrides)

    if list_articles:
        _list_articles_qdrant(cfg)
        return

    # Delegate to existing inspect_tree logic
    from raptor_pipeline.inspect_tree import main as _inspect_tree_main
    from omegaconf import OmegaConf, DictConfig as OmegaDictConfig

    # Convert pydantic config back to OmegaConf DictConfig for inspect_tree
    raw = cfg.model_dump(by_alias=True)
    omegacfg = OmegaConf.create(raw)
    _inspect_tree_main(omegacfg)


# ── inspect-graph ─────────────────────────────────────────────

@cli.command("inspect-graph")
@click.option("--word", "-w", default=None, help="Ключевое слово для инспекции")
@click.option("--article-id", "-a", default=None, help="Фильтр по article_id (показать keywords статьи с confidence)")
@click.option("--min-confidence", "-c", type=float, default=None, help="Показать только keywords с confidence ≥ значения")
@click.option("--list-articles", is_flag=True, help="Показать список статей в хранилищах")
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def inspect_graph(word, article_id, min_confidence, list_articles, override):
    """Просмотр Knowledge Graph (Neo4j) с текстами из Qdrant.

    \\b
    Примеры:
      python -m raptor_pipeline inspect-graph
      python -m raptor_pipeline inspect-graph --word оптимизация
      python -m raptor_pipeline inspect-graph --article-id 986380
      python -m raptor_pipeline inspect-graph --article-id 986380 --min-confidence 0.8
      python -m raptor_pipeline inspect-graph --list-articles
    """
    overrides = {}
    if word is not None:
        overrides["word"] = word

    cfg = load_config(CONFIG_DIR, CONFIG_NAME, RaptorPipelineConfig,
                      overrides=override, **overrides)

    if list_articles:
        _list_articles_neo4j(cfg)
        return

    # Delegate to existing inspect_graph logic
    from raptor_pipeline.inspect_graph import main as _inspect_graph_main
    from omegaconf import OmegaConf

    raw = cfg.model_dump(by_alias=True)
    omegacfg = OmegaConf.create(raw)
    _inspect_graph_main(
        omegacfg,
        article_id=str(article_id) if article_id else None,
        min_confidence=min_confidence,
    )


if __name__ == "__main__":
    cli()

