"""Standalone pipeline runner — executes pipeline steps with nested contexts.

Runs steps in topological order, nesting custom step contexts so that
downstream steps can access data from upstream steps via
``current_step_ctx(UpstreamContext)``.

Example::

    from dagster_dsl import load_pipeline_yaml, run_pipeline

    builder = load_pipeline_yaml("pipeline.yaml")
    results = run_pipeline(builder)
    # results == {"parse": {...}, "raptor": {...}, ...}

Context nesting (conceptual)::

    pipeline_context("habr_full")
      └─ custom_step_context(ParseContext)       ← step "parse" provides
           ├─ execute_step("parse")              ← fills ParseContext
           └─ custom_step_context(RaptorContext)  ← step "raptor" provides
                ├─ execute_step("raptor")         ← reads ParseContext
                └─ execute_step("concepts")       ← reads both
"""
from __future__ import annotations

import logging
from contextlib import ExitStack
from typing import Any

from dagster_dsl.contexts import custom_step_context, pipeline_context
from dagster_dsl.output_ref import StepOutputRef
from dagster_dsl.steps import StepRegistry, execute_step_with_callbacks

log = logging.getLogger(__name__)


def _resolve_runtime_outputs(
    config: dict[str, Any],
    results: dict[str, Any],
) -> dict[str, Any]:
    """Replace ``${{ steps.id.key }}`` strings with actual values from *results*.

    Uses ``StepOutputRef`` for parsing and resolution; the ref also performs
    a runtime type-check when resolving.
    """
    def _walk(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _walk(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_walk(v) for v in obj]
        elif isinstance(obj, str):
            ref = StepOutputRef.parse_ref(obj)
            if ref is not None:
                step_result = results.get(ref.step_id)
                if isinstance(step_result, dict) and ref.output_key in step_result:
                    return step_result[ref.output_key]
        return obj

    return _walk(config)


def _revalidate_config(
    step_name: str,
    step_id: str,
    resolved_overrides: dict[str, Any],
    global_overrides: dict[str, Any],
) -> None:
    """Re-validate resolved config against the step's Pydantic schema.

    This catches complex constraints (ge=, le=, cross-field validators)
    that could not be checked at load time because the values were refs.
    """
    registry = StepRegistry()
    if not registry.has(step_name):
        return
    step_def = registry.get(step_name)
    if step_def.schema_class is None or step_def.config_dir is None:
        return

    try:
        from cli_base.config_loader import load_config
        from dagster_dsl.config_utils import resolve_step_overrides

        hydra_overrides, _ = resolve_step_overrides(
            global_cfg=global_overrides,
            step_cfg=resolved_overrides,
            schema_class=step_def.schema_class,
        )
        load_config(
            config_dir=step_def.config_dir,
            config_name=step_def.config_name,
            schema_class=step_def.schema_class,
            overrides=tuple(hydra_overrides),
        )
    except Exception as e:
        raise ValueError(
            f"Ошибка валидации конфига шага '{step_id}' ({step_name}) "
            f"после подстановки ссылок: {e}"
        ) from e


def run_pipeline(builder, **extra_overrides: Any) -> dict[str, Any]:
    """Execute all pipeline steps in topological order with nested contexts.

    After resolving step-output references the config is **re-validated**
    against the module's Pydantic schema so that complex constraints
    (``ge=``, ``le=``, cross-field validators) are checked on real values.

    Args:
        builder: A ``PipelineBuilder`` instance.
        **extra_overrides: Additional global overrides.

    Returns:
        Dict mapping step_id → step result.

    Raises:
        RuntimeError: If a step's ``@requires_step_context`` prerequisite
                      is not satisfied.
        ValueError:   If re-validation after ref substitution fails.
    """
    global_overrides = {**builder.global_overrides, **extra_overrides}
    registry = StepRegistry()
    ordered_steps = builder.topology_sort()
    results: dict[str, Any] = {}

    with ExitStack() as stack:
        # Activate pipeline context
        pipe_ctx = stack.enter_context(
            pipeline_context(builder.name, **global_overrides)
        )

        for step_ref in ordered_steps:
            step_name = step_ref.step_name

            # Resolve context_class: StepRef > StepRegistry
            ctx_class = step_ref.context_class
            if ctx_class is None and registry.has(step_name):
                ctx_class = registry.get(step_name).context_class

            # Activate custom context BEFORE the step executes
            ctx_instance = None
            if ctx_class is not None:
                ctx_instance = ctx_class()
                stack.enter_context(custom_step_context(ctx_instance))
                log.debug(
                    "Activated %s for step '%s'",
                    ctx_class.__name__, step_ref.id,
                )

            # Resolve runtime outputs in config overrides
            resolved_overrides = _resolve_runtime_outputs(
                step_ref.overrides, results
            )

            # Resolve inputs and merge on top of config overrides
            # (inputs take precedence — they are explicit data flow)
            if step_ref.inputs:
                resolved_inputs = _resolve_runtime_outputs(
                    step_ref.inputs, results
                )
                resolved_overrides = {**resolved_overrides, **resolved_inputs}

            # Re-validate config with real values (constraints check)
            has_refs = (
                resolved_overrides != step_ref.overrides
                or step_ref.inputs
            )
            if has_refs:
                _revalidate_config(
                    step_name, step_ref.id,
                    resolved_overrides, global_overrides,
                )

            # Execute the step
            log.info("▶ Running step '%s' (%s)", step_ref.id, step_name)
            result = execute_step_with_callbacks(
                step_name,
                on_success=step_ref.on_success_callbacks or None,
                on_failure=step_ref.on_failure_callbacks or None,
                on_retry=step_ref.on_retry_callbacks or None,
                **resolved_overrides,
            )
            results[step_ref.id] = result
            log.info("✅ Step '%s' completed", step_ref.id)

    return results
