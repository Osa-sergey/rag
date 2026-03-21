"""CLI entry point for Retrieval module.

Usage:
    python -m retrieval search "Как работает RAG?"
    python -m retrieval search "BM25 vs BERT" --no-rephrase --top-k 5
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
from omegaconf import OmegaConf

from cli_base.logging import setup_logging

# ── Config ────────────────────────────────────────────────────
CONFIG_DIR = str(Path(__file__).parent / "conf")
CONFIG_NAME = "config"


def load_config(overrides: tuple[str, ...] = ()) -> dict:
    """Load Hydra-style config from YAML."""
    cfg_path = Path(CONFIG_DIR) / f"{CONFIG_NAME}.yaml"
    cfg = OmegaConf.load(cfg_path)
    if overrides:
        override_cfg = OmegaConf.from_dotlist(list(overrides))
        cfg = OmegaConf.merge(cfg, override_cfg)
    return cfg


def _format_scores(scores_by_query: dict[str, float], q_labels: dict[str, str]) -> str:
    """Format per-query scores as a compact string."""
    parts = []
    for q_text, score in scores_by_query.items():
        label = q_labels.get(q_text, q_text[:30])
        parts.append(f"{label}: {score:.3f}")
    return " | ".join(parts)


# ── Click CLI ─────────────────────────────────────────────────
@click.group()
@click.option("-v", "--verbose", is_flag=True, help="DEBUG logging")
def cli(verbose: bool) -> None:
    """Retrieval — multi-source RAG retrieval for quality analysis."""
    cli.verbose = verbose


# ══════════════════════════════════════════════════════════════
# search
# ══════════════════════════════════════════════════════════════

@cli.command("search")
@click.argument("query")
@click.option("--top-k", "-k", type=int, default=None, help="Top-K results per source")
@click.option("--no-rephrase", is_flag=True, help="Skip LLM query rephrasing")
@click.option("--level", "-l", type=int, default=None, help="Filter RAPTOR level")
@click.option("--override", "-o", multiple=True, help="Config override (key=value)")
def search(query, top_k, no_rephrase, level, override):
    """Search across all sources for a given query.

    \\b
    Examples:
      python -m retrieval search "Как работает RAG?"
      python -m retrieval search "BM25 vs BERT" --no-rephrase --top-k 5
      python -m retrieval search "vector search" -l 0
    """
    cfg = load_config(override)
    level = "DEBUG" if getattr(cli, "verbose", False) else cfg.get("log_level", "INFO")
    setup_logging(level=level, log_file=cfg.get("log_file"))
    top_k = top_k or cfg.get("top_k", 10)

    # Build dependencies
    from raptor_pipeline.embeddings.providers import create_embedding_provider
    embedder = create_embedding_provider(cfg.embeddings)

    from cli_base.class_resolver import resolve_class
    from interfaces import BaseGraphStore
    gs_cls = resolve_class(
        cfg.stores.neo4j.get("_class_", "stores.graph_store.Neo4jGraphStore"),
        BaseGraphStore,
    )
    gs = gs_cls(cfg.stores.neo4j)

    from retrieval.retriever import MultiSourceRetriever
    retriever = MultiSourceRetriever(
        cfg, embedder=embedder, graph_store=gs,
    )

    # Run search
    result = retriever.search(
        query, top_k=top_k, rephrase=not no_rephrase, level=level,
    )

    # ── Display results ──
    click.echo(f"\n{'═' * 70}")
    click.echo(f"  Query: {result.query}")
    click.echo(f"{'═' * 70}")

    if result.rephrased_queries:
        click.echo(f"\n  🔄 Rephrased queries:")
        for i, rq in enumerate(result.rephrased_queries, 1):
            click.echo(f"    Q{i}: {rq}")

    # Query labels
    all_queries = [result.query] + result.rephrased_queries
    q_labels = {result.query: "Q₀"}
    for i, rq in enumerate(result.rephrased_queries, 1):
        q_labels[rq] = f"Q{i}"

    # ── RAPTOR Chunks ──
    click.echo(f"\n{'─' * 70}")
    click.echo(f"  📄 RAPTOR Chunks ({len(result.chunks)} results)")
    click.echo(f"{'─' * 70}")

    if not result.chunks:
        click.echo("  (no results)")
    else:
        for c in result.chunks:
            text_preview = c.text[:200].replace("\n", " ")
            if len(c.text) > 200:
                text_preview += "..."

            click.echo(
                f"\n  [{c.score:.3f}] hits={c.hit_count} "
                f"level={c.level} article={c.article_id}"
            )
            click.echo(f"    node: {c.node_id}")
            if c.keywords:
                click.echo(f"    keywords: {', '.join(c.keywords[:10])}")
            click.echo(f"    text: {text_preview}")
            click.echo(f"    scores: {_format_scores(c.scores_by_query, q_labels)}")

    # ── Concepts ──
    click.echo(f"\n{'─' * 70}")
    click.echo(f"  💡 Concepts ({len(result.concepts)} results)")
    click.echo(f"{'─' * 70}")

    if not result.concepts:
        click.echo("  (no results)")
    else:
        for c in result.concepts:
            click.echo(
                f"\n  [{c.score:.3f}] hits={c.hit_count} "
                f"{c.name} ({c.domain})"
            )
            desc_preview = c.description[:150].replace("\n", " ")
            if len(c.description) > 150:
                desc_preview += "..."
            click.echo(f"    desc: {desc_preview}")
            if c.keywords:
                click.echo(f"    keywords: {', '.join(c.keywords[:10])}")
            if c.articles:
                click.echo(f"    articles: {', '.join(c.articles)}")

            if c.relations:
                click.echo(f"    relations ({len(c.relations)}):")
                for rel in c.relations[:5]:
                    click.echo(
                        f"      → {rel.get('name', '?')} ({rel.get('predicate', '')})"
                    )
                if len(c.relations) > 5:
                    click.echo(f"      ... +{len(c.relations) - 5} more")

            click.echo(f"    scores: {_format_scores(c.scores_by_query, q_labels)}")

    # ── Cross-Relations ──
    click.echo(f"\n{'─' * 70}")
    click.echo(f"  🔗 Cross-Relations ({len(result.relations)} results)")
    click.echo(f"{'─' * 70}")

    if not result.relations:
        click.echo("  (no results)")
    else:
        for r in result.relations:
            src = r.source_name or r.source_concept_id[:8]
            tgt = r.target_name or r.target_concept_id[:8]
            click.echo(
                f"\n  [{r.score:.3f}] hits={r.hit_count} "
                f"{src} → {tgt}"
            )
            click.echo(f"    predicate: {r.predicate}")
            if r.description:
                desc = r.description[:200].replace("\n", " ")
                if len(r.description) > 200:
                    desc += "..."
                click.echo(f"    desc: {desc}")
            click.echo(f"    scores: {_format_scores(r.scores_by_query, q_labels)}")

    # ── Summary ──
    click.echo(f"\n{'═' * 70}")
    total = len(result.chunks) + len(result.concepts) + len(result.relations)
    click.echo(
        f"  Summary: {total} unique results "
        f"({len(result.chunks)} chunks, {len(result.concepts)} concepts, "
        f"{len(result.relations)} relations) "
        f"from {len(all_queries)} query variants"
    )

    for q in all_queries:
        label = q_labels.get(q, q[:40])
        chunk_hits = sum(1 for c in result.chunks if q in c.scores_by_query)
        concept_hits = sum(1 for c in result.concepts if q in c.scores_by_query)
        rel_hits = sum(1 for r in result.relations if q in r.scores_by_query)
        click.echo(f"    {label}: {chunk_hits} chunks, {concept_hits} concepts, {rel_hits} relations")

    click.echo()

    gs.close()


if __name__ == "__main__":
    cli()
