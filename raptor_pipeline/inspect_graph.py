"""Utility script to browse Knowledge Graph in Neo4j and link back to Qdrant text."""
from __future__ import annotations

import sys
import hydra
from omegaconf import DictConfig
from qdrant_client import QdrantClient
from qdrant_client.http import models
from neo4j import GraphDatabase

def get_chunk_text(q_client: QdrantClient, collection: str, chunk_id: str) -> str:
    """Fetch text for a specific chunk_id from Qdrant."""
    # We store node_id in payload, and chunk_id is used for node_id during extraction
    points, _ = q_client.scroll(
        collection_name=collection,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="node_id",
                    match=models.MatchValue(value=chunk_id),
                )
            ]
        ),
        limit=1,
        with_payload=True,
    )
    if points and points[0].payload:
        return points[0].payload.get("text", "[No text found]")
    return "[Chunk not found in Qdrant]"


def _fix_cyrillic_args():
    """Fix Hydra LexerNoViableAltException for Cyrillic values.

    Hydra's OmegaConf lexer can't handle non-ASCII characters in
    unquoted CLI values.  We wrap such values in single quotes so
    OmegaConf treats them as plain strings.

    Example:
        word=оптимизация  →  word='оптимизация'
    """
    fixed = []
    for arg in sys.argv[1:]:
        if "=" in arg and not arg.startswith("--"):
            key, value = arg.split("=", 1)
            # If value has non-ASCII chars and is not already quoted
            has_non_ascii = any(ord(c) > 127 for c in value)
            already_quoted = (
                (value.startswith("'") and value.endswith("'"))
                or (value.startswith('"') and value.endswith('"'))
            )
            if has_non_ascii and not already_quoted:
                arg = f"{key}='{value}'"
        fixed.append(arg)
    sys.argv[1:] = fixed


# Apply the fix BEFORE Hydra parses args
_fix_cyrillic_args()


def main(cfg: DictConfig, article_id: str | None = None, min_confidence: float | None = None) -> None:
    """Core inspect-graph logic, callable from Click or standalone."""
    from cli_base.logging import get_console
    from rich.table import Table
    from rich.tree import Tree as RichTree
    from rich.panel import Panel
    from rich.text import Text

    console = get_console()

    # 1. Connect to Neo4j
    n_cfg = cfg.stores.neo4j
    driver = GraphDatabase.driver(n_cfg.uri, auth=(n_cfg.user, n_cfg.password))
    
    # 2. Connect to Qdrant
    q_cfg = cfg.stores.qdrant
    q_client = QdrantClient(host=q_cfg.host, port=q_cfg.port)
    q_collection = q_cfg.collection_name

    keyword_to_inspect = cfg.get("word", None)
    # article_id can come from function arg or config
    filter_article = article_id or cfg.get("article_id", None)

    with driver.session(database=n_cfg.database) as session:
        if not keyword_to_inspect:
            if filter_article:
                # Mode A2: List keywords for a specific article (with confidence)
                conf_label = f" (confidence ≥ {min_confidence})" if min_confidence else ""
                result = session.run(
                    """
                    MATCH (a:Article {id: $article_id})-[r:HAS_KEYWORD]->(k:Keyword)
                    RETURN k.word AS word, k.category AS category,
                           r.confidence AS confidence,
                           k.original_words AS original_words,
                           r.chunk_ids AS chunk_ids
                    ORDER BY r.confidence DESC, word
                    """,
                    article_id=filter_article,
                )
                all_keywords = list(result)
                # Apply min_confidence filter
                if min_confidence is not None:
                    keywords = [kw for kw in all_keywords if (kw.get('confidence') or 0) >= min_confidence]
                else:
                    keywords = all_keywords
                if not all_keywords:
                    console.print(f"[yellow]No keywords found for article '{filter_article}'.[/yellow]")
                    # Debug: check if article exists
                    art = session.run(
                        "MATCH (a:Article {id: $id}) RETURN a.id AS id, a.article_name AS name",
                        id=filter_article,
                    ).single()
                    if art:
                        console.print(f"  Article exists: {art['id']} ({art.get('name', '?')})")
                        raw_count = session.run(
                            "MATCH (a:Article {id: $id})-[r:HAS_KEYWORD]->(k) RETURN count(r) AS cnt",
                            id=filter_article,
                        ).single()
                        console.print(f"  Total HAS_KEYWORD edges: {raw_count['cnt'] if raw_count else 0}")
                    else:
                        console.print(f"  [red]Article '{filter_article}' NOT FOUND in Neo4j.[/red]")
                        similar = session.run(
                            "MATCH (a:Article) WHERE a.id CONTAINS $partial OR a.article_name CONTAINS $partial "
                            "RETURN a.id AS id, a.article_name AS name LIMIT 5",
                            partial=filter_article,
                        ).data()
                        if similar:
                            console.print(f"  Similar articles: {similar}")
                elif not keywords:
                    console.print(f"[yellow]No keywords with confidence ≥ {min_confidence} (total: {len(all_keywords)})[/yellow]")
                else:
                    tbl = Table(title=f"Keywords for Article '{filter_article}'{conf_label}", show_lines=False)
                    tbl.add_column("Keyword", style="bold cyan")
                    tbl.add_column("Category", style="dim")
                    tbl.add_column("Conf", justify="right", width=6)
                    tbl.add_column("Chunks", justify="right", width=7)
                    tbl.add_column("Merged from", style="dim", overflow="ellipsis")
                    for kw in keywords:
                        conf = kw.get('confidence')
                        conf_str = f"{conf:.2f}" if conf is not None else "NULL"
                        orig = kw.get('original_words') or []
                        chunks = kw.get('chunk_ids') or []
                        tbl.add_row(
                            kw['word'], kw['category'], conf_str,
                            str(len(chunks)) if chunks else "—",
                            ", ".join(orig) if orig else "",
                        )
                    console.print(tbl)
                    shown = len(keywords)
                    total = len(all_keywords)
                    if min_confidence is not None and total != shown:
                        console.print(f"  Shown: {shown}/{total} (confidence ≥ {min_confidence})")
                    else:
                        console.print(f"  Total: {total} keywords")
                # Show confidence distribution
                if all_keywords:
                    confs = [kw.get('confidence') or 0 for kw in all_keywords]
                    high = sum(1 for c in confs if c >= 0.8)
                    med = sum(1 for c in confs if 0.5 <= c < 0.8)
                    low = sum(1 for c in confs if c < 0.5)
                    console.print(f"  [dim]Confidence distribution: ≥0.8: {high}, 0.5–0.8: {med}, <0.5: {low}[/dim]")
            else:
                # Mode A1: List all keywords globally
                result = session.run(
                    """
                    MATCH (k:Keyword)
                    OPTIONAL MATCH ()-[r:HAS_KEYWORD]->(k)
                    RETURN k.word AS word, k.category AS category,
                           k.original_words AS original_words,
                           max(r.confidence) AS max_confidence,
                           count(r) AS article_count
                    ORDER BY word
                    """
                )
                keywords = list(result)
                if not keywords:
                    console.print("[yellow]No keywords found in Neo4j.[/yellow]")
                else:
                    tbl = Table(title="Available Keywords in Neo4j", show_lines=False)
                    tbl.add_column("Keyword", style="bold cyan")
                    tbl.add_column("Category", style="dim")
                    tbl.add_column("Max Conf", justify="right", width=9)
                    tbl.add_column("Articles", justify="right", width=9)
                    tbl.add_column("Merged from", style="dim", overflow="ellipsis")
                    for kw in keywords:
                        conf = kw.get('max_confidence')
                        conf_str = f"{conf:.2f}" if conf is not None else ""
                        art_count = kw.get('article_count', 0)
                        orig = kw.get('original_words') or []
                        tbl.add_row(
                            kw['word'], kw['category'], conf_str,
                            str(art_count) if art_count else "—",
                            ", ".join(orig) if orig else "",
                        )
                    console.print(tbl)
                    console.print(f"  Total: {len(keywords)} keywords")
            console.print("\n[dim]Tip: Use '--word KEYWORD' to inspect relationships. Use '--article-id ID' to filter.[/dim]")
        
        else:
            # ── Mode B: Inspect specific keyword ──
            # 0. Show keyword info
            kw_info = session.run(
                "MATCH (k:Keyword {word: $word}) RETURN k.category AS category, k.original_words AS original_words",
                word=keyword_to_inspect,
            )
            kw_record = kw_info.single()

            # Build a Rich tree rooted at the keyword
            kw_tree = RichTree(
                Text.assemble(
                    ("🔑 ", "bold"),
                    (keyword_to_inspect, "bold cyan"),
                    (f"  ({kw_record['category']})" if kw_record else "", "dim"),
                ),
                guide_style="bold bright_blue",
            )
            if kw_record:
                orig = kw_record.get('original_words') or []
                if orig:
                    kw_tree.add(Text(f"Merged from: {', '.join(orig)}", style="dim"))

            # 1. Relations — grouped by source chunk
            result = session.run(
                """
                MATCH (s:Keyword {word: $word})-[r:RELATED_TO]->(o:Keyword)
                RETURN s.word AS subject, r.predicate AS predicate, o.word AS object, r.chunk_ids AS chunk_ids
                UNION
                MATCH (s:Keyword)-[r:RELATED_TO]->(o:Keyword {word: $word})
                RETURN s.word AS subject, r.predicate AS predicate, o.word AS object, r.chunk_ids AS chunk_ids
                """,
                word=keyword_to_inspect
            )
            
            relations = list(result)
            if not relations:
                kw_tree.add(Text("No relations found", style="dim yellow"))
            else:
                rels_branch = kw_tree.add(
                    f"[bold]🔗 Relations[/bold] [dim]({len(relations)} total)[/dim]"
                )

                # Group relations by chunk_id
                chunk_to_rels: dict[str, list[dict]] = {}
                for rel in relations:
                    c_ids = rel.get('chunk_ids', []) or []
                    if isinstance(c_ids, str):
                        c_ids = [c_ids]
                    if not c_ids:
                        c_ids = ["(no chunk)"]
                    for c_id in c_ids:
                        chunk_to_rels.setdefault(c_id, []).append(dict(rel))
                
                processed_chunks = set()
                for c_id, rels_in_chunk in chunk_to_rels.items():
                    chunk_branch = rels_branch.add(f"[bold]📦 Chunk:[/bold] [cyan]{c_id}[/cyan]")
                    for rel in rels_in_chunk:
                        chunk_branch.add(
                            Text.assemble(
                                (rel['subject'], "green"),
                                (" ──[", ""),
                                (rel['predicate'], "yellow"),
                                ("]──▶ ", ""),
                                (rel['object'], "green"),
                            )
                        )
                    
                    # Show chunk text once per group
                    if c_id and c_id != "(no chunk)" and c_id not in processed_chunks:
                        text = get_chunk_text(q_client, q_collection, c_id)
                        chunk_branch.add(Panel(text, title="Source Text", border_style="dim", width=90))
                        processed_chunks.add(c_id)
            
            # 2. Articles mentioning this keyword
            result = session.run(
                """
                MATCH (a:Article)-[r:HAS_KEYWORD]->(k:Keyword {word: $word})
                RETURN a.id AS article_id, a.article_name AS article_name,
                       r.confidence AS confidence, r.chunk_ids AS chunk_ids
                """,
                word=keyword_to_inspect
            )
            articles = list(result)
            if articles:
                arts_branch = kw_tree.add(
                    f"[bold]📰 Articles[/bold] [dim]({len(articles)})[/dim]"
                )
                for art in articles:
                    c_ids = art.get('chunk_ids', []) or []
                    if isinstance(c_ids, str): c_ids = [c_ids]
                    conf = art.get('confidence')
                    conf_str = f" conf={conf:.2f}" if conf is not None else " conf=NULL"
                    name = art.get('article_name') or ''
                    name_str = f" ({name})" if name else ''
                    arts_branch.add(
                        f"[cyan]{art['article_id']}[/cyan]{name_str} [dim]{conf_str}  [{len(c_ids)} chunks][/dim]"
                    )

            # 3. Cross-article references
            result = session.run(
                """
                MATCH (src:Article)-[r:REFERENCES]->(tgt:Article)
                WHERE src.id = $word OR tgt.id = $word
                   OR src.article_name = $word OR tgt.article_name = $word
                RETURN src.id AS source, tgt.id AS target,
                       r.display AS display, r.section AS section,
                       r.chunk_ids AS chunk_ids
                """,
                word=keyword_to_inspect,
            )
            refs = list(result)
            if refs:
                refs_branch = kw_tree.add(
                    f"[bold]🔀 Cross-References[/bold] [dim]({len(refs)})[/dim]"
                )
                for ref in refs:
                    c_ids = ref.get('chunk_ids', []) or []
                    if isinstance(c_ids, str):
                        c_ids = [c_ids]
                    section_str = f"#{ref['section']}" if ref.get('section') else ""
                    ref_branch = refs_branch.add(
                        Text.assemble(
                            ("[", ""), (ref['source'], "cyan"), ("] → [", ""),
                            (ref['target'], "green"), (section_str, "dim"), ("]", ""),
                            (f"  display='{ref.get('display', '')}'", "dim"),
                        )
                    )
                    for c_id in c_ids:
                        if c_id:
                            text = get_chunk_text(q_client, q_collection, c_id)
                            ref_branch.add(Panel(text, title=f"Chunk {c_id}", border_style="dim", width=80))

            console.print(kw_tree)

    driver.close()

@hydra.main(config_path="conf", config_name="config", version_base=None)
def _hydra_main(cfg: DictConfig) -> None:
    main(cfg)

if __name__ == "__main__":
    _hydra_main()
