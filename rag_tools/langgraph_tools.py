"""LangGraph-compatible @tool wrappers with LLM-friendly output.

Each tool is an async function decorated with ``@tool`` from
``langchain_core.tools``.  All tools return LLM-formatted text
via adapters from ``rag_tools.formatters``.

Usage::

    from langgraph.prebuilt import ToolNode
    from rag_tools.langgraph_tools import get_tools

    tool_node = ToolNode(get_tools())
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from langchain_core.tools import tool, BaseTool

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

_ctx: ToolContext | None = None


def _get_ctx() -> ToolContext:
    """Return the shared ToolContext, creating it on first call."""
    global _ctx
    if _ctx is None:
        _ctx = ToolContext()
    return _ctx


def init_context(ctx: ToolContext) -> None:
    """Allow external code to inject a pre-configured ToolContext."""
    global _ctx
    _ctx = ctx


# ─── Tool definitions ────────────────────────────────────────


@tool
async def raptor_process(
    file_path: str,
    config_overrides: Optional[dict[str, Any]] = None,
) -> str:
    """Process an article through the RAPTOR pipeline.

    Accepts any format: .yaml (pre-parsed), .md, .html, or .csv.
    Non-YAML files are automatically converted first.
    Creates hierarchical text chunks, RAPTOR tree with LLM summaries,
    extracts keywords and relations, stores in Qdrant + Neo4j.

    Use config_overrides to change LLM or pipeline settings per call, e.g.:
      {"summarizer.provider": "ollama", "raptor.max_levels": 4}
    """
    inp = RaptorProcessInput(
        file_path=file_path,
        config_overrides=config_overrides or {},
    )
    result = await _tools.raptor_process(inp, _get_ctx())
    return _fmt.format_raptor_process(result)


@tool
async def concept_build(
    article_ids: list[str],
    config_overrides: Optional[dict[str, Any]] = None,
) -> str:
    """Build cross-article concepts from a set of articles.

    Loads keywords from Neo4j, generates descriptions via LLM,
    clusters semantically similar keywords into Concepts, and
    discovers cross-article relations between them.

    Use config_overrides to change LLM or clustering settings, e.g.:
      {"llm.provider": "ollama", "clustering.min_cluster_size": 2}
    """
    inp = ConceptBuildInput(
        article_ids=article_ids,
        config_overrides=config_overrides or {},
    )
    result = await _tools.concept_build(inp, _get_ctx())
    return _fmt.format_concept_build(result)


@tool
async def concept_expand(
    concept_ids: list[str],
    article_ids: list[str],
    high_threshold: float = 0.85,
    low_threshold: float = 0.65,
) -> str:
    """Expand existing concepts with keywords from new articles.

    Matches new keywords to existing concepts via cosine similarity
    and LLM verification, creating new concept versions.
    """
    inp = ConceptExpandInput(
        concept_ids=concept_ids,
        article_ids=article_ids,
        high_threshold=high_threshold,
        low_threshold=low_threshold,
    )
    result = await _tools.concept_expand(inp, _get_ctx())
    return _fmt.format_concept_expand(result)


@tool
async def concept_dry_run(article_ids: list[str]) -> str:
    """Preview what concept building would do without LLM calls.

    Returns article counts, keyword statistics, and estimated
    LLM calls for cost estimation.
    """
    inp = ConceptDryRunInput(article_ids=article_ids)
    result = await _tools.concept_dry_run(inp, _get_ctx())
    return _fmt.format_concept_dry_run(result)


@tool
async def rag_search(
    query: str,
    top_k: int = 10,
    rephrase: bool = True,
    level: Optional[int] = None,
) -> str:
    """Multi-source RAG search across RAPTOR chunks, concepts, and relations.

    Generates rephrased query variants via LLM, embeds them,
    searches Qdrant collections, deduplicates results,
    and enriches concepts with Neo4j relations.
    """
    inp = RagSearchInput(
        query=query, top_k=top_k, rephrase=rephrase, level=level,
    )
    result = await _tools.rag_search(inp, _get_ctx())
    return _fmt.format_rag_search(result)


@tool
async def concept_inspect(
    concept_id: str,
    full_text: bool = False,
) -> str:
    """Inspect a concept with full provenance tracing.

    Traces from Concept to Keywords to source Chunks,
    showing which articles contributed and similarity scores.
    """
    inp = ConceptInspectInput(concept_id=concept_id, full_text=full_text)
    result = await _tools.concept_inspect(inp, _get_ctx())
    return _fmt.format_concept_inspect(result)


@tool
async def list_articles() -> str:
    """List all indexed articles in the knowledge base.

    Returns article IDs, names, keyword counts, and summary status.
    Use this to discover available article_ids for other tools.
    """
    inp = ListArticlesInput()
    result = await _tools.list_articles(inp, _get_ctx())
    articles = [a.model_dump() for a in result.articles]
    return _fmt.format_article_list(articles)


@tool
async def list_concepts(
    domain: Optional[str] = None,
    article_id: Optional[str] = None,
) -> str:
    """List all concepts in the knowledge base.

    Optional filters by domain or source article_id.
    Returns concept IDs, names, keywords, and relation counts.
    Use this to discover concept_ids for inspect or expand tools.
    """
    inp = ListConceptsInput(domain=domain, article_id=article_id)
    result = await _tools.list_concepts(inp, _get_ctx())
    concepts = [c.model_dump() for c in result.concepts]
    return _fmt.format_concept_list(concepts)


@tool
async def parse_document(
    file_path: str,
    output_dir: Optional[str] = None,
) -> str:
    """Parse a raw document (Markdown, HTML, or CSV) into structured YAML.

    The generated YAML can then be processed by raptor_process.
    For most cases, use raptor_process directly — it auto-converts.
    Use this tool when you only want to parse without indexing.
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


@tool
async def topic_train(
    article_ids: list[str],
    config_overrides: Optional[dict[str, Any]] = None,
) -> str:
    """Train BERTopic on all/selected articles."""
    inp = TopicTrainInput(article_ids=article_ids, config_overrides=config_overrides or {})
    result = await _tools.topic_train(inp, _get_ctx())
    return f"Trained {result.docs_trained} docs, found {result.topics_found} topics."

@tool
async def topic_predict(
    article_path: str,
    config_overrides: Optional[dict[str, Any]] = None,
) -> str:
    """Predict topic for an article and rewrite its YAML."""
    inp = TopicPredictInput(article_path=article_path, config_overrides=config_overrides or {})
    result = await _tools.topic_predict(inp, _get_ctx())
    return f"Topic: {result.topic} (confidence: {result.confidence:.2f})"

@tool
async def vault_parse(
    config_overrides: Optional[dict[str, Any]] = None,
) -> str:
    """Full parsing of Obsidian Vault to JSON."""
    inp = VaultParseInput(config_overrides=config_overrides or {})
    result = await _tools.vault_parse(inp, _get_ctx())
    return f"Parsed {result.daily_count} daily, {result.weekly_count} weekly, {result.monthly_count} monthly."

@tool
async def vault_list_tasks(
    status: Optional[str] = None,
    date_range: Optional[str] = None,
    person: Optional[str] = None,
    priority: Optional[str] = None,
    section: Optional[str] = None,
) -> str:
    """List tasks from Obsidian Vault."""
    import json
    inp = VaultListTasksInput(status=status, date_range=date_range, person=person, priority=priority, section=section)
    result = await _tools.vault_list_tasks(inp, _get_ctx())
    return f"Found {result.count} tasks.\n" + json.dumps(result.tasks, ensure_ascii=False, indent=2)

@tool
async def vault_search(query: str) -> str:
    """Search tasks in Obsidian Vault."""
    import json
    inp = VaultSearchInput(query=query)
    result = await _tools.vault_search(inp, _get_ctx())
    return f"Found {result.count} tasks.\n" + json.dumps(result.tasks, ensure_ascii=False, indent=2)

@tool
async def vault_stats() -> str:
    """Get task stats from Obsidian Vault."""
    import json
    inp = VaultStatsInput()
    result = await _tools.vault_stats(inp, _get_ctx())
    return json.dumps(result.model_dump(), indent=2)

@tool
async def vault_wellness(date_range: Optional[str] = None) -> str:
    """Get wellness entries from Obsidian Vault."""
    import json
    inp = VaultWellnessInput(date_range=date_range)
    result = await _tools.vault_wellness(inp, _get_ctx())
    return json.dumps(result.entries, ensure_ascii=False, indent=2)

@tool
async def vault_add_task(
    date: str,
    text: str,
    section: str = "main",
    status: str = "open",
    people: Optional[str] = None,
    scheduled_date: Optional[str] = None,
    due_date: Optional[str] = None,
) -> str:
    """Add a task to a daily note."""
    inp = VaultAddTaskInput(date=date, text=text, section=section, status=status, people=people, scheduled_date=scheduled_date, due_date=due_date)
    result = await _tools.vault_add_task(inp, _get_ctx())
    return result.message

@tool
async def vault_update_task(
    date: str,
    query: str,
    status: str,
) -> str:
    """Update task status in a daily note."""
    inp = VaultUpdateTaskInput(date=date, query=query, status=status)
    result = await _tools.vault_update_task(inp, _get_ctx())
    return result.message

@tool
async def vault_delete_task(
    date: str,
    query: str,
) -> str:
    """Delete task from a daily note."""
    inp = VaultDeleteTaskInput(date=date, query=query)
    result = await _tools.vault_delete_task(inp, _get_ctx())
    return result.message

@tool
async def vault_create_note(date: str) -> str:
    """Create a daily note from template."""
    inp = VaultCreateNoteInput(date=date)
    result = await _tools.vault_create_note(inp, _get_ctx())
    return result.message

@tool
async def vault_check_access(
    user: str,
    file_path: str,
    action: str = "read",
) -> str:
    """Check a user's role-based access to a file."""
    inp = VaultCheckAccessInput(user=user, file_path=file_path, action=action)
    result = await _tools.vault_check_access(inp, _get_ctx())
    return f"Allowed: {result.allowed}\nPermissions: {result.permissions}\nRules matched: {result.rules_matched}"

# ─── Public API ──────────────────────────────────────────────

def get_tools() -> list[BaseTool]:
    """Return all RAG tools for use with LangGraph ToolNode.

    Usage::

        from langgraph.prebuilt import ToolNode
        from rag_tools.langgraph_tools import get_tools

        tool_node = ToolNode(get_tools())
    """
    return [
        raptor_process,
        concept_build,
        concept_expand,
        concept_dry_run,
        rag_search,
        concept_inspect,
        list_articles,
        list_concepts,
        parse_document,
        topic_train,
        topic_predict,
        vault_parse,
        vault_list_tasks,
        vault_search,
        vault_stats,
        vault_wellness,
        vault_add_task,
        vault_update_task,
        vault_delete_task,
        vault_create_note,
        vault_check_access,
    ]
