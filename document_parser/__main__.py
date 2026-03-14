"""CLI entry point for Document Parser (Click + Hydra + Pydantic).

Architecture:
  Click handler (thin)  → parse CLI args, load config
  Business function     → calls existing document_parser logic

Usage:
    python -m document_parser --help
    python -m document_parser parse-csv --input-file articles.csv
    python -m document_parser parse-md --input-file note.md
    python -m document_parser list-ids --file parsed_yaml/986380.yaml
    python -m document_parser extract-text --file parsed_yaml/986380.yaml --start-id 4.1
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click

from cli_base import add_common_commands, load_config
from document_parser.schemas import DocumentParserConfig

# Force UTF-8 for Windows console
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

CONFIG_DIR = Path(__file__).parent / "conf"
CONFIG_NAME = "config"


# ══════════════════════════════════════════════════════════════
# Click group
# ══════════════════════════════════════════════════════════════

@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Подробный вывод (DEBUG)")
def cli(verbose: bool) -> None:
    """Document Parser — парсинг HTML/Markdown документов в структурированный YAML."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-7s  %(name)s: %(message)s",
    )


# ── validate / show-config (из cli_base) ──────────────────────
add_common_commands(cli, CONFIG_DIR, CONFIG_NAME, DocumentParserConfig)


# ══════════════════════════════════════════════════════════════
# parse-csv
# ══════════════════════════════════════════════════════════════

@cli.command("parse-csv")
@click.option("--input-file", "-f", required=True, help="CSV-файл с HTML-статьями")
@click.option("--output-dir", default=None, help="Директория для выходных YAML")
@click.option("--html-column", default=None, help="Колонка с HTML-контентом")
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def parse_csv(input_file, output_dir, html_column, override):
    """Парсинг CSV с HTML-статьями → структурированные YAML-файлы.

    \\b
    Примеры:
      python -m document_parser parse-csv -f articles.csv
      python -m document_parser parse-csv -f data.csv --html-column body_html
      python -m document_parser parse-csv -f data.csv --output-dir output/
    """
    overrides = {}
    if output_dir:
        overrides["output_dir"] = output_dir
    if html_column:
        overrides["html_column"] = html_column

    cfg = load_config(CONFIG_DIR, CONFIG_NAME, DocumentParserConfig,
                      overrides=override, **overrides)

    from document_parser.structurizer import process_csv

    csv_path = Path(input_file)
    out_dir = Path(cfg.output_dir)
    count = 0
    for result, out_file in process_csv(csv_path, html_column=cfg.html_column, output_dir=out_dir):
        article_id = result.get("article_id", "?")
        click.echo(f"  ✓ {article_id} → {out_file}")
        count += 1

    click.echo(f"\nОбработано статей: {count}")
    click.echo(f"Результаты в: {out_dir}")
    if count > 0:
        click.echo(f"\n💡 Для запуска raptor_pipeline:")
        click.echo(f"   python -m raptor_pipeline.main input_file={out_file.name}")


# ══════════════════════════════════════════════════════════════
# parse-md
# ══════════════════════════════════════════════════════════════

@cli.command("parse-md")
@click.option("--input-file", "-f", required=True, help="Markdown-файл для парсинга")
@click.option("--output-dir", default=None, help="Директория для выходного YAML")
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def parse_md(input_file, output_dir, override):
    """Парсинг Markdown-файла → структурированный YAML.

    \\b
    Примеры:
      python -m document_parser parse-md -f note.md
      python -m document_parser parse-md -f README.md --output-dir output/
    """
    overrides = {}
    if output_dir:
        overrides["output_dir"] = output_dir

    cfg = load_config(CONFIG_DIR, CONFIG_NAME, DocumentParserConfig,
                      overrides=override, **overrides)

    from document_parser.structurizer import process_md_file

    md_path = Path(input_file)
    out_dir = Path(cfg.output_dir)
    result, out_file = process_md_file(md_path, output_dir=out_dir)
    article_id = result.get("article_id", md_path.stem)
    n_blocks = len(result.get("document", []))
    click.echo(f"✓ {article_id} — {n_blocks} блоков → {out_file}")
    click.echo(f"Результат в: {out_dir}")
    click.echo(f"\n💡 Для запуска raptor_pipeline:")
    click.echo(f"   python -m raptor_pipeline.main input_file={out_file.name}")


# ══════════════════════════════════════════════════════════════
# extract-text
# ══════════════════════════════════════════════════════════════

@cli.command("extract-text")
@click.option("--file", "-f", "yaml_file", required=True, help="YAML-файл (результат парсинга)")
@click.option("--start-id", "-s", required=True, help="Начальный ID блока")
@click.option("--end-id", "-e", default=None, help="Конечный ID блока (опционально)")
def extract_text(yaml_file, start_id, end_id):
    """Извлечение текста из YAML-файла по диапазону ID.

    \\b
    Примеры:
      python -m document_parser extract-text -f parsed_yaml/986380.yaml -s 4.1
      python -m document_parser extract-text -f parsed_yaml/986380.yaml -s 4 -e 4.1.1.2
    """
    from document_parser.text_extractor import extract_from_yaml

    path = Path(yaml_file)
    text = extract_from_yaml(path, start_id, end_id)
    click.echo(text)


# ══════════════════════════════════════════════════════════════
# extract-assets
# ══════════════════════════════════════════════════════════════

@cli.command("extract-assets")
@click.option("--file", "-f", "yaml_file", default=None, help="YAML-файл (или все из output_dir)")
@click.option("--assets-dir", default=None, help="Директория для images/links YAML")
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def extract_assets(yaml_file, assets_dir, override):
    """Извлечение изображений и ссылок из YAML → отдельные YAML-файлы.

    \\b
    Примеры:
      python -m document_parser extract-assets -f parsed_yaml/986380.yaml
      python -m document_parser extract-assets --assets-dir output/assets
    """
    overrides = {}
    if assets_dir:
        overrides["assets_dir"] = assets_dir

    cfg = load_config(CONFIG_DIR, CONFIG_NAME, DocumentParserConfig,
                      overrides=override, **overrides)

    from document_parser.links_extractor import process_yaml_file

    out_dir = Path(cfg.assets_dir)

    if yaml_file:
        files = [Path(yaml_file)]
    else:
        input_dir = Path(cfg.output_dir)
        files = sorted(input_dir.glob("*.yaml"))
        if not files:
            click.echo(f"Нет YAML-файлов в {input_dir}")
            return

    for yf in files:
        images_path, links_path = process_yaml_file(yf, out_dir)
        click.echo(f"✓ {yf.name}")
        click.echo(f"  → images: {images_path.name}")
        click.echo(f"  → links:  {links_path.name}")


# ══════════════════════════════════════════════════════════════
# list-ids
# ══════════════════════════════════════════════════════════════

@cli.command("list-ids")
@click.option("--file", "-f", "yaml_file", required=True, help="YAML-файл")
def list_ids(yaml_file):
    """Вывод всех ID блоков из YAML-документа.

    \\b
    Примеры:
      python -m document_parser list-ids -f parsed_yaml/986380.yaml
    """
    from document_parser.utils import print_available_ids

    path = Path(yaml_file)
    print_available_ids(path)


# ══════════════════════════════════════════════════════════════
# check-ids
# ══════════════════════════════════════════════════════════════

@cli.command("check-ids")
@click.option("--file", "-f", "yaml_file", default=None, help="YAML-файл (или все из output_dir)")
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def check_ids(yaml_file, override):
    """Проверка последовательности ID в YAML-документе.

    \\b
    Примеры:
      python -m document_parser check-ids -f parsed_yaml/986380.yaml
      python -m document_parser check-ids
    """
    cfg = load_config(CONFIG_DIR, CONFIG_NAME, DocumentParserConfig,
                      overrides=override)

    from document_parser.utils import load_yaml, check_id_sequence

    if yaml_file:
        files = [Path(yaml_file)]
    else:
        input_dir = Path(cfg.output_dir)
        files = sorted(input_dir.glob("*.yaml"))
        if not files:
            click.echo(f"Нет YAML-файлов в {input_dir}")
            return

    ok_count = 0
    fail_count = 0
    for yf in files:
        data = load_yaml(yf)
        doc = data.get("document", [])
        is_ok = check_id_sequence(doc)
        status = "✓ OK" if is_ok else "✗ НАРУШЕНИЕ"
        click.echo(f"  {status}  {yf.name}")
        if is_ok:
            ok_count += 1
        else:
            fail_count += 1

    click.echo(f"\nИтого: {ok_count} OK, {fail_count} с нарушениями")


if __name__ == "__main__":
    cli()
