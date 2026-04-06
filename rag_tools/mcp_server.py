"""FastMCP server exposing RAG tools via MCP protocol.

Run::

    python -m rag_tools.mcp_server          # stdio transport
    python -m rag_tools.mcp_server --sse     # SSE HTTP transport

Or via entry point::

    rag-mcp
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from rag_tools import tools as _tools
from rag_tools import formatters as _fmt
from rag_tools.bootstrap import ToolContext
from rag_tools.schemas import (
    RaptorProcessInput,
    ConceptBuildInput,
    ConceptExpandInput,
    ConceptDryRunInput,
    RagSearchInput,
    ConceptInspectInput,
    ListArticlesInput,
    ListConceptsInput,
    ParseDocumentInput,
    TopicTrainInput,
    TopicPredictInput,
    VaultParseInput,
    VaultListTasksInput,
    VaultSearchInput,
    VaultStatsInput,
    VaultWellnessInput,
    VaultAddTaskInput,
    VaultUpdateTaskInput,
    VaultDeleteTaskInput,
    VaultCreateNoteInput,
    VaultCheckAccessInput,
)

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "rag-tools",
    instructions=(
        "RAPTOR RAG pipeline tools: process articles, build concepts, "
        "search knowledge base, list articles/concepts, and inspect provenance."
    ),
)

_ctx: ToolContext | None = None


def _get_ctx() -> ToolContext:
    global _ctx
    if _ctx is None:
        _ctx = ToolContext()
    return _ctx


# ─── Tool registrations ──────────────────────────────────────


@mcp.tool()
async def raptor_process(
    file_path: str,
    config_overrides: dict[str, Any] | None = None,
) -> str:
    """Process an article through the RAPTOR pipeline.

    Accepts .yaml, .md, .html, or .csv files.
    Non-YAML files are auto-converted first.
    Use config_overrides for per-call LLM/pipeline settings.
    """
    inp = RaptorProcessInput(
        file_path=file_path,
        config_overrides=config_overrides or {},
    )
    result = await _tools.raptor_process(inp, _get_ctx())
    return _fmt.format_raptor_process(result)


@mcp.tool()
async def concept_build(
    article_ids: list[str],
    config_overrides: dict[str, Any] | None = None,
) -> str:
    """Build cross-article concepts from articles.

    Clusters keywords, generates descriptions, discovers relations.
    """
    inp = ConceptBuildInput(
        article_ids=article_ids,
        config_overrides=config_overrides or {},
    )
    result = await _tools.concept_build(inp, _get_ctx())
    return _fmt.format_concept_build(result)


@mcp.tool()
async def concept_expand(
    concept_ids: list[str],
    article_ids: list[str],
    high_threshold: float = 0.85,
    low_threshold: float = 0.65,
) -> str:
    """Expand existing concepts with keywords from new articles."""
    inp = ConceptExpandInput(
        concept_ids=concept_ids,
        article_ids=article_ids,
        high_threshold=high_threshold,
        low_threshold=low_threshold,
    )
    result = await _tools.concept_expand(inp, _get_ctx())
    return _fmt.format_concept_expand(result)


@mcp.tool()
async def concept_dry_run(article_ids: list[str]) -> str:
    """Preview concept building without LLM calls.

    Returns keyword stats and estimated LLM costs.
    """
    inp = ConceptDryRunInput(article_ids=article_ids)
    result = await _tools.concept_dry_run(inp, _get_ctx())
    return _fmt.format_concept_dry_run(result)


@mcp.tool()
async def rag_search(
    query: str,
    top_k: int = 10,
    rephrase: bool = True,
    level: int | None = None,
) -> str:
    """Multi-source RAG search across chunks, concepts, and relations.

    Rephrases query via LLM, searches Qdrant, deduplicates, enriches.
    """
    inp = RagSearchInput(
        query=query, top_k=top_k, rephrase=rephrase, level=level,
    )
    result = await _tools.rag_search(inp, _get_ctx())
    return _fmt.format_rag_search(result)


@mcp.tool()
async def concept_inspect(
    concept_id: str,
    full_text: bool = False,
) -> str:
    """Inspect a concept with provenance to source chunks."""
    inp = ConceptInspectInput(concept_id=concept_id, full_text=full_text)
    result = await _tools.concept_inspect(inp, _get_ctx())
    return _fmt.format_concept_inspect(result)


@mcp.tool()
async def list_articles() -> str:
    """List all indexed articles in the knowledge base.

    Returns IDs, names, keyword counts, summary status.
    """
    inp = ListArticlesInput()
    result = await _tools.list_articles(inp, _get_ctx())
    articles = [a.model_dump() for a in result.articles]
    return _fmt.format_article_list(articles)


@mcp.tool()
async def list_concepts(
    domain: str | None = None,
    article_id: str | None = None,
) -> str:
    """List concepts with optional domain/article filters.

    Returns IDs, names, keywords, relations counts.
    """
    inp = ListConceptsInput(domain=domain, article_id=article_id)
    result = await _tools.list_concepts(inp, _get_ctx())
    concepts = [c.model_dump() for c in result.concepts]
    return _fmt.format_concept_list(concepts)


@mcp.tool()
async def parse_document(
    file_path: str,
    output_dir: str | None = None,
) -> str:
    """Parse a raw document (MD/HTML/CSV) into structured YAML.

    Use raptor_process directly for most cases (auto-converts).
    This tool is for parsing without indexing.
    """
    inp = ParseDocumentInput(file_path=file_path, output_dir=output_dir)
    result = await _tools.parse_document(inp, _get_ctx())
    return (
        f"# Document Parsed\n"
        f"- yaml_path: {result.yaml_path}\n"
        f"- article_id: {result.article_id}\n"
        f"- blocks: {result.blocks}\n"
        f"- articles_parsed: {result.articles_parsed}"
    )


@mcp.tool()
async def topic_train(
    article_ids: list[str],
    config_overrides: dict[str, Any] | None = None,
) -> str:
    """Train BERTopic on all/selected articles."""
    inp = TopicTrainInput(article_ids=article_ids, config_overrides=config_overrides or {})
    result = await _tools.topic_train(inp, _get_ctx())
    return f"Trained {result.docs_trained} docs, found {result.topics_found} topics."


@mcp.tool()
async def topic_predict(
    article_path: str,
    config_overrides: dict[str, Any] | None = None,
) -> str:
    """Predict topic for an article and rewrite its YAML."""
    inp = TopicPredictInput(article_path=article_path, config_overrides=config_overrides or {})
    result = await _tools.topic_predict(inp, _get_ctx())
    return f"Topic: {result.topic} (confidence: {result.confidence:.2f})"


@mcp.tool()
async def vault_parse(
    config_overrides: dict[str, Any] | None = None,
) -> str:
    """Full parsing of Obsidian Vault to JSON."""
    inp = VaultParseInput(config_overrides=config_overrides or {})
    result = await _tools.vault_parse(inp, _get_ctx())
    return f"Parsed {result.daily_count} daily, {result.weekly_count} weekly, {result.monthly_count} monthly."


@mcp.tool()
async def vault_list_tasks(
    status: str | None = None,
    date_range: str | None = None,
    person: str | None = None,
    priority: str | None = None,
    section: str | None = None,
) -> str:
    """List tasks from Obsidian Vault."""
    import json
    inp = VaultListTasksInput(status=status, date_range=date_range, person=person, priority=priority, section=section)
    result = await _tools.vault_list_tasks(inp, _get_ctx())
    return f"Found {result.count} tasks.\n" + json.dumps(result.tasks, ensure_ascii=False, indent=2)


@mcp.tool()
async def vault_search(query: str) -> str:
    """Search tasks in Obsidian Vault."""
    import json
    inp = VaultSearchInput(query=query)
    result = await _tools.vault_search(inp, _get_ctx())
    return f"Found {result.count} tasks.\n" + json.dumps(result.tasks, ensure_ascii=False, indent=2)


@mcp.tool()
async def vault_stats() -> str:
    """Get task stats from Obsidian Vault."""
    import json
    inp = VaultStatsInput()
    result = await _tools.vault_stats(inp, _get_ctx())
    return json.dumps(result.model_dump(), indent=2)


@mcp.tool()
async def vault_wellness(date_range: str | None = None) -> str:
    """Get wellness entries from Obsidian Vault."""
    import json
    inp = VaultWellnessInput(date_range=date_range)
    result = await _tools.vault_wellness(inp, _get_ctx())
    return json.dumps(result.entries, ensure_ascii=False, indent=2)


@mcp.tool()
async def vault_add_task(
    date: str,
    text: str,
    section: str = "main",
    status: str = "open",
    people: str | None = None,
    scheduled_date: str | None = None,
    due_date: str | None = None,
) -> str:
    """Add a task to a daily note."""
    inp = VaultAddTaskInput(date=date, text=text, section=section, status=status, people=people, scheduled_date=scheduled_date, due_date=due_date)
    result = await _tools.vault_add_task(inp, _get_ctx())
    return result.message


@mcp.tool()
async def vault_update_task(
    date: str,
    query: str,
    status: str,
) -> str:
    """Update task status in a daily note."""
    inp = VaultUpdateTaskInput(date=date, query=query, status=status)
    result = await _tools.vault_update_task(inp, _get_ctx())
    return result.message


@mcp.tool()
async def vault_delete_task(
    date: str,
    query: str,
) -> str:
    """Delete task from a daily note."""
    inp = VaultDeleteTaskInput(date=date, query=query)
    result = await _tools.vault_delete_task(inp, _get_ctx())
    return result.message


@mcp.tool()
async def vault_create_note(date: str) -> str:
    """Create a daily note from template."""
    inp = VaultCreateNoteInput(date=date)
    result = await _tools.vault_create_note(inp, _get_ctx())
    return result.message


@mcp.tool()
async def vault_check_access(
    user: str,
    file_path: str,
    action: str = "read",
) -> str:
    """Check a user's role-based access to a file."""
    inp = VaultCheckAccessInput(user=user, file_path=file_path, action=action)
    result = await _tools.vault_check_access(inp, _get_ctx())
    return f"Allowed: {result.allowed}\nPermissions: {result.permissions}\nRules matched: {result.rules_matched}"


# ─── Entry point ─────────────────────────────────────────────

def main():
    mcp.run()


if __name__ == "__main__":
    main()
