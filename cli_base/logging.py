"""Centralized logging setup: Rich console + structlog JSON file.

Usage in any __main__.py::

    from cli_base.logging import setup_logging, get_console
    setup_logging(level="INFO", log_file="logs/pipeline.jsonl")

Console output: Rich-rendered, colorful, human-readable.
File output:    One JSON object per line (structured, grep/jq-friendly).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import structlog
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from rich.panel import Panel
from rich.logging import RichHandler

# ── Singleton console ─────────────────────────────────────────

_console: Console | None = None


def get_console() -> Console:
    """Return a shared Rich Console (stderr, for log-friendly piping)."""
    global _console
    if _console is None:
        _console = Console(stderr=True, force_terminal=True)
    return _console


# ── setup_logging ─────────────────────────────────────────────

def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
) -> None:
    """Configure stdlib logging + structlog.

    Console → RichHandler (colorful, human-readable)
    File    → JSON lines via structlog (structured, machine-readable)

    Args:
        level:   Log level name (DEBUG / INFO / WARNING / ERROR / CRITICAL).
        log_file: Path to JSON log file. ``None`` = console only.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # ── stdlib handlers ───────────────────────────────────────
    handlers: list[logging.Handler] = []

    # Console handler (Rich)
    rich_handler = RichHandler(
        console=get_console(),
        show_path=False,
        show_time=True,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
        markup=True,
    )
    rich_handler.setLevel(numeric_level)
    handlers.append(rich_handler)

    # File handler (JSON lines)
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        # Formatting is done by structlog, set a passthrough formatter
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        handlers.append(file_handler)

    # Reset root logger
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(numeric_level)
    for h in handlers:
        root.addHandler(h)

    # Quiet noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "neo4j", "qdrant_client"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # ── structlog config ──────────────────────────────────────
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Attach structlog formatter to file handler for JSON output
    if log_file and len(handlers) > 1:
        json_formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
            foreign_pre_chain=shared_processors,
        )
        handlers[1].setFormatter(json_formatter)

    # Attach structlog formatter to Rich handler so structlog loggers work
    rich_formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        foreign_pre_chain=shared_processors,
    )
    rich_handler.setFormatter(rich_formatter)


# ── Output helpers ────────────────────────────────────────────

def print_table(
    title: str,
    columns: list[tuple[str, str]],
    rows: list[list[str]],
    *,
    caption: str | None = None,
) -> None:
    """Render a Rich table to the console.

    Args:
        title:   Table title.
        columns: List of (header, style) tuples.
        rows:    List of row lists (strings).
        caption: Optional caption below the table.
    """
    table = Table(title=title, caption=caption, show_lines=False)
    for header, style in columns:
        table.add_column(header, style=style)
    for row in rows:
        table.add_row(*row)
    get_console().print(table)


def print_yaml(data: dict | list, *, title: str = "YAML") -> None:
    """Render a dict/list as syntax-highlighted YAML."""
    import yaml
    yaml_str = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=False)
    get_console().print(Panel(syntax, title=title, border_style="blue"))


def print_config(cfg, *, title: str = "Configuration") -> None:
    """Render a Pydantic model or dict as highlighted YAML.

    Args:
        cfg: Pydantic BaseModel or plain dict.
        title: Panel title.
    """
    if hasattr(cfg, "model_dump"):
        data = cfg.model_dump(by_alias=True)
    elif hasattr(cfg, "dict"):
        data = cfg.dict()
    else:
        data = dict(cfg)
    print_yaml(data, title=title)
