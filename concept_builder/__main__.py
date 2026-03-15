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
@click.option("--article-id", "-a", default=None, help="Фильтр по article_id")
@click.option("--show-relations", "-r", is_flag=True, help="Только concepts со связями + показать связи")
@click.option("--full", "-f", is_flag=True, help="Полный текст описаний (без обрезки)")
@click.option("--override", "-o", multiple=True, help="Hydra override")
def list_concepts(domain, article_id, show_relations, full, override):
    """Показать все Concept-ноды с их ID.

    \\b
    Примеры:
      python -m concept_builder list-concepts
      python -m concept_builder list-concepts -d devops -r -f
      python -m concept_builder list-concepts -a 986380 --full
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
            OPTIONAL MATCH (c)-[r:CROSS_RELATED_TO]-(other:Concept)
            RETURN c.id AS id, c.canonical_name AS name, c.domain AS domain,
                   c.description AS description,
                   c.source_articles AS source_articles,
                   c.keyword_words AS keyword_words,
                   c.version AS version,
                   c.is_active AS is_active,
                   count(DISTINCT r) AS relations_count,
                   collect(DISTINCT {{name: other.canonical_name, predicate: r.predicate, desc: r.description}}) AS relations
            ORDER BY c.domain, c.canonical_name, c.version
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

    if show_relations:
        result = [c for c in result if c.get("relations_count", 0) > 0]
        if not result:
            click.echo("Нет Concepts со связями.")
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
        version = c.get("version") or 1
        is_active = c.get("is_active", True)
        active_badge = "✓ active" if is_active else "inactive"

        click.echo(f"  💡 {name} ({domain_val}) v{version} [{active_badge}]")
        click.echo(f"     id: {cid}")
        click.echo(f"     keywords: {', '.join(keywords) if keywords else '—'}")
        click.echo(f"     articles: {', '.join(articles) if articles else '—'}")
        if rels:
            click.echo(f"     cross-relations: {rels}")
            if show_relations:
                relations = c.get("relations") or []
                for rel in relations:
                    if rel.get("name"):
                        pred = rel.get("predicate", "")
                        rname = rel.get("name", "?")
                        rdesc = rel.get("desc", "")
                        line = f"       → {rname}"
                        if pred:
                            line += f" ({pred})"
                        if rdesc:
                            if not full:
                                rdesc = rdesc[:80] + "..." if len(rdesc) > 80 else rdesc
                            line += f": {rdesc}"
                        click.echo(line)
        if desc:
            if not full:
                desc = desc[:120] + "..." if len(desc) > 120 else desc
            click.echo(f"     description: {desc}")
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


# ══════════════════════════════════════════════════════════════
# expand
# ══════════════════════════════════════════════════════════════

@cli.command("expand")
@click.option("--concept-ids", "-c", required=True, help="UUID Concept-нод через запятую")
@click.option("--article-ids", "-a", required=True, help="Article IDs через запятую")
@click.option("--high-threshold", default=0.85, type=float, help="Порог прямого включения (default: 0.85)")
@click.option("--low-threshold", default=0.65, type=float, help="Порог LLM-верификации (default: 0.65)")
@click.option("--override", "-o", multiple=True, help="Hydra override")
def expand_cmd(concept_ids, article_ids, high_threshold, low_threshold, override):
    """Расширить существующие Concepts keywords из новых статей.

    \\b
    Примеры:
      python -m concept_builder expand -c uuid1,uuid2 -a 986380,985200
      python -m concept_builder expand -c uuid1 -a 986380 --high-threshold 0.80
    """
    cfg = load_config(CONFIG_DIR, CONFIG_NAME, ConceptBuilderConfig, overrides=override)

    from concept_builder.containers import ConceptBuilderContainer
    container = ConceptBuilderContainer(config=cfg)
    _ensure_concept_collections(container, cfg)
    processor = container.processor()

    c_ids = [x.strip() for x in concept_ids.split(",") if x.strip()]
    a_ids = [x.strip() for x in article_ids.split(",") if x.strip()]

    results = processor.expand(
        c_ids, a_ids,
        high_threshold=high_threshold,
        low_threshold=low_threshold,
    )

    if not results:
        click.echo("\n  Нет совпадений между keywords и Concepts.")
        container.graph_store().close()
        return

    # ── Phase 5: Show results and get user choice ─────────
    click.echo(f"\n{'═' * 70}")
    click.echo(f"  EXPAND — выбор версий")
    click.echo(f"{'═' * 70}")

    for r in results:
        click.echo(f"\n{'═' * 70}")
        click.echo(f"  Concept: {r.concept_name} ({r.domain})")
        click.echo(f"{'═' * 70}")

        # v1 — original
        click.echo(f"\n  v{r.original_version} (текущая):")
        click.echo(f"    keywords: {', '.join(r.original.keyword_words)}")
        click.echo(f"    articles: {', '.join(r.original.source_articles)}")
        click.echo(f"    description: {r.original.description}")

        available = [r.original_version]

        # v(N+1) — direct
        if r.v_direct:
            click.echo(f"\n  v{r.v_direct.version} (+ прямые включения):")
            for word, sim in r.direct_keywords:
                click.echo(f"    + {word} (sim={sim:.2f})")
            click.echo(f"    keywords: {', '.join(r.v_direct.keyword_words)}")
            click.echo(f"    articles: {', '.join(r.v_direct.source_articles)}")
            click.echo(f"    description: {r.v_direct.description}")
            available.append(r.v_direct.version)

        # v(N+2) — direct + LLM
        if r.v_llm:
            click.echo(f"\n  v{r.v_llm.version} (+ прямые + LLM-верифицированные):")
            for word, conf, rel in r.llm_keywords:
                click.echo(f"    + {word} (LLM confidence={conf:.2f}, \"{rel}\")")
            click.echo(f"    keywords: {', '.join(r.v_llm.keyword_words)}")
            click.echo(f"    articles: {', '.join(r.v_llm.source_articles)}")
            click.echo(f"    description: {r.v_llm.description}")
            available.append(r.v_llm.version)

        choices = "/".join(str(v) for v in available)
        while True:
            choice = click.prompt(
                f"\n  Выберите версию [{choices}]",
                type=int,
                default=available[-1],
            )
            if choice in available:
                r.chosen_version = choice
                break
            click.echo(f"  ❌ Допустимые: {choices}")

    # ── Finalize ──────────────────────────────────────────
    click.echo(f"\n{'═' * 70}")
    click.echo("  Сохранение выбранных версий...")

    summary = processor.finalize_expand(results)

    click.echo(f"\n  ✓ Concepts обновлено: {summary['concepts_updated']}")
    click.echo(f"  ✓ Новых concepts: {summary['new_concepts']}")
    click.echo(f"  ✓ Cross-relations: {summary['relations']}")
    click.echo(f"  ✓ Версий сохранено: {summary['versions_stored']}")
    click.echo()

    container.graph_store().close()


# ══════════════════════════════════════════════════════════════
# expand-dry-run
# ══════════════════════════════════════════════════════════════

@cli.command("expand-dry-run")
@click.option("--concept-ids", "-c", required=True, help="UUID Concept-нод через запятую")
@click.option("--article-ids", "-a", required=True, help="Article IDs через запятую")
@click.option("--high-threshold", default=0.85, type=float, help="Порог прямого включения")
@click.option("--low-threshold", default=0.65, type=float, help="Порог LLM-верификации")
@click.option("--override", "-o", multiple=True, help="Hydra override")
def expand_dry_run(concept_ids, article_ids, high_threshold, low_threshold, override):
    """Preview expand без LLM-вызовов — только cosine matching.

    \\b
    Примеры:
      python -m concept_builder expand-dry-run -c uuid1,uuid2 -a 986380
    """
    cfg = load_config(CONFIG_DIR, CONFIG_NAME, ConceptBuilderConfig, overrides=override)

    from concept_builder.containers import ConceptBuilderContainer
    container = ConceptBuilderContainer(config=cfg)
    processor = container.processor()

    c_ids = [x.strip() for x in concept_ids.split(",") if x.strip()]
    a_ids = [x.strip() for x in article_ids.split(",") if x.strip()]

    # Load concepts
    concepts = processor._load_existing_concepts(c_ids)
    if not concepts:
        click.echo("❌ Concepts не найдены")
        return

    # Load keywords
    all_kws = []
    for aid in a_ids:
        kws = processor._load_article_keywords(aid)
        filtered = [k for k in kws if k.confidence >= cfg.min_keyword_confidence]
        all_kws.extend(filtered)

    if not all_kws:
        click.echo("❌ Нет keywords в указанных статьях")
        return

    # Need descriptions + embeddings for matching
    need_desc = sum(1 for k in all_kws if not k.description)
    need_emb = len(all_kws)  # all need embeddings for matching
    concepts_no_emb = sum(1 for c in concepts if c.embedding is None)

    click.echo(f"\n{'═' * 70}")
    click.echo(f"  EXPAND DRY RUN — {len(concepts)} concepts × {len(a_ids)} articles")
    click.echo(f"{'═' * 70}\n")

    click.echo(f"  Существующие Concepts:")
    for c in concepts:
        emb_status = "✓" if c.embedding else "⚠️ нет embedding"
        click.echo(f"    💡 {c.canonical_name} ({c.domain}) v{c.version} [{emb_status}]")
        click.echo(f"       id: {c.id}")
        click.echo(f"       keywords: {', '.join(c.keyword_words)}")
        click.echo(f"       articles: {', '.join(c.source_articles)}")

    click.echo(f"\n  Keywords из статей:")
    for aid in a_ids:
        kws_for_aid = [k for k in all_kws if k.article_id == aid]
        no_desc = sum(1 for k in kws_for_aid if not k.description)
        click.echo(f"    📄 {aid} — {len(kws_for_aid)} keywords, {no_desc} без описания")

    click.echo(f"\n  Итого:")
    click.echo(f"    Keywords: {len(all_kws)} (из них {need_desc} без описания)")
    click.echo(f"    Concepts без embedding: {concepts_no_emb}")
    click.echo(f"\n  Пороги:")
    click.echo(f"    high_threshold (прямое): {high_threshold}")
    click.echo(f"    low_threshold (LLM): {low_threshold}")
    click.echo(f"\n  Оценка LLM-вызовов:")
    # descriptions + verification + regeneration
    est_verify = len(all_kws) // 3  # rough estimate of LLM candidates
    est_regen = len(concepts)
    est_total = need_desc + est_verify + est_regen
    click.echo(f"    Описания keywords: ~{need_desc}")
    click.echo(f"    Верификация: ~{est_verify}")
    click.echo(f"    Перегенерация concepts: ~{est_regen}")
    click.echo(f"    Итого: ~{est_total}")
    click.echo()

    container.graph_store().close()


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
