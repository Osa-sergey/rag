"""YAML pipeline loader — reads YAML, validates, builds PipelineBuilder.

Main entry point: ``load_pipeline_yaml(path)`` — returns a PipelineBuilder
with all steps, dependencies, overrides, and callbacks configured.

Validation is two-level:
    1. Structural — YAML is validated against PipelineYaml Pydantic schema
    2. Per-step config — each step's config overrides are validated against
       the module's Pydantic schema (e.g. RaptorPipelineConfig) via Hydra compose
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, get_type_hints

import yaml
from pydantic import ValidationError

from dagster_dsl.callbacks import CallbackConfig
from dagster_dsl.pipeline_builder import PipelineBuilder
from dagster_dsl.pipeline_schema import PipelineYaml, StepYaml
from dagster_dsl.steps import StepRegistry

log = logging.getLogger(__name__)


# ── Public API ────────────────────────────────────────────────


def load_pipeline_yaml(path: str | Path) -> PipelineBuilder:
    """Load a YAML pipeline definition and return a PipelineBuilder.

    Steps:
        1. Read YAML file
        2. Validate structure via PipelineYaml (Pydantic)
        3. Validate each step's config against the module's Pydantic schema
        4. Build and return a PipelineBuilder with callbacks attached

    Args:
        path: Path to the YAML pipeline file.

    Returns:
        A fully configured PipelineBuilder.

    Raises:
        FileNotFoundError: If the YAML file doesn't exist.
        ValueError: On validation errors (with detailed messages).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Pipeline YAML не найден: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Pipeline YAML должен быть dict, получен: {type(raw).__name__}")

    return load_pipeline_dict(raw, source=str(path))


def load_pipeline_dict(raw: dict[str, Any], source: str = "<dict>") -> PipelineBuilder:
    """Load a pipeline from a parsed YAML dict.

    Useful for testing or programmatic pipeline creation.
    """
    # ── Step 1: Structural validation ──
    try:
        pipeline_yaml = PipelineYaml.model_validate(raw)
    except ValidationError as e:
        raise ValueError(
            f"Ошибка валидации pipeline ({source}):\n{_format_validation_errors(e)}"
        ) from e

    # ── Step 2: Validate registered steps exist ──
    registry = StepRegistry()
    step_errors: list[str] = []

    for step_id, step_yaml in pipeline_yaml.steps.items():
        if not registry.has(step_yaml.module):
            available = ", ".join(registry.list_steps()) or "(нет зарегистрированных)"
            step_errors.append(
                f"  Step '{step_id}': модуль '{step_yaml.module}' не зарегистрирован.\n"
                f"    Доступные: {available}"
            )

    if step_errors:
        raise ValueError(
            f"Ошибки в pipeline ({source}):\n" + "\n".join(step_errors)
        )

    # ── Step 3: Validate per-step configs ──
    config_errors: list[str] = []

    for step_id, step_yaml in pipeline_yaml.steps.items():
        step_def = registry.get(step_yaml.module)
        
        # Validate output references in config
        mocked_step_cfg, ref_errors = _validate_and_mock_output_refs(
            step_id=step_id,
            config=step_yaml.config,
            pipeline_yaml=pipeline_yaml,
            schema_class=step_def.schema_class if step_def else None,
        )
        config_errors.extend(ref_errors)

        # Validate output references in inputs (same rules)
        if step_yaml.inputs:
            _, input_ref_errors = _validate_and_mock_output_refs(
                step_id=step_id,
                config=step_yaml.inputs,
                pipeline_yaml=pipeline_yaml,
                schema_class=step_def.schema_class if step_def else None,
            )
            config_errors.extend(input_ref_errors)

        if step_def.schema_class and step_def.config_dir:
            errors = validate_step_config(
                step_id=step_id,
                step_name=step_yaml.module,
                global_overrides=pipeline_yaml.config,
                step_overrides=mocked_step_cfg,
                step_def=step_def,
            )
            config_errors.extend(errors)

    if config_errors:
        raise ValueError(
            f"Ошибки конфигурации шагов ({source}):\n" + "\n".join(config_errors)
        )

    # ── Step 4: Build PipelineBuilder ──
    builder = PipelineBuilder(pipeline_yaml.name)

    # Global overrides — store nested dict directly, not via config_override(**flat)
    if pipeline_yaml.config:
        builder._global_overrides.update(pipeline_yaml.config)

    # Metadata
    if pipeline_yaml.metadata:
        builder.meta(**pipeline_yaml.metadata)

    # Steps
    step_refs = {}
    for step_id, step_yaml in pipeline_yaml.steps.items():
        ref = builder.step(
            step_yaml.module,
            step_id=step_id,
            **step_yaml.config,
        )
        # Hydra defaults for config composition
        ref.hydra_defaults = list(step_yaml.defaults)
        # Attach callbacks
        ref.on_success_callbacks = step_yaml.parsed_on_success()
        ref.on_failure_callbacks = step_yaml.parsed_on_failure()
        ref.on_retry_callbacks = step_yaml.parsed_on_retry()
        # Attach outputs and inputs
        ref.outputs = step_yaml.outputs
        ref.inputs = dict(step_yaml.inputs)
        # Resolve context_class from StepRegistry (set via @register_step)
        if registry.has(step_yaml.module):
            step_def = registry.get(step_yaml.module)
            if step_def.context_class is not None:
                ref.context_class = step_def.context_class
        step_refs[step_id] = ref

    # Dependencies (second pass — all refs must exist)
    for step_id, step_yaml in pipeline_yaml.steps.items():
        if step_yaml.depends_on:
            deps = [step_refs[dep_id] for dep_id in step_yaml.depends_on]
            step_refs[step_id].after(*deps)

    log.info(
        "Loaded pipeline '%s' from %s: %d steps",
        pipeline_yaml.name, source, len(pipeline_yaml.steps),
    )

    return builder


# ── Per-Step Config Validation ────────────────────────────────


def validate_step_config(
    step_id: str,
    step_name: str,
    global_overrides: dict[str, Any],
    step_overrides: dict[str, Any],
    step_def: Any,
    hydra_defaults: list[Any] | None = None,
) -> list[str]:
    """Validate a step's config overrides against the module's Pydantic schema.

    Merges global + step overrides, loads config via Hydra compose,
    and validates against the schema. Returns list of error messages.

    If hydra_defaults is provided, they are prepended to the Hydra overrides
    to compose configs from the module's defaults groups (e.g. embeddings: huggingface).
    """
    errors: list[str] = []

    try:
        from cli_base.config_loader import load_config
        from dagster_dsl.config_utils import resolve_step_overrides

        hydra_overrides, _ = resolve_step_overrides(
            global_cfg=global_overrides,
            step_cfg=step_overrides,
            schema_class=step_def.schema_class,
        )

        load_config(
            config_dir=step_def.config_dir,
            config_name=step_def.config_name,
            schema_class=step_def.schema_class,
            overrides=tuple(hydra_overrides),
        )
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, "message"):
            error_msg = e.message
        errors.append(f"  Step '{step_id}' ({step_name}):\n    {error_msg}")

    return errors


# ── Helpers ───────────────────────────────────────────────────


def _format_validation_errors(exc: ValidationError) -> str:
    """Format Pydantic ValidationError into readable lines."""
    lines = []
    for err in exc.errors():
        loc = " → ".join(str(x) for x in err["loc"])
        msg = err["msg"]
        val = err.get("input", "?")
        lines.append(f"  {loc}: {msg} (получено: {val!r})")
    return "\n".join(lines)


def _validate_and_mock_output_refs(
    step_id: str,
    config: dict[str, Any],
    pipeline_yaml: PipelineYaml,
    schema_class: Any,
) -> tuple[dict[str, Any], list[str]]:
    """Walk config dict, validate ``${{ steps.id.key }}`` refs, return mocked config.

    Uses ``StepOutputRef`` to encapsulate parsing, type-checking, and mock
    value generation.  Parsed refs are embedded into the mocked config as
    ``StepOutputRef`` objects — ``pipeline_runner`` resolves them at runtime
    and re-validates the full config with Pydantic constraints.
    """
    from dagster_dsl.config_utils import _unwrap_type
    from dagster_dsl.output_ref import StepOutputRef

    errors: list[str] = []

    def _get_field_annotation(cls: Any, path: str) -> type | None:
        if cls is None:
            return None
        try:
            parts = path.split('.')
            current_cls = cls
            for part in parts:
                if not hasattr(current_cls, "__annotations__"):
                    return None
                hints = get_type_hints(current_cls)
                part_clean = part.split('[')[0]
                if part_clean not in hints:
                    return None
                ann = _unwrap_type(hints[part_clean])
                if hasattr(ann, "__annotations__"):
                    current_cls = ann
                else:
                    return ann
            return current_cls
        except Exception:
            return None

    def _walk(obj: Any, path: str = "") -> Any:
        if isinstance(obj, dict):
            return {k: _walk(v, f"{path}.{k}" if path else k) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_walk(v, f"{path}[{i}]") for i, v in enumerate(obj)]
        elif isinstance(obj, str):
            ref = StepOutputRef.parse_ref(obj)
            if ref is None:
                return obj

            # 1. Check if referenced step exists
            if ref.step_id not in pipeline_yaml.steps:
                errors.append(
                    f"  Step '{step_id}': Ссылка на неизвестный шаг "
                    f"'{ref.step_id}' в '{obj}'"
                )
                return obj

            # 2. Check if it's in depends_on
            current_step = pipeline_yaml.steps[step_id]
            if ref.step_id not in current_step.depends_on:
                errors.append(
                    f"  Step '{step_id}': Шаг '{ref.step_id}' "
                    f"должен быть в depends_on"
                )
                return obj

            # 3. Check if output key is declared
            ref_step = pipeline_yaml.steps[ref.step_id]
            if ref.output_key not in ref_step.outputs:
                errors.append(
                    f"  Step '{step_id}': Шаг '{ref.step_id}' "
                    f"не объявляет output '{ref.output_key}'"
                )
                return obj

            out_type = ref_step.outputs[ref.output_key]
            ref = ref.model_copy(update={"expected_type": out_type})

            # 4. Type compatibility check against target schema
            target_ann = _get_field_annotation(schema_class, path)
            if target_ann and not StepOutputRef.is_type_compatible(
                out_type, target_ann
            ):
                expected_name = getattr(
                    target_ann, "__name__", str(target_ann)
                )
                errors.append(
                    f"  Step '{step_id}': Несовпадение типов для '{path}'. "
                    f"Ожидается {expected_name}, получено {out_type} "
                    f"от '{obj}'"
                )

            # Return mock for Hydra validation; the StepRef stores the
            # original config string — runner will re-parse & resolve.
            return ref.mock_value()

        return obj

    mocked_cfg = _walk(config)
    return mocked_cfg, errors
