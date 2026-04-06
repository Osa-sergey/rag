"""LLM-friendly output formatters for RAG tool results.

Each formatter converts a Pydantic output model into a compact,
structured text representation optimized for LLM consumption:
- Consistent markdown-like structure
- Key facts first, details later
- Numbered items for easy reference
- Concise labels (no emoji, no rich formatting)
"""
from __future__ import annotations

from typing import Any

from rag_tools.schemas import (
    RaptorProcessOutput,
    ConceptBuildOutput,
    ConceptExpandOutput,
    ConceptDryRunOutput,
    RagSearchOutput,
    ConceptInspectOutput,
)


def format_raptor_process(out: RaptorProcessOutput) -> str:
    """Format raptor_process result for LLM."""
    lines = [
        f"# Article Processed: {out.article_name or out.article_id}",
        f"- article_id: {out.article_id}",
        f"- version: {out.version}" if out.version else None,
        f"- chunks: {out.chunks}",
        f"- raptor_nodes: {out.raptor_nodes}",
        f"- unique_keywords: {out.unique_keywords}",
        f"- relations: {out.relations}",
    ]
    if out.article_summary:
        lines.append(f"\n## Summary\n{out.article_summary}")
    if out.links:
        lines.append(f"\n## Cross-Article Links ({len(out.links)})")
        for i, lnk in enumerate(out.links, 1):
            lines.append(f"{i}. [{lnk.link_type}] {lnk.display} -> {lnk.target}")
    if out.token_usage:
        total = out.token_usage.get("total_tokens", "?")
        lines.append(f"\n## Token Usage: {total} total tokens")
    return "\n".join(l for l in lines if l is not None)


def format_concept_build(out: ConceptBuildOutput) -> str:
    """Format concept_build result for LLM."""
    lines = [
        f"# Concept Building Result",
        f"- concepts_created: {out.concepts_created}",
        f"- relations_created: {out.relations_created}",
    ]
    if out.concepts:
        lines.append(f"\n## Concepts ({len(out.concepts)})")
        for i, c in enumerate(out.concepts, 1):
            name = c.get("name", "?")
            domain = c.get("domain", "?")
            kws = ", ".join(c.get("keywords", []))
            arts = ", ".join(c.get("articles", []))
            lines.append(
                f"{i}. **{name}** (domain: {domain})\n"
                f"   - id: {c.get('id', '?')}\n"
                f"   - keywords: {kws}\n"
                f"   - articles: {arts}"
            )
    return "\n".join(lines)


def format_concept_expand(out: ConceptExpandOutput) -> str:
    """Format concept_expand result for LLM."""
    if not out.expanded_concepts:
        return "No concepts were expanded."
    lines = [f"# Expanded Concepts ({len(out.expanded_concepts)})"]
    for i, ec in enumerate(out.expanded_concepts, 1):
        direct = ", ".join(ec.direct_keywords) if ec.direct_keywords else "none"
        llm = ", ".join(ec.llm_keywords) if ec.llm_keywords else "none"
        lines.append(
            f"{i}. **{ec.concept_name}** (domain: {ec.domain}, v{ec.original_version})\n"
            f"   - id: {ec.concept_id}\n"
            f"   - direct matches: {direct}\n"
            f"   - LLM-verified: {llm}"
        )
    return "\n".join(lines)


def format_concept_dry_run(out: ConceptDryRunOutput) -> str:
    """Format concept_dry_run result for LLM."""
    lines = [
        f"# Concept Build Dry Run",
        f"- articles: {len(out.articles)}",
        f"- total_keywords: {out.total_keywords}",
        f"- estimated_llm_calls: {out.estimated_llm_calls}",
    ]
    if out.unprocessed_articles:
        lines.append(
            f"- WARNING: {len(out.unprocessed_articles)} articles have no keywords "
            f"(run raptor_process first): {', '.join(out.unprocessed_articles)}"
        )
    lines.append(f"\n## Articles")
    for aid in out.articles:
        name = out.article_names.get(aid, aid)
        kw_count = out.keywords_per_article.get(aid, 0)
        lines.append(f"- {aid} ({name}): {kw_count} keywords")
    return "\n".join(lines)


def format_rag_search(out: RagSearchOutput) -> str:
    """Format rag_search result for LLM."""
    lines = [f"# Search Results for: {out.query}"]
    if out.rephrased_queries:
        lines.append(f"Query variants: {', '.join(out.rephrased_queries)}")

    if out.chunks:
        lines.append(f"\n## Chunks ({len(out.chunks)})")
        for i, c in enumerate(out.chunks, 1):
            kws = ", ".join(c.keywords) if c.keywords else ""
            lines.append(
                f"\n### {i}. [{c.article_id} L{c.level}] score={c.score:.3f}"
                f"{f' keywords: {kws}' if kws else ''}\n{c.text}"
            )

    if out.concepts:
        lines.append(f"\n## Concepts ({len(out.concepts)})")
        for i, c in enumerate(out.concepts, 1):
            arts = ", ".join(c.articles) if c.articles else ""
            lines.append(
                f"{i}. **{c.name}** (domain: {c.domain}, score={c.score:.3f})\n"
                f"   {c.description}"
                f"{f' | articles: {arts}' if arts else ''}"
            )

    if out.relations:
        lines.append(f"\n## Relations ({len(out.relations)})")
        for i, r in enumerate(out.relations, 1):
            lines.append(
                f"{i}. {r.source_name} --[{r.predicate}]--> {r.target_name}"
                f" (score={r.score:.3f}): {r.description}"
            )

    return "\n".join(lines)


def format_concept_inspect(out: ConceptInspectOutput) -> str:
    """Format concept_inspect result for LLM."""
    lines = [
        f"# Concept: {out.canonical_name}",
        f"- id: {out.concept_id}",
        f"- domain: {out.domain}",
        f"- version: {out.version}" if out.version else None,
        f"- active: {out.is_active}" if out.is_active is not None else None,
        f"- articles: {', '.join(out.source_articles)}" if out.source_articles else None,
        f"- keywords: {', '.join(out.keywords)}" if out.keywords else None,
    ]
    if out.description:
        lines.append(f"\n## Description\n{out.description}")

    if out.keyword_traces:
        lines.append(f"\n## Keyword Traces ({len(out.keyword_traces)})")
        for i, t in enumerate(out.keyword_traces, 1):
            status = "IN CONCEPT" if t.in_concept else "outside"
            sim = f"sim={t.similarity:.3f}" if t.similarity is not None else ""
            conf = f"conf={t.confidence:.2f}" if t.confidence is not None else ""
            scores = " ".join(s for s in [sim, conf] if s)
            lines.append(
                f"{i}. '{t.word}' in {t.article_id}"
                f" ({t.article_name or '?'}) [{status}] {scores}"
            )
            if t.chunks:
                for c in t.chunks:
                    level_label = f"L{c.get('level', 0)}"
                    lines.append(
                        f"   - chunk [{level_label}]: {c.get('text', '')[:200]}"
                    )

    if out.cross_relations:
        lines.append(f"\n## Cross-Relations ({len(out.cross_relations)})")
        for i, r in enumerate(out.cross_relations, 1):
            lines.append(
                f"{i}. --[{r.predicate}]--> {r.other_name} ({r.other_domain}): {r.description}"
            )

    return "\n".join(l for l in lines if l is not None)


# ── List formatters ──────────────────────────────────────────


def format_article_list(articles: list[dict]) -> str:
    """Format article list for LLM."""
    lines = [f"# Articles ({len(articles)})"]
    for i, a in enumerate(articles, 1):
        aid = a.get("id", "?")
        name = a.get("name", "")
        kw_count = a.get("keyword_count", 0)
        has_summary = a.get("has_summary", False)
        flags = []
        if has_summary:
            flags.append("has_summary")
        if kw_count:
            flags.append(f"{kw_count} keywords")
        flag_str = f" ({', '.join(flags)})" if flags else ""
        lines.append(f"{i}. {aid} - {name}{flag_str}")
    return "\n".join(lines)


def format_concept_list(concepts: list[dict]) -> str:
    """Format concept list for LLM."""
    lines = [f"# Concepts ({len(concepts)})"]
    for i, c in enumerate(concepts, 1):
        name = c.get("name", "?")
        domain = c.get("domain", "?")
        cid = c.get("id", "?")
        kws = ", ".join(c.get("keyword_words") or [])
        arts = ", ".join(c.get("source_articles") or [])
        rels = c.get("relations_count", 0)
        version = c.get("version") or 1
        active = c.get("is_active", True)
        status = "active" if active else "inactive"
        lines.append(
            f"{i}. **{name}** (domain: {domain}, v{version}, {status})\n"
            f"   - id: {cid}\n"
            f"   - keywords: {kws or 'none'}\n"
            f"   - articles: {arts or 'none'}"
            f"{f', relations: {rels}' if rels else ''}"
        )
    return "\n".join(lines)
