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


# ── Click CLI ─────────────────────────────────────────────────
@click.group()
@click.option("-v", "--verbose", is_flag=True, help="DEBUG logging")
def cli(verbose: bool) -> None:
    """Retrieval — multi-source RAG retrieval for quality analysis."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s %(name)s: %(message)s",
    )


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
    top_k = top_k or cfg.get("top_k", 10)

    # Build dependencies
    from raptor_pipeline.embeddings.providers import create_embedding_provider
    embedder = create_embedding_provider(cfg.embeddings)

    from stores.graph_store import Neo4jGraphStore
    gs = Neo4jGraphStore(cfg.stores.neo4j)

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
            click.echo(f"    {i}. {rq}")

    # All query labels for trace display
    all_queries = [result.query] + result.rephrased_queries
    q_labels = {result.query: "Q₀ (original)"}
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
            weighted = c.score * c.hit_count
            text_preview = c.text[:200].replace("\n", " ")
            if len(c.text) > 200:
                text_preview += "..."

            click.echo(
                f"\n  [{c.score:.3f}×{c.hit_count}={weighted:.3f}] "
                f"level={c.level} article={c.article_id}"
            )
            click.echo(f"    node: {c.node_id}")
            if c.keywords:
                click.echo(f"    keywords: {', '.join(c.keywords[:10])}")
            click.echo(f"    text: {text_preview}")

            # Trace: which queries found this
            unique_sources = []
            seen = set()
            for fb in c.found_by:
                label = q_labels.get(fb, fb[:40])
                if label not in seen:
                    seen.add(label)
                    unique_sources.append(label)
            click.echo(f"    found by: {', '.join(unique_sources)}")

    # ── Concepts ──
    click.echo(f"\n{'─' * 70}")
    click.echo(f"  💡 Concepts ({len(result.concepts)} results)")
    click.echo(f"{'─' * 70}")

    if not result.concepts:
        click.echo("  (no results)")
    else:
        for c in result.concepts:
            weighted = c.score * c.hit_count
            click.echo(
                f"\n  [{c.score:.3f}×{c.hit_count}={weighted:.3f}] "
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

            # Relations
            if c.relations:
                click.echo(f"    relations ({len(c.relations)}):")
                for rel in c.relations[:5]:
                    click.echo(
                        f"      → {rel.get('name', '?')} ({rel.get('predicate', '')})"
                    )
                if len(c.relations) > 5:
                    click.echo(f"      ... +{len(c.relations) - 5} more")

            # Trace
            unique_sources = []
            seen = set()
            for fb in c.found_by:
                label = q_labels.get(fb, fb[:40])
                if label not in seen:
                    seen.add(label)
                    unique_sources.append(label)
            click.echo(f"    found by: {', '.join(unique_sources)}")

    # ── Cross-Relations ──
    click.echo(f"\n{'─' * 70}")
    click.echo(f"  🔗 Cross-Relations ({len(result.relations)} results)")
    click.echo(f"{'─' * 70}")

    if not result.relations:
        click.echo("  (no results)")
    else:
        for r in result.relations:
            weighted = r.score * r.hit_count
            src = r.source_name or r.source_concept_id[:8]
            tgt = r.target_name or r.target_concept_id[:8]
            click.echo(
                f"\n  [{r.score:.3f}×{r.hit_count}={weighted:.3f}] "
                f"{src} → {tgt}"
            )
            click.echo(f"    predicate: {r.predicate}")
            if r.description:
                desc = r.description[:200].replace("\n", " ")
                if len(r.description) > 200:
                    desc += "..."
                click.echo(f"    desc: {desc}")

            unique_sources = []
            seen = set()
            for fb in r.found_by:
                label = q_labels.get(fb, fb[:40])
                if label not in seen:
                    seen.add(label)
                    unique_sources.append(label)
            click.echo(f"    found by: {', '.join(unique_sources)}")

    # ── Summary ──
    click.echo(f"\n{'═' * 70}")
    total = len(result.chunks) + len(result.concepts) + len(result.relations)
    click.echo(
        f"  Summary: {total} unique results "
        f"({len(result.chunks)} chunks, {len(result.concepts)} concepts, "
        f"{len(result.relations)} relations) "
        f"from {len(all_queries)} query variants"
    )

    # Show how many results came from each query
    for q in all_queries:
        label = q_labels.get(q, q[:40])
        chunk_hits = sum(1 for c in result.chunks if q in c.found_by)
        concept_hits = sum(1 for c in result.concepts if q in c.found_by)
        rel_hits = sum(1 for r in result.relations if q in r.found_by)
        click.echo(f"    {label}: {chunk_hits} chunks, {concept_hits} concepts, {rel_hits} relations")

    click.echo()

    gs.close()


if __name__ == "__main__":
    cli()
