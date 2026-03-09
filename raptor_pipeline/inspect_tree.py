"""Utility script to visualize the RAPTOR tree structure from Qdrant."""
from __future__ import annotations

import hydra
from omegaconf import DictConfig
from qdrant_client import QdrantClient
from qdrant_client.http import models

def print_tree(nodes: dict, node_id: str, indent: str = "", is_last: bool = True, show_full_text: bool = False):
    """Recursively print the tree structure."""
    if node_id not in nodes:
        print(f"{indent}└── [MISSING] {node_id}")
        return

    node = nodes[node_id]
    level = node.get("level", 0)
    text = node.get("text", "")
    
    if show_full_text:
        # Format full text with proper indentation
        lines = text.strip().split("\n")
        text_display = "\n".join([(indent + ("    " if is_last else "│   ") + "    " + line) for line in lines])
        text_snippet = f"\n{text_display}"
    else:
        text_snippet = ": " + text[:100].replace("\n", " ").strip() + "..."
    
    marker = "└── " if is_last else "├── "
    type_label = "📄 ТЕКСТ" if level == 0 else "📝 САММАРИ"
    print(f"{indent}{marker}[Level {level} | {type_label}] ID: {node_id}")
    if show_full_text:
        print(f"{indent}{'    ' if is_last else '│   '}Text:{text_snippet}")
    else:
        print(f"{indent}{'    ' if is_last else '│   '}{text_snippet}")
    
    new_indent = indent + ("    " if is_last else "│   ")
    children = node.get("children_ids", [])
    
    for i, child_id in enumerate(children):
        print_tree(nodes, child_id, new_indent, i == len(children) - 1, show_full_text)

@hydra.main(config_path="conf", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:
    client = QdrantClient(
        host=cfg.stores.qdrant.get("host", "localhost"),
        port=cfg.stores.qdrant.get("port", 6333),
    )
    collection = cfg.stores.qdrant.get("collection_name", "raptor_chunks")
    
    print(f"Fetching nodes from collection '{collection}'...")
    
    article_id = cfg.get("article_id", None)
    
    scroll_filter = None
    if article_id:
        print(f"Filtering by article_id: {article_id}")
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
        print("No points found in collection.")
        return

    # Map nodes by their node_id
    nodes_map = {}
    for p in points:
        payload = p.payload
        if "node_id" in payload:
            nodes_map[payload["node_id"]] = payload
        else:
            # Fallback for old records without node_id in payload (unlikely to work well)
            print(f"Warning: Point {p.id} missing 'node_id' in payload.")

    if not nodes_map:
        print("No nodes with 'node_id' found. Try running the pipeline again to update data.")
        return

    # Find root nodes (nodes that are not children of any other node)
    # Or just nodes at the highest level
    all_children = set()
    for node in nodes_map.values():
        for child_id in node.get("children_ids", []):
            all_children.add(child_id)
            
    roots = [
        node_id for node_id, node in nodes_map.items() 
        if node_id not in all_children and node.get("level", 0) > 0
    ]
    
    # If no hierarchy found (v0 only), just show leaves or highest level
    if not roots:
        max_level = max(n.get("level", 0) for n in nodes_map.values())
        roots = [nid for nid, n in nodes_map.items() if n.get("level", 0) == max_level]

    show_full_text = cfg.get("full_text", False)
    
    print(f"\nRAPTOR Tree Structure (Total nodes: {len(nodes_map)}):")
    print("=" * 60)
    for i, root_id in enumerate(roots):
        print_tree(nodes_map, root_id, is_last=(i == len(roots) - 1), show_full_text=show_full_text)
    print("=" * 60)
    
    if not show_full_text:
        print("\nTip: Use 'full_text=true' (or '+full_text=true' if not in config) to see complete content.")

if __name__ == "__main__":
    main()
