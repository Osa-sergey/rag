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

    # ── Display results (Rich) ──
    from cli_base.logging import get_console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    console = get_console()

    # Query labels
    all_queries = [result.query] + result.rephrased_queries
    q_labels = {result.query: "Q₀"}
    for i, rq in enumerate(result.rephrased_queries, 1):
        q_labels[rq] = f"Q{i}"

    console.rule(f"[bold]Query: {result.query}[/bold]")

    if result.rephrased_queries:
        console.print("\n[bold]🔄 Rephrased queries:[/bold]")
        for i, rq in enumerate(result.rephrased_queries, 1):
            console.print(f"  Q{i}: {rq}")

    # ── RAPTOR Chunks ──
    console.rule(f"[bold]📄 RAPTOR Chunks ({len(result.chunks)} results)")
    if not result.chunks:
        console.print("  [dim](no results)[/dim]")
    else:
        chunks_table = Table(show_lines=True, expand=True)
        chunks_table.add_column("Score", width=7, justify="center")
        chunks_table.add_column("Hits", width=5, justify="center")
        chunks_table.add_column("Level", width=5, justify="center")
        chunks_table.add_column("Article", style="cyan", width=12)
        chunks_table.add_column("Keywords", style="dim", width=25, overflow="ellipsis")
        chunks_table.add_column("Text", ratio=1)

        for c in result.chunks:
            text_preview = c.text[:200].replace("\n", " ")
            if len(c.text) > 200:
                text_preview += "…"
            kw = ", ".join(c.keywords[:10]) if c.keywords else "—"
            chunks_table.add_row(
                f"{c.score:.3f}", str(c.hit_count), str(c.level),
                str(c.article_id), kw, text_preview,
            )
        console.print(chunks_table)

    # ── Concepts ──
    console.rule(f"[bold]💡 Concepts ({len(result.concepts)} results)")
    if not result.concepts:
        console.print("  [dim](no results)[/dim]")
    else:
        for c in result.concepts:
            desc_preview = c.description[:150].replace("\n", " ")
            if len(c.description) > 150:
                desc_preview += "…"
            header = f"[{c.score:.3f}] hits={c.hit_count}  [bold]{c.name}[/bold] ({c.domain})"
            lines = [f"[dim]{desc_preview}[/dim]"]
            if c.keywords:
                lines.append(f"keywords: {', '.join(c.keywords[:10])}")
            if c.articles:
                lines.append(f"articles: {', '.join(c.articles)}")
            if c.relations:
                rel_strs = [f"→ {r.get('name', '?')} ({r.get('predicate', '')})" for r in c.relations[:5]]
                if len(c.relations) > 5:
                    rel_strs.append(f"… +{len(c.relations) - 5} more")
                lines.append("relations: " + " | ".join(rel_strs))
            lines.append(f"scores: {_format_scores(c.scores_by_query, q_labels)}")
            console.print(Panel("\n".join(lines), title=header, border_style="blue"))

    # ── Cross-Relations ──
    console.rule(f"[bold]🔗 Cross-Relations ({len(result.relations)} results)")
    if not result.relations:
        console.print("  [dim](no results)[/dim]")
    else:
        rel_table = Table(show_lines=True, expand=True)
        rel_table.add_column("Score", width=7, justify="center")
        rel_table.add_column("Hits", width=5, justify="center")
        rel_table.add_column("Source", style="cyan", width=18)
        rel_table.add_column("→", width=2, justify="center")
        rel_table.add_column("Target", style="green", width=18)
        rel_table.add_column("Predicate", width=15)
        rel_table.add_column("Description", ratio=1, overflow="ellipsis")

        for r in result.relations:
            src = r.source_name or r.source_concept_id[:8]
            tgt = r.target_name or r.target_concept_id[:8]
            desc = (r.description[:120] + "…") if r.description and len(r.description) > 120 else (r.description or "—")
            rel_table.add_row(
                f"{r.score:.3f}", str(r.hit_count), src, "→", tgt,
                r.predicate, desc,
            )
        console.print(rel_table)

    # ── Summary ──
    console.rule("[bold]Summary")
    total = len(result.chunks) + len(result.concepts) + len(result.relations)
    console.print(
        f"  [bold]{total}[/bold] unique results "
        f"({len(result.chunks)} chunks, {len(result.concepts)} concepts, "
        f"{len(result.relations)} relations) "
        f"from {len(all_queries)} query variants"
    )
    for q in all_queries:
        label = q_labels.get(q, q[:40])
        chunk_hits = sum(1 for c in result.chunks if q in c.scores_by_query)
        concept_hits = sum(1 for c in result.concepts if q in c.scores_by_query)
        rel_hits = sum(1 for r in result.relations if q in r.scores_by_query)
        console.print(f"    {label}: {chunk_hits} chunks, {concept_hits} concepts, {rel_hits} relations")

    console.print()
    gs.close()


if __name__ == "__main__":
    cli()
