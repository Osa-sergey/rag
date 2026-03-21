"""Utility script to visualize the RAPTOR tree structure from Qdrant."""
from __future__ import annotations

import hydra
from omegaconf import DictConfig
from qdrant_client import QdrantClient
from qdrant_client.http import models
from rich.tree import Tree as RichTree
from rich.text import Text


def _build_tree(
    tree: RichTree,
    nodes: dict,
    node_id: str,
    show_full_text: bool = False,
):
    """Recursively add nodes to a Rich Tree."""
    if node_id not in nodes:
        tree.add(Text(f"[MISSING] {node_id}", style="bold red"))
        return

    node = nodes[node_id]
    level = node.get("level", 0)
    text = node.get("text", "")

    if level == 0:
        icon, type_label, style = "📄", "ТЕКСТ", "green"
    else:
        icon, type_label, style = "📝", "САММАРИ", "yellow"

    label = Text()
    label.append(f"{icon} ", style="bold")
    label.append(f"Level {level}", style=f"bold {style}")
    label.append(f" | {type_label}", style=style)
    label.append(f"  {node_id}", style="dim")

    branch = tree.add(label)

    if show_full_text:
        snippet = Text(text.strip(), style="dim")
    else:
        snippet = Text(text[:100].replace("\n", " ").strip() + "…", style="dim")
    branch.add(snippet)

    for child_id in node.get("children_ids", []):
        _build_tree(branch, nodes, child_id, show_full_text)

def main(cfg: DictConfig) -> None:
    """Core inspect-tree logic, callable from Click or standalone."""
    from cli_base.logging import get_console
    console = get_console()

    client = QdrantClient(
        host=cfg.stores.qdrant.get("host", "localhost"),
        port=cfg.stores.qdrant.get("port", 6333),
    )
    collection = cfg.stores.qdrant.get("collection_name", "raptor_chunks")
    
    console.print(f"Fetching nodes from collection [cyan]{collection}[/cyan]...")
    
    article_id = cfg.get("article_id", None)
    if article_id is not None:
        article_id = str(article_id)  # Hydra may parse numeric IDs as int
    
    scroll_filter = None
    if article_id:
        console.print(f"Filtering by article_id: [cyan]{article_id}[/cyan]")
        scroll_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="article_id",
                    match=models.MatchValue(value=article_id),
                )
            ]
        )
    
    # Fetch all points (assuming small to medium collection for inspection)
    points, _ = client.scroll(
        collection_name=collection,
        scroll_filter=scroll_filter,
        with_payload=True,
        with_vectors=False,
        limit=5000,
    )
    
    if not points:
        console.print("[yellow]No points found in collection.[/yellow]")
        if article_id:
            # Debug: show what article_ids actually exist
            sample, _ = client.scroll(
                collection_name=collection,
                with_payload=["article_id"],
                with_vectors=False,
                limit=20,
            )
            existing_ids = {p.payload.get("article_id", "?") for p in sample}
            console.print(f"  [dim](existing article_ids sample: {existing_ids})[/dim]")
        return

    # Map nodes by their node_id
    nodes_map = {}
    for p in points:
        payload = p.payload
        if "node_id" in payload:
            nodes_map[payload["node_id"]] = payload
        else:
            # Fallback for old records without node_id in payload (unlikely to work well)
            console.print(f"[yellow]Warning: Point {p.id} missing 'node_id' in payload.[/yellow]")

    if not nodes_map:
        console.print("[yellow]No nodes with 'node_id' found. Try running the pipeline again to update data.[/yellow]")
        return

    # Find root nodes (nodes that are not children of any other node)
    # Or just nodes at the highest level
    all_children = set()
    for node in nodes_map.values():
        for child_id in node.get("children_ids", []):
            all_children.add(child_id)
            
    roots = [
        node_id for node_id, node in nodes_map.items() 
        if node_id not in all_children
    ]
    
    # If no roots found at all, fallback to highest-level nodes
    if not roots:
        max_level = max(n.get("level", 0) for n in nodes_map.values())
        roots = [nid for nid, n in nodes_map.items() if n.get("level", 0) == max_level]

    # Sort roots: summaries first (descending by level), then leaves
    roots.sort(key=lambda nid: -nodes_map[nid].get("level", 0))

    show_full_text = cfg.get("full_text", False)

    # Build and print Rich tree
    tree = RichTree(
        f"🌳 RAPTOR Tree  [dim]({len(nodes_map)} nodes)[/dim]",
        guide_style="bold bright_blue",
    )
    for root_id in roots:
        _build_tree(tree, nodes_map, root_id, show_full_text=show_full_text)
    console.print(tree)
    
    if not show_full_text:
        console.print("\n[dim]Tip: Use 'full_text=true' to see complete content.[/dim]")

    # ── Show article summary from Neo4j ───────────────────────
    try:
        from neo4j import GraphDatabase
        n_cfg = cfg.stores.neo4j
        driver = GraphDatabase.driver(n_cfg.uri, auth=(n_cfg.user, n_cfg.password))
        
        # Determine which article_ids are present
        article_ids_in_tree = set()
        for node in nodes_map.values():
            aid = node.get("article_id", "")
            if aid:
                article_ids_in_tree.add(aid)
        
        if article_id:
            article_ids_in_tree = {article_id}
        
        with driver.session(database=n_cfg.database) as session:
            for aid in sorted(article_ids_in_tree):
                result = session.run(
                    "MATCH (a:Article {id: $id}) RETURN a.summary AS summary, a.article_name AS name",
                    id=aid,
                )
                record = result.single()
                if record and record["summary"]:
                    name = record.get("name") or aid
                    from rich.panel import Panel
                    from cli_base.logging import get_console
                    get_console().print(Panel(record["summary"], title=f"📋 {name}", border_style="green"))
                else:
                    print(f"\n(Саммари для '{aid}' не найдено в Neo4j)")
        
        driver.close()
    except Exception as exc:
        print(f"\n(Не удалось загрузить саммари из Neo4j: {exc})")

@hydra.main(config_path="conf", config_name="config", version_base=None)
def _hydra_main(cfg: DictConfig) -> None:
    main(cfg)

if __name__ == "__main__":
    _hydra_main()
