from pathlib import Path
from typing import Dict, List, Optional
import yaml


# ───────────────────────────────────────
# INLINE
# ───────────────────────────────────────
def render_inline(node: Dict) -> str:
    text = node.get("text", "")
    if not text:
        return ""

    # link — отдельный случай
    if node.get("type") == "link":
        href = node.get("href")
        if href:
            return f"[{text}]({href})"
        return text

    marks = node.get("marks") or []
    for mark in marks:
        if isinstance(mark, str):
            mtype = mark
        elif isinstance(mark, dict):
            mtype = mark.get("type")
        else:
            continue
        if mtype == "bold":
            text = f"**{text}**"
        elif mtype == "italic":
            text = f"*{text}*"
        elif mtype == "code":
            text = f"`{text}`"

    return text



def inline_text(children: List[Dict]) -> str:
    parts = []
    for c in children or []:
        if c.get("type") in {"text", "link"}:
            rendered = render_inline(c)
            if rendered:
                parts.append(rendered)
    return " ".join(parts)


# ───────────────────────────────────────
# FLATTEN DOCUMENT (DEPTH-FIRST)
# ───────────────────────────────────────

def flatten_blocks(blocks: List[Dict]) -> List[Dict]:
    flat = []

    def walk(block):
        # сохраняем блок, если есть id
        if "id" in block:
            flat.append(block)

        btype = block.get("type")

        if btype == "list":
            for item in block.get("items", {}).get("items", []):
                # каждый list_item добавляем в flat с id
                flat.append({
                    "id": str(item["id"]),
                    "type": "list_item",
                    "paragraphs": item.get("paragraphs", []),
                    "lists": item.get("lists", [])
                })
                # рекурсивно обходим вложенные списки
                for nested in item.get("lists", []):
                    walk({"type": "list", "id": nested.get("id"), "items": nested})

        elif btype == "blockquote":
            for child in block.get("children", []):
                walk(child)

    for b in blocks:
        walk(b)

    return flat


# ───────────────────────────────────────
# RENDER BLOCK
# ───────────────────────────────────────

def render_block(block: Dict) -> str:
    t = block.get("type")

    if t == "header":
        level = block.get("level", 1)
        content = inline_text(block.get("children"))
        if content:
            return f"{'#' * level} {content}"
        else:
            return f"{'#' * level}"  # если текст пустой, пробел не нужен

    if t == "paragraph":
        return inline_text(block.get("children"))

    if t == "list_item":
        lines = []
        for para in block.get("paragraphs", []):
            text = inline_text(para)
            if text:
                lines.append(f"- {text}")
        # вложенные списки
        for nested in block.get("lists", []):
            nested_text = render_block({"type": "list", "items": nested})
            if nested_text:
                lines.append(nested_text)
        return "\n".join(lines)

    if t == "list":
        lines = []
        for item in block.get("items", {}).get("items", []):
            lines.append(render_block(item))
        return "\n".join(lines)

    if t == "blockquote":
        texts = []
        for child in block.get("children", []):
            if child.get("type") in {"paragraph", "header", "list", "list_item", "blockquote"}:
                text = render_block(child)
                if text:
                    texts.append(text)
        return "\n\n".join(texts)

    return ""



# ───────────────────────────────────────
# CORE EXTRACTION
# ───────────────────────────────────────

def extract_text_range(
    document: List[Dict],
    start_id: str,
    end_id: Optional[str] = None
) -> str:
    flat = flatten_blocks(document)

    result = []
    collecting = False

    for block in flat:
        bid = str(block.get("id"))
        if bid is None:
            continue

        if end_id is None:
            if bid == start_id or bid.startswith(start_id + "."):
                text = render_block(block)
                if text.strip():  # <-- фильтруем пустые строки
                    result.append(text)
            continue

        if bid == start_id:
            collecting = True

        if collecting:
            text = render_block(block)
            if text.strip():  # <-- фильтруем пустые строки
                result.append(text)

        if collecting and bid == end_id:
            break

    return "\n\n".join(result).strip()


# ───────────────────────────────────────
# HELPERS
# ───────────────────────────────────────

def list_all_ids(document: List[Dict]) -> List[str]:
    return [
        str(b["id"])
        for b in flatten_blocks(document)
        if "id" in b
    ]


def load_yaml(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ───────────────────────────────────────
# PUBLIC API
# ───────────────────────────────────────

def extract_from_yaml(
    yaml_path: Path,
    start_id: str,
    end_id: Optional[str] = None
) -> str:
    data = load_yaml(yaml_path)
    return extract_text_range(data["document"], start_id, end_id)


def print_available_ids(yaml_path: Path):
    data = load_yaml(yaml_path)
    for i in list_all_ids(data["document"]):
        print(i)


# ───────────────────────────────────────
# EXAMPLE
# ───────────────────────────────────────

if __name__ == "__main__":
    path = Path("parsed_yaml/21 Chunking Strategies for RAG_20260204_171549.yaml")

    print("=== ALL IDS ===")
    print_available_ids(path)

    print("\n=== 4.1 ===")
    print(extract_from_yaml(path, "4.1"))

    print("\n=== 4 → 4.1.1.2 ===")
    print(extract_from_yaml(path, "4", "4.1.1.2"))

    print("\n=== 4.1 → 5.2.1 ===")
    print(extract_from_yaml(path, "4.1", "5.2.1"))
