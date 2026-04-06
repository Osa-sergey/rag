"""Async core tool functions — framework-agnostic business logic.

Each function accepts a Pydantic Input, delegates to the existing
pipeline classes (via ToolContext), and returns a Pydantic Output.

Heavy / blocking operations run inside ``asyncio.to_thread()``
so the caller's event loop is never blocked.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from rag_tools.bootstrap import ToolContext
from rag_tools.schemas import (
    RaptorProcessInput,
    RaptorProcessOutput,
    ConceptBuildInput,
    ConceptBuildOutput,
    ConceptExpandInput,
    ConceptExpandOutput,
    ExpandedConceptInfo,
    ConceptDryRunInput,
    ConceptDryRunOutput,
    RagSearchInput,
    RagSearchOutput,
    ConceptInspectInput,
    ConceptInspectOutput,
    KeywordTraceInfo,
    CrossRelationInfo,
    ListArticlesInput,
    ListArticlesOutput,
    ArticleInfo,
    ListConceptsInput,
    ListConceptsOutput,
    ConceptInfo,
    ParseDocumentInput,
    ParseDocumentOutput,
    TopicTrainInput,
    TopicTrainOutput,
    TopicPredictInput,
    TopicPredictOutput,
    VaultParseInput,
    VaultParseOutput,
    VaultListTasksInput,
    VaultListTasksOutput,
    VaultSearchInput,
    VaultSearchOutput,
    VaultStatsInput,
    VaultStatsOutput,
    VaultWellnessInput,
    VaultWellnessOutput,
    VaultAddTaskInput,
    VaultUpdateTaskInput,
    VaultDeleteTaskInput,
    VaultCreateNoteInput,
    VaultOperationOutput,
    VaultCheckAccessInput,
    VaultCheckAccessOutput,
)

logger = logging.getLogger(__name__)

_ACCEPTED_RAW_EXTENSIONS = {".md", ".html", ".htm", ".csv"}


# ═══════════════════════════════════════════════════════════════
# Helper: auto-convert raw files to YAML
# ═══════════════════════════════════════════════════════════════

def _ensure_yaml(file_path: str) -> Path:
    """Convert a raw HTML/MD/CSV file to YAML if needed.

    Returns the path to a YAML file ready for the RAPTOR pipeline.
    If the input is already .yaml/.yml, returns it as-is.
    """
    fp = Path(file_path)
    suffix = fp.suffix.lower()

    if suffix in {".yaml", ".yml"}:
        return fp

    if suffix == ".md":
        from document_parser.structurizer import process_md_file
        _, yaml_path = process_md_file(fp)
        logger.info("Converted %s -> %s", fp.name, yaml_path)
        return yaml_path

    if suffix in {".html", ".htm"}:
        from document_parser.structurizer import html_to_ast, ArticleParser
        import yaml as _yaml
        from datetime import datetime

        content = fp.read_text(encoding="utf-8")
        ast = html_to_ast(content)
        parser = ArticleParser()
        structured = parser.parse(ast)
        article_id = fp.stem
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_dir = fp.parent / "parsed_yaml"
        out_dir.mkdir(exist_ok=True)
        yaml_path = out_dir / f"{article_id}_{timestamp}.yaml"
        result = {
            "article_id": article_id,
            "parsed_at": datetime.utcnow().isoformat(),
            "document": structured,
        }
        with yaml_path.open("w", encoding="utf-8") as f:
            _yaml.dump(result, f, allow_unicode=True, sort_keys=False)
        logger.info("Converted %s -> %s", fp.name, yaml_path)
        return yaml_path

    if suffix == ".csv":
        from document_parser.structurizer import process_csv
        results = list(process_csv(fp))
        if not results:
            raise ValueError(f"No articles found in CSV: {fp}")
        # Return the last generated YAML for single-article processing
        _, yaml_path = results[-1]
        logger.info("Converted %s -> %d YAMLs (using %s)", fp.name, len(results), yaml_path)
        return yaml_path

    raise ValueError(
        f"Unsupported file format: '{suffix}'. "
        f"Accepted: .yaml, .yml, .md, .html, .csv"
    )


# ═══════════════════════════════════════════════════════════════
# 1. raptor_process
# ═══════════════════════════════════════════════════════════════

async def raptor_process(
    inp: RaptorProcessInput, ctx: ToolContext,
) -> RaptorProcessOutput:
    """Process an article through the RAPTOR pipeline.

    Automatically converts HTML/MD/CSV to YAML if needed.
    """
    yaml_path = await asyncio.to_thread(_ensure_yaml, inp.file_path)
    pipeline = ctx.build_raptor_pipeline(inp.config_overrides or None)
    result = await asyncio.to_thread(pipeline.process_file, yaml_path)
    return RaptorProcessOutput(**result)


# ═══════════════════════════════════════════════════════════════
# 2. concept_build
# ═══════════════════════════════════════════════════════════════

async def concept_build(
    inp: ConceptBuildInput, ctx: ToolContext,
) -> ConceptBuildOutput:
    """Build cross-article concepts from a set of articles."""
    processor = ctx.build_concept_processor(inp.config_overrides or None)
    result = await asyncio.to_thread(
        processor.process, inp.article_ids,
    )
    return ConceptBuildOutput(
        concepts_created=result.get("concepts_created", 0),
        relations_created=result.get("relations_created", 0),
        concepts=result.get("concepts", []),
        summary=result,
    )


# ═══════════════════════════════════════════════════════════════
# 3. concept_expand
# ═══════════════════════════════════════════════════════════════

async def concept_expand(
    inp: ConceptExpandInput, ctx: ToolContext,
) -> ConceptExpandOutput:
    """Expand existing concepts with keywords from new articles."""
    results = await asyncio.to_thread(
        ctx.concept_processor.expand,
        inp.concept_ids,
        inp.article_ids,
        high_threshold=inp.high_threshold,
        low_threshold=inp.low_threshold,
        llm_confidence_threshold=inp.llm_confidence_threshold,
    )

    expanded = []
    for r in results:
        expanded.append(ExpandedConceptInfo(
            concept_id=r.concept_id,
            concept_name=r.concept_name,
            domain=r.domain,
            original_version=r.original_version,
            direct_keywords=[kw for kw, _ in r.direct_keywords],
            llm_keywords=[kw for kw, _, _ in r.llm_keywords],
        ))
    return ConceptExpandOutput(expanded_concepts=expanded)


# ═══════════════════════════════════════════════════════════════
# 4. concept_dry_run
# ═══════════════════════════════════════════════════════════════

async def concept_dry_run(
    inp: ConceptDryRunInput, ctx: ToolContext,
) -> ConceptDryRunOutput:
    """Preview what concept building would process without running LLM calls."""
    report = await asyncio.to_thread(
        ctx.concept_processor.dry_run, inp.article_ids,
    )
    return ConceptDryRunOutput(
        articles=report.articles,
        article_names=report.article_names,
        total_keywords=report.total_keywords,
        keywords_per_article=report.keywords_per_article,
        estimated_llm_calls=report.estimated_llm_calls,
        unprocessed_articles=report.unprocessed_articles,
    )


# ═══════════════════════════════════════════════════════════════
# 5. rag_search
# ═══════════════════════════════════════════════════════════════

async def rag_search(
    inp: RagSearchInput, ctx: ToolContext,
) -> RagSearchOutput:
    """Multi-source search across RAPTOR chunks, concepts, and relations."""
    result = await asyncio.to_thread(
        ctx.retriever.search,
        inp.query,
        top_k=inp.top_k,
        rephrase=inp.rephrase,
        level=inp.level,
    )
    return RagSearchOutput.from_retrieval_result(result)


# ═══════════════════════════════════════════════════════════════
# 6. concept_inspect
# ═══════════════════════════════════════════════════════════════

async def concept_inspect(
    inp: ConceptInspectInput, ctx: ToolContext,
) -> ConceptInspectOutput:
    """Inspect a concept with full provenance tracing to source chunks."""
    raw = await asyncio.to_thread(
        ctx.concept_inspector.inspect_concept,
        inp.concept_id,
        full_text=inp.full_text,
    )

    if "error" in raw:
        return ConceptInspectOutput(
            concept_id=inp.concept_id,
            canonical_name=raw["error"],
        )

    return ConceptInspectOutput(
        concept_id=raw.get("concept_id", inp.concept_id),
        canonical_name=raw.get("canonical_name", ""),
        domain=raw.get("domain", ""),
        description=raw.get("description", ""),
        source_articles=raw.get("source_articles", []),
        version=raw.get("version"),
        is_active=raw.get("is_active"),
        run_id=raw.get("run_id"),
        keywords=raw.get("keywords", []),
        keyword_traces=[
            KeywordTraceInfo(**trace) for trace in raw.get("keyword_traces", [])
        ],
        cross_relations=[
            CrossRelationInfo(**rel) for rel in raw.get("cross_relations", [])
        ],
    )


# ═══════════════════════════════════════════════════════════════
# 7. list_articles
# ═══════════════════════════════════════════════════════════════

def _list_articles_from_neo4j(ctx: ToolContext) -> list[dict]:
    """Query all articles from Neo4j."""
    gs = ctx.graph_store
    with gs._driver.session(database=gs._database) as session:
        result = session.run(
            "MATCH (a:Article) "
            "OPTIONAL MATCH (a)-[r:HAS_KEYWORD]->(k:Keyword) "
            "RETURN a.id AS id, a.article_name AS name, "
            "       a.summary IS NOT NULL AS has_summary, "
            "       count(DISTINCT k) AS kw_count "
            "ORDER BY a.id"
        )
        return [
            {
                "id": str(r["id"]),
                "name": r.get("name") or "",
                "keyword_count": r.get("kw_count", 0),
                "has_summary": bool(r.get("has_summary")),
            }
            for r in result
        ]


async def list_articles(
    inp: ListArticlesInput, ctx: ToolContext,
) -> ListArticlesOutput:
    """List all indexed articles from Neo4j."""
    raw = await asyncio.to_thread(_list_articles_from_neo4j, ctx)
    return ListArticlesOutput(
        articles=[ArticleInfo(**a) for a in raw],
    )


# ═══════════════════════════════════════════════════════════════
# 8. list_concepts
# ═══════════════════════════════════════════════════════════════

def _list_concepts_from_neo4j(
    ctx: ToolContext,
    domain: str | None = None,
    article_id: str | None = None,
) -> list[dict]:
    """Query concepts from Neo4j with optional filters."""
    gs = ctx.graph_store
    where_parts = []
    params: dict[str, Any] = {}
    if domain:
        where_parts.append("c.domain = $domain")
        params["domain"] = domain
    if article_id:
        where_parts.append("$article_id IN c.source_articles")
        params["article_id"] = article_id

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    with gs._driver.session(database=gs._database) as session:
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
                   count(DISTINCT r) AS relations_count
            ORDER BY c.domain, c.canonical_name
            """,
            **params,
        ).data()

    return [
        {
            "id": c.get("id", ""),
            "name": c.get("name", ""),
            "domain": c.get("domain", ""),
            "description": c.get("description", ""),
            "keyword_words": c.get("keyword_words") or [],
            "source_articles": c.get("source_articles") or [],
            "relations_count": c.get("relations_count", 0),
            "version": c.get("version") or 1,
            "is_active": c.get("is_active", True),
        }
        for c in result
    ]


async def list_concepts(
    inp: ListConceptsInput, ctx: ToolContext,
) -> ListConceptsOutput:
    """List concepts from Neo4j with optional domain/article filters."""
    raw = await asyncio.to_thread(
        _list_concepts_from_neo4j, ctx, inp.domain, inp.article_id,
    )
    return ListConceptsOutput(
        concepts=[ConceptInfo(**c) for c in raw],
    )


# ═══════════════════════════════════════════════════════════════
# 9. parse_document
# ═══════════════════════════════════════════════════════════════

def _parse_document_sync(file_path: str, output_dir: str | None) -> dict:
    """Parse a raw document file to YAML synchronously."""
    fp = Path(file_path)
    suffix = fp.suffix.lower()
    out_dir = Path(output_dir) if output_dir else Path("parsed_yaml")

    if suffix == ".md":
        from document_parser.structurizer import process_md_file
        result, yaml_path = process_md_file(fp, output_dir=out_dir)
        return {
            "yaml_path": str(yaml_path),
            "article_id": result.get("article_id", fp.stem),
            "blocks": len(result.get("document", [])),
            "articles_parsed": 1,
        }

    if suffix in {".html", ".htm"}:
        from document_parser.structurizer import html_to_ast, ArticleParser
        import yaml as _yaml
        from datetime import datetime

        content = fp.read_text(encoding="utf-8")
        ast = html_to_ast(content)
        parser = ArticleParser()
        structured = parser.parse(ast)
        article_id = fp.stem
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_dir.mkdir(exist_ok=True)
        yaml_path = out_dir / f"{article_id}_{timestamp}.yaml"
        result = {
            "article_id": article_id,
            "parsed_at": datetime.utcnow().isoformat(),
            "document": structured,
        }
        with yaml_path.open("w", encoding="utf-8") as f:
            _yaml.dump(result, f, allow_unicode=True, sort_keys=False)
        return {
            "yaml_path": str(yaml_path),
            "article_id": article_id,
            "blocks": len(structured),
            "articles_parsed": 1,
        }

    if suffix == ".csv":
        from document_parser.structurizer import process_csv
        results = list(process_csv(fp, output_dir=out_dir))
        if not results:
            raise ValueError(f"No articles found in CSV: {fp}")
        _, last_yaml = results[-1]
        return {
            "yaml_path": str(last_yaml),
            "article_id": results[-1][0].get("article_id", ""),
            "blocks": sum(len(r.get("document", [])) for r, _ in results),
            "articles_parsed": len(results),
        }

    raise ValueError(f"Unsupported format: '{suffix}'. Use .md, .html, or .csv")


async def parse_document(
    inp: ParseDocumentInput, ctx: ToolContext,
) -> ParseDocumentOutput:
    """Parse a raw document (MD/HTML/CSV) into structured YAML."""
    result = await asyncio.to_thread(
        _parse_document_sync, inp.file_path, inp.output_dir,
    )
    return ParseDocumentOutput(**result)


# ═══════════════════════════════════════════════════════════════
# 10. topic_modeler
# ═══════════════════════════════════════════════════════════════

async def topic_train(
    inp: TopicTrainInput, ctx: ToolContext,
) -> TopicTrainOutput:
    """Train BERTopic on all/selected articles."""
    cfg = {"article_ids": inp.article_ids}
    cfg.update(inp.config_overrides)
    res = await ctx.run_step("topic_modeler.train", **cfg)
    if not isinstance(res, dict): res = {}
    return TopicTrainOutput(
        topics_found=res.get("topics_found", 0),
        docs_trained=res.get("docs_trained", 0),
    )

async def topic_predict(
    inp: TopicPredictInput, ctx: ToolContext,
) -> TopicPredictOutput:
    """Predict topic for an article and rewrite its YAML."""
    cfg = {"article_path": inp.article_path}
    cfg.update(inp.config_overrides)
    res = await ctx.run_step("topic_modeler.add_article", **cfg)
    if not isinstance(res, dict): res = {}
    return TopicPredictOutput(
        topic=res.get("topic", ""),
        confidence=res.get("confidence", 0.0),
    )

# ═══════════════════════════════════════════════════════════════
# 11. vault_parser & vault_acl
# ═══════════════════════════════════════════════════════════════

async def vault_parse(
    inp: VaultParseInput, ctx: ToolContext,
) -> VaultParseOutput:
    res = await ctx.run_step("vault_parser.parse", **inp.config_overrides)
    return VaultParseOutput(**res)

async def vault_list_tasks(
    inp: VaultListTasksInput, ctx: ToolContext,
) -> VaultListTasksOutput:
    res = await ctx.run_step("vault_parser.list_tasks", status=inp.status, priority=inp.priority, date_range=inp.date_range, person=inp.person, section=inp.section)
    return VaultListTasksOutput(**res)

async def vault_search(
    inp: VaultSearchInput, ctx: ToolContext,
) -> VaultSearchOutput:
    res = await ctx.run_step("vault_parser.search", query=inp.query)
    return VaultSearchOutput(**res)

async def vault_stats(
    inp: VaultStatsInput, ctx: ToolContext,
) -> VaultStatsOutput:
    res = await ctx.run_step("vault_parser.stats")
    return VaultStatsOutput(**res)

async def vault_wellness(
    inp: VaultWellnessInput, ctx: ToolContext,
) -> VaultWellnessOutput:
    res = await ctx.run_step("vault_parser.wellness", date_range=inp.date_range)
    return VaultWellnessOutput(**res)

async def vault_add_task(
    inp: VaultAddTaskInput, ctx: ToolContext,
) -> VaultOperationOutput:
    res = await ctx.run_step("vault_parser.add_task", date=inp.date, text=inp.text, section=inp.section, status=inp.status, people=inp.people, scheduled_date=inp.scheduled_date, due_date=inp.due_date)
    return VaultOperationOutput(success=res.get("success", False), message="Task added")

async def vault_update_task(
    inp: VaultUpdateTaskInput, ctx: ToolContext,
) -> VaultOperationOutput:
    res = await ctx.run_step("vault_parser.update_task", date=inp.date, query=inp.query, status=inp.status)
    return VaultOperationOutput(success=res.get("success", False), message="Task updated")

async def vault_delete_task(
    inp: VaultDeleteTaskInput, ctx: ToolContext,
) -> VaultOperationOutput:
    res = await ctx.run_step("vault_parser.delete_task", date=inp.date, query=inp.query)
    return VaultOperationOutput(success=res.get("success", False), message="Task deleted")

async def vault_create_note(
    inp: VaultCreateNoteInput, ctx: ToolContext,
) -> VaultOperationOutput:
    res = await ctx.run_step("vault_parser.create_note", date=inp.date)
    return VaultOperationOutput(success=bool(res.get("path")), message=f"Created {res.get('path')}")

async def vault_check_access(
    inp: VaultCheckAccessInput, ctx: ToolContext,
) -> VaultCheckAccessOutput:
    res = await ctx.run_step("vault_acl.check_access", user=inp.user, file_path=inp.file_path, action=inp.action)
    return VaultCheckAccessOutput(**res)
