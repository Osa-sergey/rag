"""Step registry and execution engine.

Each step is a wrapper around an existing module's business logic.
Steps are registered globally and can be looked up by ``module.command``
name (e.g. ``"raptor_pipeline.run"``).

A step execution:
  1. Merges pipeline-level + step-level Hydra overrides
  2. Loads config via ``cli_base.load_config``
  3. Creates DI container (if module uses one)
  4. Calls the business function
  5. Returns the result
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel

from dagster_dsl.contexts import (
    StepContextRegistry,
    current_pipeline,
    current_step,
    custom_step_context,
    pipeline_context,
    requires_context,
    step_context,
)

log = logging.getLogger(__name__)


# ── Step Definition ───────────────────────────────────────────


@dataclass
class StepDefinition:
    """Metadata and executor for a single pipeline step.

    Attributes:
        name:           Fully qualified name ``module.command`` (e.g. ``raptor_pipeline.run``).
        description:    Human-readable description shown in Dagster UI.
        module_name:    Python module name (e.g. ``raptor_pipeline``).
        command_name:   Command within the module (e.g. ``run``).
        config_dir:     Path to the Hydra config directory.
        config_name:    Hydra config file name (without .yaml).
        schema_class:   Pydantic model class for validation.
        execute_fn:     Callable that receives ``(cfg, **step_overrides)`` and runs the business logic.
        tags:           Arbitrary tags for grouping / filtering.
    """

    name: str
    description: str = ""
    module_name: str = ""
    command_name: str = ""
    config_dir: Optional[Path] = None
    config_name: str = "config"
    schema_class: Optional[Type[BaseModel]] = None
    execute_fn: Optional[Callable[..., Any]] = None
    tags: dict[str, str] = field(default_factory=dict)
    context_class: Optional[type] = None
    requires_contexts: list[type] = field(default_factory=list)

    def __post_init__(self) -> None:
        if "." in self.name and not self.module_name:
            parts = self.name.rsplit(".", 1)
            self.module_name = parts[0]
            self.command_name = parts[1]


# ── Step Registry (singleton) ────────────────────────────────


class StepRegistry:
    """Global registry of available steps.

    Steps are registered at import time via ``@register_step`` or
    ``StepRegistry.register()``.
    """

    _instance: Optional["StepRegistry"] = None
    _steps: dict[str, StepDefinition]

    def __new__(cls) -> "StepRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._steps = {}
        return cls._instance

    def register(self, step_def: StepDefinition) -> None:
        """Register a step definition."""
        self._steps[step_def.name] = step_def
        log.debug("Registered step: %s", step_def.name)

    def get(self, name: str) -> StepDefinition:
        """Retrieve a step by name. Raises ``KeyError`` if not found."""
        if name not in self._steps:
            available = ", ".join(sorted(self._steps)) or "(none)"
            raise KeyError(
                f"Step '{name}' не зарегистрирован. "
                f"Доступные шаги: {available}"
            )
        return self._steps[name]

    def list_steps(self) -> list[str]:
        """List all registered step names."""
        return sorted(self._steps.keys())

    def has(self, name: str) -> bool:
        """Check if a step is registered."""
        return name in self._steps

    def clear(self) -> None:
        """Clear all registrations (for testing)."""
        self._steps.clear()

    def __contains__(self, name: str) -> bool:
        return name in self._steps

    def __len__(self) -> int:
        return len(self._steps)


def register_step(
    name: str,
    *,
    description: str = "",
    config_dir: Optional[Path] = None,
    config_name: str = "config",
    schema_class: Optional[Type[BaseModel]] = None,
    tags: Optional[dict[str, str]] = None,
    context_class: Optional[type] = None,
    requires_contexts: Optional[list[type]] = None,
):
    """Decorator to register a function as a pipeline step.

    Args:
        context_class:      Custom context class this step PROVIDES.
        requires_contexts:  List of context classes this step REQUIRES
                            from upstream steps.

    Example::

        @register_step(
            "raptor_pipeline.run",
            context_class=RaptorContext,
            requires_contexts=[ParseContext],
        )
        def raptor_run(cfg):
            parse = current_step_ctx(ParseContext)  # guaranteed
            ...
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        step_def = StepDefinition(
            name=name,
            description=description,
            config_dir=config_dir,
            config_name=config_name,
            schema_class=schema_class,
            execute_fn=fn,
            tags=tags or {},
            context_class=context_class,
            requires_contexts=requires_contexts or [],
        )
        StepRegistry().register(step_def)
        return fn

    return decorator


# ── Step Execution ────────────────────────────────────────────


def execute_step(step_name: str, **step_overrides: Any) -> Any:
    """Execute a registered step within the current pipeline context.

    1. Looks up the step in the registry
    2. Merges pipeline overrides + step overrides
    3. Loads config via Hydra + validates with Pydantic
    4. Calls the step's execute_fn
    5. Returns the result

    Can be called standalone (outside pipeline context) — in that case
    only step_overrides are used.
    """
    registry = StepRegistry()
    step_def = registry.get(step_name)

    if step_def.execute_fn is None:
        raise RuntimeError(
            f"Step '{step_name}' has no execute_fn. "
            f"Register it with @register_step or set execute_fn manually."
        )

    # Resolve effective config: filter global by schema, deep merge with step overrides
    from dagster_dsl.config_utils import resolve_step_overrides

    global_cfg: dict[str, Any] = {}
    try:
        pipeline_ctx = current_pipeline()
        global_cfg = pipeline_ctx.overrides
    except RuntimeError:
        pass  # No pipeline context — standalone execution

    hydra_overrides, merged_nested = resolve_step_overrides(
        global_cfg=global_cfg,
        step_cfg=step_overrides,
        schema_class=step_def.schema_class,
    )

    # Load config via Hydra + Pydantic
    cfg = None
    if step_def.schema_class and step_def.config_dir:
        from cli_base.config_loader import load_config

        cfg = load_config(
            config_dir=step_def.config_dir,
            config_name=step_def.config_name,
            schema_class=step_def.schema_class,
            overrides=tuple(hydra_overrides),
        )

    # Check that required custom step contexts (prerequisites) are active.
    # Merge from two sources: @requires_step_context decorator + StepDefinition.requires_contexts
    decorator_ctxs = getattr(step_def.execute_fn, "_required_step_contexts", ())
    all_required = list(dict.fromkeys(list(step_def.requires_contexts) + list(decorator_ctxs)))
    if all_required:
        missing = [
            cls.__name__ for cls in all_required
            if not StepContextRegistry.has_active(cls)
        ]
        if missing:
            raise RuntimeError(
                f"❌ Шаг '{step_name}' требует контексты шагов: "
                f"{', '.join(c.__name__ for c in all_required)}.\n"
                f"   Отсутствуют: {', '.join(missing)}.\n"
                f"   Выполните шаги-prerequisites, предоставляющие эти контексты."
            )

    # Execute within step context + optional custom context
    with step_context(step_name, **step_overrides):
        # If step has a custom context_class AND it's not already active
        # (i.e. not managed by run_pipeline), activate it here (standalone mode)
        need_ctx = (
            step_def.context_class is not None
            and not StepContextRegistry.has_active(step_def.context_class)
        )

        if need_ctx:
            ctx_instance = step_def.context_class()
            with custom_step_context(ctx_instance):
                if cfg is not None:
                    return step_def.execute_fn(cfg)
                else:
                    return step_def.execute_fn(**merged_nested)
        else:
            if cfg is not None:
                return step_def.execute_fn(cfg)
            else:
                return step_def.execute_fn(**merged_nested)


def execute_step_with_callbacks(
    step_name: str,
    on_success: list | None = None,
    on_failure: list | None = None,
    on_retry: list | None = None,
    **step_overrides: Any,
) -> Any:
    """Execute a step with callback handling for outcomes.

    Wraps ``execute_step()`` with:
      - on_success callbacks after successful completion
      - on_failure callbacks on exception
      - retry logic (if 'retry' callback is in on_failure)
    """
    import time
    from dagster_dsl.callbacks import execute_callbacks, get_retry_config, CallbackConfig

    on_success = on_success or []
    on_failure = on_failure or []
    on_retry = on_retry or []

    # Check for retry config
    retry_cfg = get_retry_config(on_failure)
    max_attempts = retry_cfg["max_attempts"] if retry_cfg else 1
    delay = retry_cfg["delay"] if retry_cfg else 0

    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = execute_step(step_name, **step_overrides)

            # Success callbacks
            execute_callbacks(on_success, step_name, "success", result)
            return result

        except Exception as e:
            last_error = e
            log.warning(
                "Step '%s' failed (attempt %d/%d): %s",
                step_name, attempt, max_attempts, e,
            )

            if attempt < max_attempts:
                # Retry callbacks
                execute_callbacks(on_retry, step_name, "retry", e)
                log.info("Retrying '%s' in %ds...", step_name, delay)
                time.sleep(delay)
            else:
                # Final failure callbacks
                execute_callbacks(on_failure, step_name, "failure", e)

    raise last_error  # type: ignore[misc]
