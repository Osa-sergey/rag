"""Step definitions for document_parser module.

Registered steps:
    document_parser.parse_csv   — Parse CSV with HTML articles → YAML
    document_parser.parse_md    — Parse Markdown file → YAML
    document_parser.extract_assets — Extract images/links from YAML
"""
from __future__ import annotations

from pathlib import Path

from dagster_dsl.steps import register_step
from document_parser.schemas import DocumentParserConfig

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "document_parser" / "conf"


@register_step(
    "document_parser.parse_csv",
    description="Парсинг CSV с HTML-статьями → структурированные YAML-файлы",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=DocumentParserConfig,
    tags={"module": "document_parser", "type": "parsing"},
)
def parse_csv_step(cfg):
    """Execute document_parser parse-csv logic."""
    from document_parser.schemas import DocumentParserConfig
    from document_parser.structurizer import process_csv

    csv_path = Path(cfg.input_file) if hasattr(cfg, "input_file") and cfg.input_file else None
    if csv_path is None:
        raise ValueError("input_file is required for document_parser.parse_csv")

    out_dir = Path(cfg.output_dir)
    results = []
    for result, out_file in process_csv(csv_path, html_column=cfg.html_column, output_dir=out_dir):
        article_id = result.get("article_id", "?")
        results.append({"article_id": article_id, "output_file": str(out_file)})

    return {"count": len(results), "files": results}


# Attach schema class for config loading
parse_csv_step.__step_schema__ = "document_parser.schemas.DocumentParserConfig"


@register_step(
    "document_parser.parse_md",
    description="Парсинг Markdown-файла → структурированный YAML",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=DocumentParserConfig,
    tags={"module": "document_parser", "type": "parsing"},
)
def parse_md_step(cfg):
    """Execute document_parser parse-md logic."""
    from document_parser.structurizer import process_md_file

    md_path = Path(cfg.input_file) if hasattr(cfg, "input_file") and cfg.input_file else None
    if md_path is None:
        raise ValueError("input_file is required for document_parser.parse_md")

    out_dir = Path(cfg.output_dir)
    result, out_file = process_md_file(md_path, output_dir=out_dir)
    return {
        "article_id": result.get("article_id", md_path.stem),
        "blocks": len(result.get("document", [])),
        "output_file": str(out_file),
    }


@register_step(
    "document_parser.extract_assets",
    description="Извлечение изображений и ссылок из YAML",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=DocumentParserConfig,
    tags={"module": "document_parser", "type": "extraction"},
)
def extract_assets_step(cfg):
    """Execute document_parser extract-assets logic."""
    from document_parser.links_extractor import process_yaml_file

    out_dir = Path(cfg.assets_dir)
    input_dir = Path(cfg.output_dir)
    files = sorted(input_dir.glob("*.yaml"))

    results = []
    for yf in files:
        images_path, links_path = process_yaml_file(yf, out_dir)
        results.append({
            "file": yf.name,
            "images": str(images_path),
            "links": str(links_path),
        })

    return {"count": len(results), "assets": results}
