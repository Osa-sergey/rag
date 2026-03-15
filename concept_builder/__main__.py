"""CLI entry point for Concept Builder (Click + Hydra + Pydantic).

Usage:
    python -m concept_builder --help
    python -m concept_builder dry-run --base-article 986380
    python -m concept_builder process --base-article 986380 --strategy bfs --max-articles 10
    python -m concept_builder process --article-ids 986380,983714
    python -m concept_builder inspect-concept --concept-id <uuid>
    python -m concept_builder trace-keyword --word docker --article-id 986380
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click

from cli_base import add_common_commands, load_config
from concept_builder.schemas import ConceptBuilderConfig

# Force UTF-8 for Windows console
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

CONFIG_DIR = Path(__file__).parent / "conf"
CONFIG_NAME = "config"


# ══════════════════════════════════════════════════════════════
# Click group
# ══════════════════════════════════════════════════════════════

@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Подробный вывод (DEBUG)")
def cli(verbose: bool) -> None:
    """Concept Builder — кросс-статейное объединение ключевых слов в понятия."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-7s  %(name)s: %(message)s",
    )


# ── validate / show-config ────────────────────────────────────
add_common_commands(cli, CONFIG_DIR, CONFIG_NAME, ConceptBuilderConfig)


# ══════════════════════════════════════════════════════════════
# dry-run
# ══════════════════════════════════════════════════════════════

@cli.command("dry-run")
@click.option("--base-article", "-b", default=None, help="Базовая статья для BFS/DFS")
@click.option("--strategy", type=click.Choice(["bfs", "dfs"]), default=None, help="Стратегия обхода")
@click.option("--max-articles", type=int, default=None, help="Максимум статей")
@click.option("--article-ids", "-a", default=None, help="Явный список article_id через запятую")
@click.option("--no-check-connectivity", is_flag=True, help="Пропустить проверку связности")
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def dry_run(base_article, strategy, max_articles, article_ids, no_check_connectivity, override):
    """Предпросмотр: показать что попадёт в обработку без LLM-вызовов.

    \\b
    Примеры:
      python -m concept_builder dry-run -b 986380
      python -m concept_builder dry-run -b 986380 --strategy dfs --max-articles 5
      python -m concept_builder dry-run -a 986380,983714
    """
    cfg = load_config(CONFIG_DIR, CONFIG_NAME, ConceptBuilderConfig, overrides=override)

    from concept_builder.containers import ConceptBuilderContainer
    container = ConceptBuilderContainer(config=cfg)

    selector = container.article_selector()
    processor = container.processor()

    # Select articles
    selected = _select_articles(
        selector, cfg, base_article, strategy, max_articles,
        article_ids, not no_check_connectivity,
    )

    if not selected:
        click.echo("Нет статей для обработки")
        return

    # Run dry-run
    report = processor.dry_run(selected)

    # Print report
    click.echo(f"\n{'═' * 60}")
    click.echo(f"  DRY RUN — {len(report.articles)} статей")
    click.echo(f"{'═' * 60}\n")

    for aid in report.articles:
        name = report.article_names.get(aid, aid)
        kw_count = report.keywords_per_article.get(aid, 0)
        total_kw = report.raw_keywords_per_article.get(aid, 0)

        if aid in report.unprocessed_articles:
            click.echo(f"  ⚠️  {aid} ({name}) — НЕ ОБРАБОТАНА (нет keywords)")
            continue

        click.echo(
            f"  📄 {aid} ({name}) — {kw_count}/{total_kw} keywords "
            f"(≥{cfg.min_keyword_confidence} / total)"
        )
        # Show confidence distribution for this article
        dist = report.confidence_distributions.get(aid, {})
        if dist:
            click.echo(
                f"     confidence: ≥0.8: {dist.get('high', 0)}, "
                f"0.5-0.8: {dist.get('med', 0)}, "
                f"<0.5: {dist.get('low', 0)}, "
                f"NULL: {dist.get('null', 0)}"
            )
        # Show sample confidence values if all are below threshold
        sample_confs = report.sample_confidences.get(aid, [])
        if kw_count == 0 and sample_confs:
            click.echo(f"     ⚠️  sample confidence values: {sample_confs[:10]}")

    if report.unprocessed_articles:
        click.echo(
            f"\n  ⚠️  {len(report.unprocessed_articles)} из {len(report.articles)} "
            f"статей не обработаны (нет keywords). "
            f"Сначала запустите raptor_pipeline для них."
        )

    click.echo(f"\n  Связи между статьями ({len(report.references)}):") 
    if report.references:
        for src, tgt in report.references:
            click.echo(f"    {src} → {tgt}")
    else:
        click.echo("    ⚠️  Нет REFERENCES рёбер между выбранными статьями")
        click.echo("    Проверьте: python -m raptor_pipeline inspect-graph --list-articles")

    cached = report.total_keywords - report.total_needing_description
    click.echo(f"\n  Всего keywords (≥{cfg.min_keyword_confidence}): {report.total_keywords}")
    click.echo(f"  Описания: {cached} cached, {report.total_needing_description} требуют LLM")
    click.echo(f"  Оценка LLM-вызовов: ~{report.estimated_llm_calls}")
    click.echo()

    container.graph_store().close()


# ══════════════════════════════════════════════════════════════
# process
# ══════════════════════════════════════════════════════════════

@cli.command("process")
@click.option("--base-article", "-b", default=None, help="Базовая статья для BFS/DFS")
@click.option("--strategy", type=click.Choice(["bfs", "dfs"]), default=None, help="Стратегия обхода")
@click.option("--max-articles", type=int, default=None, help="Максимум статей")
@click.option("--article-ids", "-a", default=None, help="Явный список article_id через запятую")
@click.option("--no-check-connectivity", is_flag=True, help="Пропустить проверку связности")
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def process(base_article, strategy, max_articles, article_ids, no_check_connectivity, override):
    """Запуск полного пайплайна кросс-статейного объединения.

    \\b
    Примеры:
      python -m concept_builder process -b 986380 --max-articles 5
      python -m concept_builder process -a 986380,983714
    """
    cfg = load_config(CONFIG_DIR, CONFIG_NAME, ConceptBuilderConfig, overrides=override)

    from concept_builder.containers import ConceptBuilderContainer
    container = ConceptBuilderContainer(config=cfg)

    selector = container.article_selector()
    processor = container.processor()

    # Ensure Qdrant collections exist
    _ensure_concept_collections(container, cfg)

    # Select articles
    selected = _select_articles(
        selector, cfg, base_article, strategy, max_articles,
        article_ids, not no_check_connectivity,
    )

    if not selected:
        click.echo("Нет статей для обработки")
        return

    click.echo(f"\n🚀 Processing {len(selected)} articles...")
    result = processor.process(selected)

    click.echo(f"\n{'═' * 60}")
    click.echo(f"  РЕЗУЛЬТАТ")
    click.echo(f"{'═' * 60}")
    click.echo(f"  Concepts: {result['concepts_created']}")
    click.echo(f"  Relations: {result['relations_created']}")

    for c in result.get("concepts", []):
        click.echo(f"\n  💡 {c['name']} (domain: {c.get('domain', '?')})")
        click.echo(f"     id: {c['id']}")
        click.echo(f"     keywords: {', '.join(c['keywords'])}")
        click.echo(f"     articles: {', '.join(c['articles'])}")

    click.echo()
    container.graph_store().close()


# ══════════════════════════════════════════════════════════════
# list-concepts
# ══════════════════════════════════════════════════════════════

@cli.command("list-concepts")
@click.option("--domain", "-d", default=None, help="Фильтр по домену")
@click.option("--article-id", "-a", default=None, help="Фильтр по article_id (concepts содержащие статью)")
@click.option("--override", "-o", multiple=True, help="Hydra override")
def list_concepts(domain, article_id, override):
    """Показать все Concept-ноды с их ID.

    \\b
    Примеры:
      python -m concept_builder list-concepts
      python -m concept_builder list-concepts --domain devops
      python -m concept_builder list-concepts --article-id 986380
    """
    cfg = load_config(CONFIG_DIR, CONFIG_NAME, ConceptBuilderConfig, overrides=override)

    from concept_builder.containers import ConceptBuilderContainer
    container = ConceptBuilderContainer(config=cfg)

    from neo4j import GraphDatabase
    n_cfg = cfg.stores.neo4j
    driver = GraphDatabase.driver(n_cfg.uri, auth=(n_cfg.user, n_cfg.password))

    with driver.session(database=n_cfg.database) as session:
        # Build query with optional filters
        where_parts = []
        params = {}
        if domain:
            where_parts.append("c.domain = $domain")
            params["domain"] = domain
        if article_id:
            where_parts.append("$article_id IN c.source_articles")
            params["article_id"] = article_id

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        result = session.run(
            f"""
            MATCH (c:Concept)
            {where_clause}
            OPTIONAL MATCH (c)-[r:CROSS_RELATED_TO]-()
            RETURN c.id AS id, c.canonical_name AS name, c.domain AS domain,
                   c.description AS description,
                   c.source_articles AS source_articles,
                   c.keyword_words AS keyword_words,
                   count(DISTINCT r) AS relations_count
            ORDER BY c.domain, c.canonical_name
            """,
            **params,
        ).data()

    driver.close()

    if not result:
        click.echo("Нет Concept-нод в Neo4j.")
        if domain:
            click.echo(f"  (фильтр domain='{domain}')")
        if article_id:
            click.echo(f"  (фильтр article_id='{article_id}')")
        return

    click.echo(f"\n{'═' * 70}")
    click.echo(f"  Concepts ({len(result)})")
    click.echo(f"{'═' * 70}\n")

    for c in result:
        name = c.get("name", "?")
        domain_val = c.get("domain", "?")
        cid = c.get("id", "?")
        keywords = c.get("keyword_words") or []
        articles = c.get("source_articles") or []
        rels = c.get("relations_count", 0)
        desc = c.get("description", "")

        click.echo(f"  💡 {name} ({domain_val})")
        click.echo(f"     id: {cid}")
        click.echo(f"     keywords: {', '.join(keywords) if keywords else '—'}")
        click.echo(f"     articles: {', '.join(articles) if articles else '—'}")
        if rels:
            click.echo(f"     cross-relations: {rels}")
        if desc:
            short_desc = desc[:100] + "..." if len(desc) > 100 else desc
            click.echo(f"     description: {short_desc}")
        click.echo()

    click.echo(f"{'═' * 70}")
    click.echo(f"  Всего: {len(result)} concepts")

    # Show unique domains
    domains = sorted({c.get("domain", "?") for c in result})
    click.echo(f"  Домены: {', '.join(domains)}")
    click.echo()

    container.graph_store().close()


# ══════════════════════════════════════════════════════════════
# inspect-concept
# ══════════════════════════════════════════════════════════════

@cli.command("inspect-concept")
@click.option("--concept-id", "-c", required=True, help="UUID Concept-ноды")
@click.option("--override", "-o", multiple=True, help="Hydra override")
def inspect_concept(concept_id, override):
    """Инспекция Concept с трейсингом до чанков.

    \\b
    Примеры:
      python -m concept_builder inspect-concept -c <uuid>
    """
    cfg = load_config(CONFIG_DIR, CONFIG_NAME, ConceptBuilderConfig, overrides=override)

    from concept_builder.containers import ConceptBuilderContainer
    container = ConceptBuilderContainer(config=cfg)
    inspector = container.inspector()

    result = inspector.inspect_concept(concept_id)

    if "error" in result:
        click.echo(f"❌ {result['error']}")
        return

    click.echo(f"\n{'═' * 60}")
    click.echo(f"  Concept: {result['canonical_name']} ({result['domain']})")
    click.echo(f"{'═' * 60}")
    click.echo(f"  ID: {result['concept_id']}")
    click.echo(f"  Description: {result['description']}")
    click.echo(f"  Articles: {result['source_articles']}")
    click.echo(f"  Keywords: {result['keywords']}")

    click.echo(f"\n  Keyword traces:")
    for trace in result.get("keyword_traces", []):
        click.echo(f"\n    🔑 {trace['word']} (article: {trace['article_id']})")
        for chunk in trace.get("chunks", []):
            click.echo(f"       L{chunk['level']} [{chunk['chunk_id']}]: {chunk['text']}")

    click.echo(f"\n  Cross-relations ({len(result.get('cross_relations', []))}):")
    for rel in result.get("cross_relations", []):
        click.echo(
            f"    ↔ {rel.get('other_name')} ({rel.get('other_domain')}) "
            f"— {rel.get('predicate')} ({rel.get('confidence', 0):.2f})"
        )

    click.echo()
    container.graph_store().close()


# ══════════════════════════════════════════════════════════════
# trace-keyword
# ══════════════════════════════════════════════════════════════

@cli.command("trace-keyword")
@click.option("--word", "-w", required=True, help="Ключевое слово")
@click.option("--article-id", "-a", required=True, help="ID статьи")
@click.option("--override", "-o", multiple=True, help="Hydra override")
def trace_keyword(word, article_id, override):
    """Отследить keyword до исходных чанков.

    \\b
    Примеры:
      python -m concept_builder trace-keyword -w docker -a 986380
    """
    cfg = load_config(CONFIG_DIR, CONFIG_NAME, ConceptBuilderConfig, overrides=override)

    from concept_builder.containers import ConceptBuilderContainer
    container = ConceptBuilderContainer(config=cfg)
    inspector = container.inspector()

    chunks = inspector.trace_keyword_to_chunks(word, article_id)

    if not chunks:
        click.echo(f"❌ Keyword '{word}' не найден в статье '{article_id}'")
        return

    click.echo(f"\n  🔑 '{word}' в статье '{article_id}' — {len(chunks)} чанков:\n")
    for chunk in chunks:
        click.echo(f"  Level {chunk['level']} [{chunk['chunk_id']}]:")
        click.echo(f"    {chunk['text']}")
        click.echo()

    container.graph_store().close()


# ══════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════

def _select_articles(selector, cfg, base_article, strategy, max_articles,
                     article_ids_str, check_connectivity):
    """Common article selection logic for dry-run and process."""
    if article_ids_str:
        ids = [x.strip() for x in article_ids_str.split(",") if x.strip()]
        return selector.select_explicit(ids, check_connectivity=check_connectivity)
    elif base_article:
        return selector.select_by_traversal(
            base_article,
            strategy=strategy or cfg.default_strategy,
            max_articles=max_articles or cfg.default_max_articles,
        )
    else:
        raise click.UsageError(
            "Укажите --base-article (-b) или --article-ids (-a)"
        )


def _ensure_concept_collections(container, cfg):
    """Create Qdrant collections for concepts and cross-relations if needed."""
    from qdrant_client.models import VectorParams, Distance

    client = container.vector_store()._client
    vector_size = cfg.stores.qdrant.vector_size

    for coll_name in [
        cfg.stores.qdrant.concepts_collection,
        cfg.stores.qdrant.cross_relations_collection,
    ]:
        collections = {c.name for c in client.get_collections().collections}
        if coll_name not in collections:
            client.create_collection(
                collection_name=coll_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )
            click.echo(f"  ✓ Created Qdrant collection '{coll_name}' (dim={vector_size})")


if __name__ == "__main__":
    cli()
