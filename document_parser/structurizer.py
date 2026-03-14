import csv
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
from collections import defaultdict
import yaml

from markdownify import markdownify as md
from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

TERMINAL_INLINE = {"link", "image", "code_inline"}

INLINE_MARKS = {
    "strong": "bold",
    "em": "italic",
    "del": "strikethrough",
    "code_inline": "code",
}


# ───────────────────────────────────────
# HTML → Markdown AST
# ───────────────────────────────────────

def html_to_ast(html: str) -> SyntaxTreeNode:
    markdown = md(
        html,
        heading_style="ATX",
        strip=["script", "style"],
    )
    mdit = MarkdownIt()
    return SyntaxTreeNode(mdit.parse(markdown))

def md_to_ast(md_content: str) -> SyntaxTreeNode:
    """
    Преобразует Markdown (из Obsidian) в AST, совместимый с парсером ArticleParser.
    """
    mdit = MarkdownIt()
    return SyntaxTreeNode(mdit.parse(md_content))

def process_md_file(md_path: Path, output_dir: Path = Path("parsed_yaml")):
    """
    Парсинг Markdown-файла в ту же структуру, что и HTML, и сохранение в YAML.
    """
    output_dir.mkdir(exist_ok=True)

    content = md_path.read_text(encoding="utf-8")
    ast = md_to_ast(content)
    dump(ast)
    parser = ArticleParser()
    structured = parser.parse(ast)

    parsed_at = datetime.utcnow().isoformat()
    file_stem = md_path.stem
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = output_dir / f"{file_stem}_{timestamp}.yaml"

    result = {
        "article_id": file_stem,
        "parsed_at": parsed_at,
        "document": structured,
    }

    with filename.open("w", encoding="utf-8") as yf:
        yaml.dump(result, yf, allow_unicode=True, sort_keys=False)

    return result, filename

class ArticleParser:
    def __init__(self):
        self.section_stack = []  # стек открытых header'ов: {"level": int, "index": int}
        self.counters = defaultdict(int)
        self.blocks: list[dict] = []

    # -------------------------
    # INLINE
    # -------------------------
    def extract_text(self, node) -> str:
        if node.type == "text":
            return node.content or ""
        return "".join(self.extract_text(c) for c in node.children or [])

    def walk_inline(self, node):
        yield node
        if node.type in TERMINAL_INLINE:
            return
        for c in node.children or []:
            yield from self.walk_inline(c)

    def parse_inlines(self, node, marks=None, result=None):
        """
        Рекурсивный разбор inline AST с сохранением marks.
        """
        if node is None:
            return []

        if marks is None:
            marks = []

        if result is None:
            result = []

        # если это маркер — добавляем его в контекст
        new_marks = marks
        if node.type in INLINE_MARKS:
            new_marks = marks + [INLINE_MARKS[node.type]]

        # если это текст — создаём элемент
        if node.type == "text" and node.content.strip():
            order = len(result) + 1
            block = {
                "type": "text",
                "order": order,
                "text": node.content,
            }
            if new_marks:
                block["marks"] = new_marks
            result.append(block)

        # link — особый случай
        elif node.type == "link":
            order = len(result) + 1
            block = {
                "type": "link",
                "order": order,
                "href": node.attrs.get("href"),
                "text": self.extract_text(node),
            }
            if marks:
                block["marks"] = marks
            result.append(block)

        # image
        elif node.type == "image":
            order = len(result) + 1
            block = {
                "type": "image",
                "order": order,
                "src": node.attrs.get("src"),
                "alt": node.attrs.get("alt", ""),
            }
            if marks:
                block["marks"] = marks
            result.append(block)

        # рекурсивно обходим детей
        for child in node.children or []:
            self.parse_inlines(child, new_marks, result)

        return result


    # -------------------------
    # LIST
    # -------------------------
    def parse_list(self, node, path: list[int]) -> dict:
        items = []
        for idx, item in enumerate(node.children or [], 1):
            item_path = path + [idx]
            paragraphs = []
            nested_lists = []
            for child in item.children or []:
                match child.type:
                    case "paragraph":
                        inline = child.children[0] if child.children else None
                        paragraphs.append(self.parse_inlines(inline) if inline else [])
                    case "bullet_list" | "ordered_list":
                        nested_lists.append(self.parse_list(child, item_path))
            items.append({
                "id": ".".join(map(str, item_path)),
                "paragraphs": paragraphs,
                "lists": nested_lists,
            })
        return {"type": node.type, "items": items}

    # -------------------------
    # HEADER / ID
    # -------------------------
    def _next_id(self, level: int) -> str:
        """Генерация id с учётом текущего уровня вложенности"""
        # закрываем уровни >= level
        while self.section_stack and self.section_stack[-1]["level"] >= level:
            self.section_stack.pop()

        # родительский путь
        parent_path = [s["index"] for s in self.section_stack] if self.section_stack else []
        parent_key = ".".join(map(str, parent_path))
        self.counters[parent_key] += 1
        index = self.counters[parent_key]

        # сохраняем индекс в стек, если это header
        return ".".join(map(str, parent_path + [index])) if parent_path else str(index)

    # -------------------------
    # HANDLERS
    # -------------------------
    def handle_heading(self, node):
        opening_token = getattr(node.nester_tokens, "opening", None)
        level = 1
        if opening_token and opening_token.tag.startswith("h"):
            level = int(opening_token.tag[1])

        block_id = self._next_id(level)
        inline = node.children[0] if node.children else None
        block = {
            "id": block_id,
            "type": "header",
            "level": level,
            "children": self.parse_inlines(inline) if inline else []
        }

        # добавляем в стек header для генерации id следующих блоков
        self.section_stack.append({"level": level, "index": int(block_id.split(".")[-1])})

        self.blocks.append(block)

    def handle_paragraph(self, node):
        level = self.section_stack[-1]["level"] + 1 if self.section_stack else 1
        block_id = self._next_id(level)
        inline = node.children[0] if node.children else None
        block = {
            "id": block_id,
            "type": "paragraph",
            "children": self.parse_inlines(inline) if inline else []
        }
        self.blocks.append(block)

    def handle_list(self, node):
        level = self.section_stack[-1]["level"] + 1 if self.section_stack else 1
        block_id = self._next_id(level)
        parsed_list = self.parse_list(node, [int(x) for x in block_id.split(".")])
        block = {"id": block_id, "type": "list", "items": parsed_list}
        self.blocks.append(block)

    def handle_code(self, node):
        level = self.section_stack[-1]["level"] + 1 if self.section_stack else 1
        block_id = self._next_id(level)
        block = {
            "id": block_id,
            "type": "code",
            "lang": getattr(node, "info", None),
            "code": getattr(node, "content", None)
        }
        self.blocks.append(block)

    def handle_blockquote(self, node):
        level = self.section_stack[-1]["level"] + 1 if self.section_stack else 1
        block_id = self._next_id(level)
        children_blocks = []
        for child in node.children or []:
            match child.type:
                case "paragraph":
                    inline = child.children[0] if child.children else None
                    children_blocks.append({
                        "type": "paragraph",
                        "children": self.parse_inlines(inline) if inline else []
                    })
                case "heading":
                    inline = child.children[0] if child.children else None
                    children_blocks.append({
                        "type": "header",
                        "level": child.level,
                        "children": self.parse_inlines(inline) if inline else []
                    })
                case "bullet_list" | "ordered_list":
                    children_blocks.append(self.parse_list(child, []))
                case "code" | "fence":
                    children_blocks.append({
                        "type": "code",
                        "lang": getattr(child, "info", None),
                        "code": getattr(child, "content", None)
                    })
        block = {"id": block_id, "type": "blockquote", "children": children_blocks}
        self.blocks.append(block)

    def handle_image(self, node):
        level = self.section_stack[-1]["level"] + 1 if self.section_stack else 1
        block_id = self._next_id(level)
        block = {"id": block_id, "type": "image", "src": node.src, "alt": node.alt}
        self.blocks.append(block)

    def handle_link(self, node):
        level = self.section_stack[-1]["level"] + 1 if self.section_stack else 1
        block_id = self._next_id(level)
        block = {"id": block_id, "type": "link", "href": node.href, "text": node.text}
        self.blocks.append(block)

    # -------------------------
    # PARSE
    # -------------------------
    def parse(self, ast_nodes: list[Any]) -> list[dict]:
        for node in ast_nodes:
            match node.type:
                case "heading":
                    self.handle_heading(node)
                case "paragraph":
                    self.handle_paragraph(node)
                case "ordered_list" | "bullet_list":
                    self.handle_list(node)
                case "code" | "fence":
                    self.handle_code(node)
                case "blockquote":
                    self.handle_blockquote(node)
                case "image":
                    self.handle_image(node)
                case "link":
                    self.handle_link(node)
        return self.blocks


# ───────────────────────────────────────
# DEBUG TREE
# ───────────────────────────────────────

def dump(node, depth=0):
    indent = "  " * depth
    print(f"{indent}- {node.type}")
    for child in node.children or []:
        dump(child, depth + 1)


# ───────────────────────────────────────
# CSV PIPELINE
# ───────────────────────────────────────

def process_csv(csv_path: Path, html_column="content_html", output_dir: Path = Path("parsed_yaml")):
    output_dir.mkdir(exist_ok=True)  # создаём папку, если нет
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            html = row.get(html_column)
            if not html:
                continue

            ast = html_to_ast(html)
            dump(ast)
            article_id = row.get("id")
            print(article_id)
            
            parser = ArticleParser()
            structured = parser.parse(ast)
            parsed_at = datetime.utcnow().isoformat()

            result = {
                "article_id": article_id,
                "parsed_at": parsed_at,
                "document": structured,
            }

            # ───── формируем имя файла: articleid_YYYYMMDD_HHMMSS.yaml ─────
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            safe_id = article_id.replace("/", "_") if article_id else "unknown"
            filename = output_dir / f"{safe_id}_{timestamp}.yaml"

            with filename.open("w", encoding="utf-8") as yf:
                yaml.dump(result, yf, allow_unicode=True, sort_keys=False)

            yield result, filename


# ───────────────────────────────────────
# MAIN
# ───────────────────────────────────────

if __name__ == "__main__":
    #csv_path = Path("scrapped_articles_1.csv")
    #for doc in process_csv(csv_path):
    #    print(json.dumps(doc, ensure_ascii=False, indent=2))
    md_path = Path("/Users/seranovchinnikov/vault/project_live/zettelkasten/notes/21 Chunking Strategies for RAG.md")
    result = process_md_file(md_path)
    print(yaml.dump(result, allow_unicode=True, sort_keys=False))   
