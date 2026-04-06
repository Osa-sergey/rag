"""Config merging, filtering, and inspection utilities for dagster_dsl.

Core functions:
    1. deep_merge()               — nested dict merge (override wins)
    2. flat_to_nested()           — "a.b.c" → {"a": {"b": {"c": ...}}}
    3. filter_global_for_schema() — drop global keys absent from step's Pydantic schema
    4. dict_to_hydra_overrides()  — nested dict → Hydra dot-notation strings
    5. resolve_step_overrides()   — full pipeline: filter → merge → hydra strings
    6. inspect_pipeline_config()  — Rich-colored display of per-step configs with source badges
"""
from __future__ import annotations

import logging
import types
import typing
from typing import Any, Optional, Type

from pydantic import BaseModel

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# 1. Deep merge
# ─────────────────────────────────────────────────────────────


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge two dicts. ``override`` wins on conflict.

    Example::

        base     = {"stores": {"neo4j": {"uri": "bolt://dev", "password": "dev"}}}
        override = {"stores": {"neo4j": {"password": "prod"}}, "log_level": "DEBUG"}
        result   = {"stores": {"neo4j": {"uri": "bolt://dev", "password": "prod"}},
                    "log_level": "DEBUG"}
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ─────────────────────────────────────────────────────────────
# 2. flat_to_nested
# ─────────────────────────────────────────────────────────────


def flat_to_nested(flat: dict[str, Any]) -> dict[str, Any]:
    """Convert a flat dot-notation dict to a nested dict.

    Example::

        flat_to_nested({"stores.neo4j.uri": "bolt://...", "log_level": "INFO"})
        # → {"stores": {"neo4j": {"uri": "bolt://..."}}, "log_level": "INFO"}

    Already-nested values (dict) under a top-level key are kept as-is.
    Mixed formats are supported.
    """
    nested: dict[str, Any] = {}
    for key, value in flat.items():
        if "." in key:
            parts = key.split(".")
            d = nested
            for part in parts[:-1]:
                if part not in d or not isinstance(d[part], dict):
                    d[part] = {}
                d = d[part]
            d[parts[-1]] = value
        else:
            if key in nested and isinstance(nested[key], dict) and isinstance(value, dict):
                nested[key] = deep_merge(nested[key], value)
            else:
                nested[key] = value
    return nested


# ─────────────────────────────────────────────────────────────
# 3. Schema-aware filtering
# ─────────────────────────────────────────────────────────────


def filter_global_for_schema(
    global_cfg: dict[str, Any],
    schema_class: Type[BaseModel],
) -> dict[str, Any]:
    """Return only the keys from ``global_cfg`` that exist in ``schema_class``.

    Prevents global config from leaking unknown keys into steps that
    don't define them (which would cause Hydra to error).

    Example::

        global = {"log_level": "INFO", "stores": {"neo4j": {"uri": "..."}}}

        # DocumentParserConfig has no 'stores' field → filtered out:
        filter_global_for_schema(global, DocumentParserConfig)
        # → {"log_level": "INFO"}

        # RaptorPipelineConfig HAS 'stores' → kept:
        filter_global_for_schema(global, RaptorPipelineConfig)
        # → {"log_level": "INFO", "stores": {"neo4j": {"uri": "..."}}}
    """
    return _filter_dict(global_cfg, schema_class)


def _filter_dict(cfg: dict[str, Any], schema: Type[BaseModel]) -> dict[str, Any]:
    schema_fields = schema.model_fields
    result: dict[str, Any] = {}
    for key, value in cfg.items():
        if key not in schema_fields:
            continue
        field_info = schema_fields[key]
        annotation = field_info.annotation
        if isinstance(value, dict) and annotation is not None:
            inner = _unwrap_type(annotation)
            if inner is not None and isinstance(inner, type) and issubclass(inner, BaseModel):
                value = _filter_dict(value, inner)
        result[key] = value
    return result


def _unwrap_type(annotation: Any) -> Any:
    """Unwrap Optional[X] → X, X | None → X, etc."""
    origin = getattr(annotation, "__origin__", None)
    if origin is typing.Union:
        args = [a for a in annotation.__args__ if a is not type(None)]
        return args[0] if len(args) == 1 else None
    if hasattr(types, "UnionType") and isinstance(annotation, types.UnionType):
        args = [a for a in annotation.__args__ if a is not type(None)]
        return args[0] if len(args) == 1 else None
    return annotation


# ─────────────────────────────────────────────────────────────
# 4. dict → Hydra override strings
# ─────────────────────────────────────────────────────────────


def dict_to_hydra_overrides(d: dict[str, Any], prefix: str = "") -> list[str]:
    """Convert a nested dict to a list of Hydra dot-notation override strings.

    Example::

        dict_to_hydra_overrides({
            "log_level": "INFO",
            "stores": {"neo4j": {"uri": "bolt://prod:7687"}},
            "tags": ["a", "b"],
        })
        # → ["log_level=INFO", "stores.neo4j.uri=bolt://prod:7687", "tags=[a,b]"]
    """
    parts: list[str] = []
    for key, value in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            parts.extend(dict_to_hydra_overrides(value, full_key))
        elif value is None:
            parts.append(f"{full_key}=null")
        elif isinstance(value, bool):
            parts.append(f"{full_key}={'true' if value else 'false'}")
        elif isinstance(value, (list, tuple)):
            items = ",".join(str(v) for v in value)
            parts.append(f"{full_key}=[{items}]")
        else:
            parts.append(f"{full_key}={value}")
    return parts


# ─────────────────────────────────────────────────────────────
# 5. Main resolution pipeline
# ─────────────────────────────────────────────────────────────


def resolve_step_overrides(
    global_cfg: dict[str, Any],
    step_cfg: dict[str, Any],
    schema_class: Optional[Type[BaseModel]] = None,
) -> tuple[list[str], dict[str, Any]]:
    """Compute the final effective config for a step.

    Pipeline:
        1. Normalize global_cfg (flat dot-notation → nested)
        2. Filter global_cfg to only keys known by the schema
        3. Deep merge filtered_global + step_cfg (step wins)
        4. Convert to Hydra override strings

    Args:
        global_cfg:   Pipeline-level config (may be flat or nested).
        step_cfg:     Step-level config (always included, not filtered).
        schema_class: Pydantic schema for this step. If None, no filtering.

    Returns:
        (hydra_overrides, merged_nested_dict)
    """
    global_nested = flat_to_nested(global_cfg)
    step_nested = flat_to_nested(step_cfg)

    if schema_class is not None:
        filtered_global = filter_global_for_schema(global_nested, schema_class)
        filtered_out = {k for k in global_nested if k not in filtered_global}
        if filtered_out:
            log.debug(
                "Global config keys filtered out for %s: %s",
                schema_class.__name__, sorted(filtered_out),
            )
    else:
        filtered_global = global_nested

    merged = deep_merge(filtered_global, step_nested)
    hydra_overrides = dict_to_hydra_overrides(merged)
    return hydra_overrides, merged


# ─────────────────────────────────────────────────────────────
# 6. Source annotation — tag each leaf with its origin
# ─────────────────────────────────────────────────────────────

_SRC_GLOBAL = "global"
_SRC_STEP = "step"
_SRC_BOTH = "step↑global"  # step overrides global

# Rich markup: (key_style, value_style, badge)
_RICH_STYLE: dict[str, tuple[str, str, str]] = {
    _SRC_GLOBAL: ("cyan",        "cyan",        "[dim cyan]← global[/dim cyan]"),
    _SRC_STEP:   ("green",       "green",       "[dim green]← step[/dim green]"),
    _SRC_BOTH:   ("bold yellow", "bold yellow", "[dim yellow]↑ step overrides global[/dim yellow]"),
}
_PLAIN_BADGE: dict[str, str] = {
    _SRC_GLOBAL: "← global",
    _SRC_STEP:   "← step",
    _SRC_BOTH:   "↑ step overrides global",
}


def _annotate_sources(
    merged: dict[str, Any],
    global_d: dict[str, Any],
    step_d: dict[str, Any],
) -> dict[str, Any]:
    """Return a parallel structure where every leaf is replaced by (value, source_tag).

    Source tags:
        "global"      — value came from global config only
        "step"        — value came from step config only
        "step↑global" — both had this key, step value wins
    """
    annotated: dict[str, Any] = {}
    for key, value in merged.items():
        in_global = key in global_d
        in_step = key in step_d

        if isinstance(value, dict):
            sub_g = global_d.get(key, {}) if in_global else {}
            sub_s = step_d.get(key, {}) if in_step else {}
            if not isinstance(sub_g, dict):
                sub_g = {}
            if not isinstance(sub_s, dict):
                sub_s = {}
            annotated[key] = _annotate_sources(value, sub_g, sub_s)
        else:
            if in_step and in_global:
                src = _SRC_BOTH
            elif in_step:
                src = _SRC_STEP
            else:
                src = _SRC_GLOBAL
            annotated[key] = (value, src)
    return annotated


def _render_annotated_rich(annotated: dict, indent: int = 4) -> str:
    """Render annotated dict as Rich markup with color-coded source badges."""
    lines: list[str] = []
    pad = " " * indent
    for key, value in annotated.items():
        if isinstance(value, dict):
            lines.append(f"{pad}[dim]{key}:[/dim]")
            lines.append(_render_annotated_rich(value, indent + 2))
        else:
            val, src = value
            key_s, val_s, badge = _RICH_STYLE[src]
            lines.append(f"{pad}[{key_s}]{key}[/{key_s}]: [{val_s}]{val}[/{val_s}] {badge}")
    return "\n".join(lines)


def _render_annotated_plain(annotated: dict, indent: int = 4) -> str:
    """Render annotated dict as plain text with source badges."""
    lines: list[str] = []
    pad = " " * indent
    for key, value in annotated.items():
        if isinstance(value, dict):
            lines.append(f"{pad}{key}:")
            lines.append(_render_annotated_plain(value, indent + 2))
        else:
            val, src = value
            lines.append(f"{pad}{key}: {val}  {_PLAIN_BADGE[src]}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# 7. Inspect utility
# ─────────────────────────────────────────────────────────────


def inspect_pipeline_config(builder: Any, *, use_rich: bool = True) -> str:
    """Display the effective (post-merge) config for every step in the pipeline.

    Each leaf key is annotated by its source:

        [cyan]   key: value  ← global          came from pipeline-level config
        [green]  key: value  ← step            step-specific override
        [yellow] key: value  ↑ step↑global     step value replaced the global value

    Args:
        builder:  A ``PipelineBuilder`` instance.
        use_rich: Use Rich for coloured terminal output (default True).

    Returns:
        Plain-text representation (also printed to stdout).
    """
    from dagster_dsl.steps import StepRegistry

    registry = StepRegistry()
    global_cfg = builder.global_overrides
    global_nested = flat_to_nested(global_cfg)

    rich_lines: list[str] = []
    plain_lines: list[str] = []

    def r(rich_str: str, plain_str: str | None = None) -> None:
        rich_lines.append(rich_str)
        plain_lines.append(plain_str if plain_str is not None else rich_str)

    legend = (
        "[cyan]■ global[/cyan]  "
        "[green]■ step[/green]  "
        "[bold yellow]■ step↑global[/bold yellow]"
    )
    legend_plain = "■ global  ■ step  ■ step↑global"

    r(f"[bold]{'═' * 62}[/bold]", "═" * 62)
    r(f"[bold]Pipeline:[/bold] [bold white]{builder.name}[/bold white]",
      f"Pipeline: {builder.name}")
    r(f"[bold]{'═' * 62}[/bold]", "═" * 62)
    r(f"  Legend: {legend}", f"  Legend: {legend_plain}")

    if global_nested:
        r("\n[dim]Global config:[/dim]", "\nGlobal config:")
        r(_format_dict(global_nested, indent=2))
    else:
        r("\n[dim]Global config:[/dim] (none)", "\nGlobal config: (none)")

    for step_id, step_ref in builder.steps.items():
        step_name = step_ref.step_name
        step_nested = flat_to_nested(step_ref.overrides)

        step_def = registry.get(step_name) if registry.has(step_name) else None
        schema_class = step_def.schema_class if step_def else None

        if schema_class is not None:
            filtered_global = filter_global_for_schema(global_nested, schema_class)
            filtered_out = [k for k in global_nested if k not in filtered_global]
        else:
            filtered_global = global_nested
            filtered_out = []

        merged = deep_merge(filtered_global, step_nested)
        annotated = _annotate_sources(merged, filtered_global, step_nested)
        n_overrides = len(dict_to_hydra_overrides(merged))
        schema_name = schema_class.__name__ if schema_class else "∅"

        r(f"\n[bold]{'─' * 62}[/bold]", "\n" + "─" * 62)
        r(
            f"[bold white]Step:[/bold white] [bold cyan]{step_id}[/bold cyan]"
            f"  [dim][[/dim][yellow]{step_name}[/yellow][dim]][/dim]"
            f"  [dim]{schema_name}[/dim]",
            f"Step: {step_id}  [{step_name}]  {schema_name}",
        )
        if step_ref.depends_on:
            r(f"  [dim]depends_on:[/dim] {step_ref.depends_on}",
              f"  depends_on: {step_ref.depends_on}")

        if filtered_out:
            f_rich = ", ".join(f"[dim red]{k}[/dim red]" for k in filtered_out)
            r(f"  [dim]Filtered (not in schema):[/dim] {f_rich}",
              f"  Filtered (not in schema): {', '.join(filtered_out)}")

        r(
            f"  [dim]── Effective config ({n_overrides} override(s)) ──[/dim]",
            f"  ── Effective config ({n_overrides} override(s)) ──",
        )
        if annotated:
            r(_render_annotated_rich(annotated, indent=4),
              _render_annotated_plain(annotated, indent=4))
        else:
            r("    [dim](no overrides — using module defaults)[/dim]",
              "    (no overrides — using module defaults)")

    r(f"\n[bold]{'═' * 62}[/bold]", "\n" + "═" * 62)

    plain_result = "\n".join(plain_lines)
    rich_markup = "\n".join(rich_lines)

    if use_rich:
        try:
            from rich.console import Console
            Console(highlight=False, force_terminal=True).print(rich_markup)
        except ImportError:
            print(plain_result)
    else:
        print(plain_result)

    return plain_result


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _format_dict(d: dict[str, Any], indent: int = 2, suffix: str = "") -> str:
    """Recursively format a nested dict as indented key: value lines (no color)."""
    lines: list[str] = []
    pad = " " * indent
    for key, value in d.items():
        if isinstance(value, dict):
            lines.append(f"{pad}{key}:")
            lines.append(_format_dict(value, indent + 2, suffix))
        else:
            lines.append(f"{pad}{key}: {value}{suffix}")
    return "\n".join(lines)
