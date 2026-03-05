from pathlib import Path
import yaml
from typing import List, Dict, Tuple


# ───────────────────────────────────────
# INLINE COLLECTORS
# ───────────────────────────────────────

def collect_from_inlines(inlines, block_id, images, links):
    for item in inlines or []:
        if item["type"] == "image":
            images.append({
                "block_id": block_id,
                "order": item["order"],
                "src": item["src"],
            })

        elif item["type"] == "link":
            links.append({
                "block_id": block_id,
                "order": item["order"],
                "href": item["href"],
                "text": item.get("text", "")
            })


# ───────────────────────────────────────
# LIST (RECURSIVE)
# ───────────────────────────────────────

def collect_from_list(list_node, images, links):
    for item in list_node.get("items", []):
        item_id = item["id"]

        for paragraph in item.get("paragraphs", []):
            collect_from_inlines(paragraph, item_id, images, links)

        for nested in item.get("lists", []):
            collect_from_list(nested, images, links)


# ───────────────────────────────────────
# BLOCKQUOTE
# ───────────────────────────────────────

def collect_from_blockquote(blockquote, parent_id, images, links):
    for child in blockquote.get("children", []):
        ctype = child["type"]

        if ctype in {"paragraph", "header"}:
            collect_from_inlines(child.get("children"), parent_id, images, links)

        elif ctype in {"bullet_list", "ordered_list"}:
            collect_from_list(child, images, links)


# ───────────────────────────────────────
# MAIN COLLECTOR
# ───────────────────────────────────────

def collect_assets(document) -> Tuple[List[Dict], List[Dict]]:
    images = []
    links = []

    for block in document:
        block_id = block["id"]
        block_type = block["type"]

        if block_type in {"paragraph", "header"}:
            collect_from_inlines(block.get("children"), block_id, images, links)

        elif block_type == "list":
            collect_from_list(block["items"], images, links)

        elif block_type == "blockquote":
            collect_from_blockquote(block, block_id, images, links)

        elif block_type == "image":
            images.append({
                "block_id": block_id,
                "order": 1,
                "src": block["src"],
            })

        elif block_type == "link":
            links.append({
                "block_id": block_id,
                "order": 1,
                "href": block["href"],
                "text": block.get("text", "")
            })

    return images, links


# ───────────────────────────────────────
# FILE PIPELINE
# ───────────────────────────────────────

def process_yaml_file(yaml_path: Path, output_dir: Path):
    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    article_id = data.get("article_id", yaml_path.stem)
    document = data.get("document", [])

    images, links = collect_assets(document)

    output_dir.mkdir(parents=True, exist_ok=True)

    images_path = output_dir / f"{article_id}_images.yaml"
    links_path = output_dir / f"{article_id}_links.yaml"

    with images_path.open("w", encoding="utf-8") as f:
        yaml.dump(images, f, allow_unicode=True, sort_keys=False)

    with links_path.open("w", encoding="utf-8") as f:
        yaml.dump(links, f, allow_unicode=True, sort_keys=False)

    return images_path, links_path


# ───────────────────────────────────────
# MAIN
# ───────────────────────────────────────

if __name__ == "__main__":
    INPUT_DIR = Path("parsed_yaml")
    OUTPUT_DIR = Path("assets")

    for yaml_file in INPUT_DIR.glob("*.yaml"):
        images_file, links_file = process_yaml_file(yaml_file, OUTPUT_DIR)
        print(f"✓ {yaml_file.name}")
        print(f"  → images: {images_file.name}")
        print(f"  → links : {links_file.name}")
