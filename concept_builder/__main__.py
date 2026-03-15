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

    # ── Similarity analysis ──────────────────────────────────
    import numpy as np
    all_kws = []
    for aid in selected:
        kws = processor._load_article_keywords(aid)
        filtered = [k for k in kws if k.confidence >= cfg.min_keyword_confidence]
        all_kws.extend(filtered)

    # Fallback descriptions
    for kc in all_kws:
        if not kc.description:
            kc.description = f"{kc.word} ({kc.category})"

    # Dedup by word
    dedup: dict[str, object] = {}
    for kc in all_kws:
        key = kc.word.lower()
        if key not in dedup:
            dedup[key] = kc
    kws_dedup = list(dedup.values())

    if len(kws_dedup) >= 2:
        click.echo(f"\n  Вычисление embeddings для {len(kws_dedup)} keywords...")
        embedder = container.embedding_provider()
        descriptions = [kc.description for kc in kws_dedup]
        embeddings = embedder.embed_texts(descriptions)
        for kc, emb in zip(kws_dedup, embeddings):
            kc.embedding = emb
        vectors = np.array(embeddings, dtype=np.float32)

        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        vectors_norm = vectors / norms

        sim_matrix = vectors_norm @ vectors_norm.T
        n = len(kws_dedup)
        upper_sims = []
        for i in range(n):
            for j in range(i + 1, n):
                upper_sims.append((sim_matrix[i, j], kws_dedup[i].word, kws_dedup[j].word))
        sims = np.array([s[0] for s in upper_sims])

        click.echo(f"\n{'═' * 70}")
        click.echo(f"  Анализ similarity — {len(kws_dedup)} keywords, {len(sims)} пар")
        click.echo(f"{'═' * 70}")

        click.echo(f"\n  📊 Распределение cosine similarity:")
        percentiles = [5, 10, 25, 50, 75, 90, 95, 99]
        click.echo(f"    {'Перцентиль':<15} {'Значение':<10}")
        click.echo(f"    {'─' * 25}")
        for p in percentiles:
            val = np.percentile(sims, p)
            click.echo(f"    P{p:<14} {val:.4f}")
        click.echo(f"    {'─' * 25}")
        click.echo(f"    {'min':<15} {sims.min():.4f}")
        click.echo(f"    {'max':<15} {sims.max():.4f}")
        click.echo(f"    {'mean':<15} {sims.mean():.4f}")
        click.echo(f"    {'std':<15} {sims.std():.4f}")

        from concept_builder.concept_clusterer import GreedyConceptClusterer
        greedy = GreedyConceptClusterer()

        click.echo(f"\n  📋 Порог → количество кластеров (greedy):")
        click.echo(f"    {'Threshold':<12} {'Кластеры':<12} {'Avg size':<12} {'Max size':<12} {'Singletons':<12}")
        click.echo(f"    {'─' * 60}")
        current_t = cfg.similarity_threshold
        thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
        for t in thresholds:
            clusters = greedy.cluster(kws_dedup, similarity_threshold=t)
            sizes = [len(c) for c in clusters]
            singletons = sum(1 for s in sizes if s == 1)
            avg_size = sum(sizes) / len(sizes) if sizes else 0
            max_size = max(sizes) if sizes else 0
            marker = " ◀" if abs(t - current_t) < 0.01 else ""
            click.echo(f"    {t:<12.2f} {len(clusters):<12} {avg_size:<12.1f} {max_size:<12} {singletons:<12}{marker}")

        click.echo(f"\n  🔗 Топ-10 наиболее похожих пар:")
        sorted_sims = sorted(upper_sims, key=lambda x: x[0], reverse=True)[:10]
        for sim_val, w1, w2 in sorted_sims:
            click.echo(f"    {sim_val:.4f}  {w1} ↔ {w2}")

        near_threshold = sorted(
            upper_sims, key=lambda x: abs(x[0] - current_t),
        )[:10]
        click.echo(f"\n  🎯 Пары вблизи порога ({current_t:.2f}):")
        for sim_val, w1, w2 in sorted(near_threshold, key=lambda x: x[0], reverse=True):
            marker = "✓" if sim_val >= current_t else "✗"
            click.echo(f"    {marker} {sim_val:.4f}  {w1} ↔ {w2}")

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
                   c.run_id AS run_id,
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
        run = c.get("run_id", "")
        if run:
            click.echo(f"     run: {run}")
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
        desc = rel.get("description", "")
        if desc:
            click.echo(f"      {desc}")

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
# list-runs
# ══════════════════════════════════════════════════════════════

@cli.command("list-runs")
@click.option("--override", "-o", multiple=True, help="Hydra override")
def list_runs(override):
    """Показать историю запусков concept_builder.

    \\b
    Примеры:
      python -m concept_builder list-runs
    """
    cfg = load_config(CONFIG_DIR, CONFIG_NAME, ConceptBuilderConfig, overrides=override)

    from neo4j import GraphDatabase
    n_cfg = cfg.stores.neo4j
    driver = GraphDatabase.driver(n_cfg.uri, auth=(n_cfg.user, n_cfg.password))

    with driver.session(database=n_cfg.database) as session:
        result = session.run(
            """
            MATCH (c:Concept)
            WHERE c.run_id IS NOT NULL AND c.run_id <> ''
            RETURN c.run_id AS run_id,
                   count(c) AS concepts,
                   collect(DISTINCT c.domain) AS domains,
                   min(c.created_at) AS created_at
            ORDER BY run_id DESC
            """,
        ).data()

    driver.close()

    if not result:
        click.echo("Нет запусков с run_id.")
        return

    click.echo(f"\n{'═' * 70}")
    click.echo(f"  Запуски concept_builder ({len(result)})")
    click.echo(f"{'═' * 70}\n")

    click.echo(f"  {'Run ID':<20} {'Concepts':<12} {'Domains':<30} {'Created':<25}")
    click.echo(f"  {'─' * 85}")

    for r in result:
        run_id = r.get("run_id", "?")
        count = r.get("concepts", 0)
        domains = ", ".join(r.get("domains") or [])
        created = r.get("created_at", "?")
        click.echo(f"  {run_id:<20} {count:<12} {domains:<30} {created:<25}")

    click.echo()


# ══════════════════════════════════════════════════════════════
# delete-concepts
# ══════════════════════════════════════════════════════════════

@cli.command("delete-concepts")
@click.option("--run-id", "-r", default=None, help="Удалить все concepts по run_id")
@click.option("--concept-ids", "-c", default=None, help="UUID Concept-нод через запятую")
@click.option("--yes", "-y", is_flag=True, help="Без подтверждения")
@click.option("--override", "-o", multiple=True, help="Hydra override")
def delete_concepts(run_id, concept_ids, yes, override):
    """Удалить Concept-ноды и связанные рёбра.

    Без флагов — удаляет все concepts (с подтверждением).

    \\b
    Примеры:
      python -m concept_builder delete-concepts
      python -m concept_builder delete-concepts --run-id 20260315_141445
      python -m concept_builder delete-concepts --concept-ids uuid1,uuid2 -y
    """
    cfg = load_config(CONFIG_DIR, CONFIG_NAME, ConceptBuilderConfig, overrides=override)

    from neo4j import GraphDatabase
    n_cfg = cfg.stores.neo4j
    driver = GraphDatabase.driver(n_cfg.uri, auth=(n_cfg.user, n_cfg.password))

    # Build filter
    if run_id:
        match_clause = "MATCH (c:Concept {run_id: $filter_val})"
        filter_val = run_id
        filter_desc = f"run_id={run_id}"
    elif concept_ids:
        ids = [x.strip() for x in concept_ids.split(",") if x.strip()]
        match_clause = "MATCH (c:Concept) WHERE c.id IN $filter_val"
        filter_val = ids
        filter_desc = f"{len(ids)} concept IDs"
    else:
        match_clause = "MATCH (c:Concept)"
        filter_val = None
        filter_desc = "ВСЕ concepts"

    params = {"filter_val": filter_val} if filter_val is not None else {}

    # Preview
    with driver.session(database=n_cfg.database) as session:
        preview = session.run(
            f"""
            {match_clause}
            RETURN c.id AS id, c.canonical_name AS name, c.domain AS domain,
                   c.version AS version, c.run_id AS run_id
            """,
            **params,
        ).data()

    if not preview:
        click.echo(f"❌ Нет concepts для {filter_desc}")
        driver.close()
        return

    click.echo(f"\n  Concepts для удаления ({len(preview)}):")
    for p in preview:
        click.echo(f"    💡 {p.get('name', '?')} ({p.get('domain', '?')}) v{p.get('version', 1)} [run={p.get('run_id', '')}]")
        click.echo(f"       id: {p.get('id', '?')}")

    if not yes:
        click.confirm(f"\n  Удалить {len(preview)} concepts и их рёбра?", abort=True)

    # Delete edges + nodes
    with driver.session(database=n_cfg.database) as session:
        result = session.run(
            f"""
            {match_clause}
            DETACH DELETE c
            RETURN count(*) AS deleted
            """,
            **params,
        ).single()

    deleted = result["deleted"] if result else 0

    # Clean Qdrant
    try:
        from concept_builder.containers import ConceptBuilderContainer
        container = ConceptBuilderContainer(config=cfg)
        client = container.vector_store()._client
        concepts_coll = cfg.stores.qdrant.concepts_collection

        concept_ids_list = [p["id"] for p in preview]
        from qdrant_client.models import Filter, FieldCondition, MatchAny
        client.delete(
            collection_name=concepts_coll,
            points_selector=Filter(must=[
                FieldCondition(key="concept_id", match=MatchAny(any=concept_ids_list)),
            ]),
        )
        click.echo(f"  ✓ Qdrant embeddings удалены")
    except Exception as exc:
        click.echo(f"  ⚠️  Qdrant cleanup failed: {exc}")

    driver.close()
    click.echo(f"  ✓ Удалено {deleted} concepts (filter: {filter_desc})")
    click.echo()


# ══════════════════════════════════════════════════════════════
# add-concept
# ══════════════════════════════════════════════════════════════

@cli.command("add-concept")
@click.option("--name", "-n", required=True, help="Canonical name for the concept")
@click.option("--description", "-d", required=True, help="Description of the concept")
@click.option("--domain", default="general", help="Knowledge domain (e.g. devops, ml)")
@click.option("--article-ids", "-a", default=None,
              help="Comma-separated article IDs to search for matching keywords")
@click.option("--high-threshold", type=float, default=0.75,
              help="Cosine ≥ this → direct keyword match (default 0.75)")
@click.option("--low-threshold", type=float, default=0.55,
              help="Cosine ≥ this → candidate for review (default 0.55)")
@click.option("--override", "-o", multiple=True, help="Hydra override")
def add_concept(name, description, domain, article_ids, high_threshold, low_threshold, override):
    """Manually create a concept and find matching keywords in articles.

    Uses the same approach as 'expand': loads keywords from articles,
    computes embeddings, then matches against the concept description
    by cosine similarity.

    \\b
    Examples:
      python -m concept_builder add-concept -n "Docker" -d "Платформа контейнеризации" -a 986380
      python -m concept_builder add-concept -n "CI/CD" -d "Continuous Integration" --domain devops
    """
    import numpy as np
    from datetime import datetime
    from tqdm import tqdm
    from concept_builder.models import ConceptNode

    cfg = load_config(CONFIG_DIR, CONFIG_NAME, ConceptBuilderConfig, overrides=override)

    from concept_builder.containers import ConceptBuilderContainer
    container = ConceptBuilderContainer(config=cfg)

    processor = container.processor()
    gs = container.graph_store()

    # Embed the concept description
    click.echo(f"\n{'═' * 70}")
    click.echo(f"  Adding concept: {name} ({domain})")
    click.echo(f"{'═' * 70}")
    click.echo(f"  Description: {description}")
    click.echo(f"  Thresholds: high={high_threshold}, low={low_threshold}")

    desc_embedding = processor._embedder.embed_texts([description])[0]
    concept_vec = np.array(desc_embedding, dtype=np.float32)

    # ── Phase 1: Load keywords from articles ──
    articles = []
    if article_ids:
        articles = [a.strip() for a in article_ids.split(",") if a.strip()]

    all_keywords = []
    min_conf = getattr(cfg, "min_keyword_confidence", 0.8)

    if articles:
        click.echo(f"\n  Loading keywords from {len(articles)} articles...")
        for aid in tqdm(articles, desc="Loading keywords", unit="article"):
            kws = processor._load_article_keywords(aid)
            filtered = [k for k in kws if k.confidence >= min_conf]
            all_keywords.extend(filtered)
            click.echo(f"    Article '{aid}': {len(filtered)} keywords (≥{min_conf})")
    else:
        click.echo("\n  ⚠️  No articles specified. Use -a to specify article IDs.")
        gs.close()
        return

    if not all_keywords:
        click.echo("  ⚠️  No keywords found in specified articles.")
        gs.close()
        return

    # ── Phase 2: Generate descriptions + embeddings for keywords ──
    need_desc = [kc for kc in all_keywords if not kc.description]
    cached = len(all_keywords) - len(need_desc)
    click.echo(f"\n  Keywords: {len(all_keywords)} total, {cached} cached, {len(need_desc)} need descriptions")

    if need_desc and processor._describer:
        click.echo(f"  Generating {len(need_desc)} descriptions...")
        for kc in tqdm(need_desc, desc="Descriptions", unit="kw"):
            kc.description = processor._describer.describe(
                kc.word, kc.article_id, kc.chunk_ids,
            )
            if not kc.description:
                kc.description = f"{kc.word} ({kc.category})"
        processor._save_keyword_descriptions(need_desc)

    click.echo(f"  Computing keyword embeddings...")
    descriptions = [kc.description for kc in all_keywords]
    embeddings = processor._embedder.embed_texts(descriptions)
    for kc, emb in zip(all_keywords, embeddings):
        kc.embedding = emb

    # ── Phase 3: Match keywords → concept by cosine similarity ──
    click.echo(f"\n  Matching {len(all_keywords)} keywords against concept...")

    direct_matches: list[tuple] = []  # (kc, similarity)
    candidates: list[tuple] = []
    unmatched: list[tuple] = []

    for kc in all_keywords:
        if kc.embedding is None:
            continue
        kw_vec = np.array(kc.embedding, dtype=np.float32)
        sim = float(np.dot(concept_vec, kw_vec) / (
            np.linalg.norm(concept_vec) * np.linalg.norm(kw_vec) + 1e-8
        ))
        if sim >= high_threshold:
            direct_matches.append((kc, sim))
        elif sim >= low_threshold:
            candidates.append((kc, sim))
        else:
            unmatched.append((kc, sim))

    # Sort by similarity
    direct_matches.sort(key=lambda x: x[1], reverse=True)
    candidates.sort(key=lambda x: x[1], reverse=True)

    # ── Display results ──
    click.echo(f"\n{'─' * 70}")
    click.echo(f"  ✅ Direct matches ({len(direct_matches)}, cosine ≥ {high_threshold}):")
    click.echo(f"{'─' * 70}")
    for kc, sim in direct_matches:
        click.echo(f"    [{sim:.3f}] {kc.word} ({kc.category}) art={kc.article_id}")
        if kc.description:
            desc = kc.description[:100].replace("\n", " ")
            click.echo(f"      {desc}")

    click.echo(f"\n{'─' * 70}")
    click.echo(f"  🔍 Candidates ({len(candidates)}, {low_threshold} ≤ cosine < {high_threshold}):")
    click.echo(f"{'─' * 70}")
    for kc, sim in candidates[:20]:
        click.echo(f"    [{sim:.3f}] {kc.word} ({kc.category}) art={kc.article_id}")

    click.echo(f"\n  Unmatched: {len(unmatched)} keywords (cosine < {low_threshold})")

    # Collect matched keywords
    matched_keywords = sorted({kc.word for kc, _ in direct_matches})
    matched_articles = sorted({kc.article_id for kc, _ in direct_matches})

    if not matched_keywords:
        click.echo("\n  ⚠️  No keywords matched above high threshold. Concept not created.")
        click.echo("  Try lowering --high-threshold or check articles.")
        gs.close()
        return

    # ── Phase 4: Regenerate description based on matched keywords ──
    matched_kws = [kc for kc, _ in direct_matches]
    click.echo(f"\n  📝 Regenerating description based on {len(matched_kws)} keywords...")

    # Create a temporary concept with user's base description
    tmp_concept = ConceptNode(
        canonical_name=name,
        domain=domain,
        description=description,
    )
    enriched_description = processor._regenerate_concept_description(
        tmp_concept, matched_kws,
    )
    click.echo(f"\n  Original:  {description}")
    click.echo(f"  Enriched:  {enriched_description[:300]}")

    # Re-embed the enriched description
    desc_embedding = processor._embedder.embed_texts([enriched_description])[0]

    # ── Phase 5: Create and store concept ──
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_manual"
    concept = ConceptNode(
        canonical_name=name,
        domain=domain,
        description=enriched_description,
        source_articles=matched_articles if matched_articles else articles,
        keyword_words=matched_keywords,
        run_id=run_id,
        is_manual=True,
        embedding=desc_embedding,
    )

    # Store in Neo4j
    with gs._driver.session(database=gs._database) as session:
        session.run(
            """
            MERGE (concept:Concept {id: $id})
            ON CREATE SET concept.created_at = $created_at
            SET concept.canonical_name = $name,
                concept.concept_group_id = $group_id,
                concept.domain = $domain,
                concept.description = $description,
                concept.source_articles = $articles,
                concept.keyword_words = $keyword_words,
                concept.version = 1,
                concept.is_active = true,
                concept.is_manual = true,
                concept.run_id = $run_id,
                concept.updated_at = $updated_at
            """,
            id=concept.id,
            group_id=concept.concept_group_id,
            name=concept.canonical_name,
            domain=concept.domain,
            description=concept.description,
            articles=concept.source_articles,
            keyword_words=concept.keyword_words,
            run_id=concept.run_id,
            created_at=concept.created_at,
            updated_at=datetime.utcnow().isoformat(),
        )

        # Create INSTANCE_OF edges
        for kw in matched_keywords:
            session.run(
                """
                MATCH (k:Keyword {word: $word})
                MATCH (c:Concept {id: $concept_id})
                MERGE (k)-[:INSTANCE_OF]->(c)
                """,
                word=kw,
                concept_id=concept.id,
            )

    click.echo(f"\n  ✅ Concept stored in Neo4j: {concept.id}")

    # Store embedding in Qdrant
    try:
        from qdrant_client.models import PointStruct
        concepts_collection = cfg.stores.qdrant.get("concepts_collection", "concepts")
        processor._vs._client.upsert(
            collection_name=concepts_collection,
            points=[PointStruct(
                id=hash(concept.id) % (2**63),
                vector=desc_embedding,
                payload={
                    "concept_id": concept.id,
                    "canonical_name": concept.canonical_name,
                    "domain": concept.domain,
                    "description": concept.description,
                    "source_articles": concept.source_articles,
                    "keyword_words": concept.keyword_words,
                    "is_manual": True,
                },
            )],
        )
        click.echo(f"  ✅ Embedding stored in Qdrant ({concepts_collection})")
    except Exception as exc:
        click.echo(f"  ⚠️  Qdrant storage failed: {exc}")

    click.echo(f"\n{'═' * 70}")
    click.echo(f"  Summary:")
    click.echo(f"    Name: {concept.canonical_name}")
    click.echo(f"    Domain: {concept.domain}")
    click.echo(f"    ID: {concept.id}")
    click.echo(f"    Run: {concept.run_id}")
    click.echo(f"    is_manual: True")
    click.echo(f"    Direct keywords ({len(matched_keywords)}): {', '.join(matched_keywords[:15])}")
    click.echo(f"    Candidate keywords: {len(candidates)} (not included, review manually)")
    click.echo(f"    Articles: {', '.join(concept.source_articles)}")
    click.echo()

    gs.close()


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
