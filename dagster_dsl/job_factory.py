"""Dagster job factory — translates PipelineBuilder DAG into Dagster ops/graph/job.

This module converts the declarative DSL description (PipelineBuilder)
into real Dagster definitions:

    PipelineBuilder
        ├── StepRef  →  @op (with config)
        ├── StepRef  →  @op (with config)
        └── dependencies  →  @graph → @job

Usage::

    from dagster_dsl import pipeline, to_dagster_job

    with pipeline("my_pipeline") as p:
        parse = p.step("document_parser.parse_csv", input_file="data.csv")
        raptor = p.step("raptor_pipeline.run").after(parse)

    job = to_dagster_job(p)
    # job is a dagster.JobDefinition
"""
from __future__ import annotations

import logging
from typing import Any, Optional

log = logging.getLogger(__name__)


def _make_op_fn(
    step_name: str,
    global_overrides: dict[str, Any],
    step_overrides: dict[str, Any],
    on_success: list | None = None,
    on_failure: list | None = None,
    on_retry: list | None = None,
):
    """Create a Python function body for a Dagster @op.

    The returned function:
      1. Merges global + step overrides
      2. Calls ``execute_step_with_callbacks()`` with retry/callback support
      3. Returns the result

    This is a factory that captures step_name, overrides, and callbacks via closure.
    """
    from dagster_dsl.steps import execute_step_with_callbacks
    from dagster_dsl.contexts import pipeline_context

    merged = {**global_overrides, **step_overrides}

    def op_fn(context, **inputs):
        """Dagster op body — executes a pipeline step."""
        context.log.info(f"Executing step: {step_name} with overrides: {merged}")

        with pipeline_context(name=context.job_name, **global_overrides):
            result = execute_step_with_callbacks(
                step_name,
                on_success=on_success,
                on_failure=on_failure,
                on_retry=on_retry,
                **step_overrides,
            )

        context.log.info(f"Step {step_name} completed")
        return result

    op_fn.__name__ = step_name.replace(".", "_")
    op_fn.__qualname__ = op_fn.__name__
    return op_fn


def to_dagster_job(builder, **job_kwargs: Any):
    """Translate a PipelineBuilder into a Dagster JobDefinition.

    Args:
        builder: A ``PipelineBuilder`` instance with declared steps.
        **job_kwargs: Extra kwargs passed to ``dagster.GraphDefinition.to_job()``.

    Returns:
        A ``dagster.JobDefinition`` ready to be executed.
    """
    try:
        from dagster import In, Nothing, OpDefinition, GraphDefinition, DependencyDefinition
    except ImportError:
        raise ImportError(
            "dagster is required for to_dagster_job(). "
            "Install it: pip install dagster dagster-webserver"
        )

    steps = builder.steps
    global_overrides = builder.global_overrides

    if not steps:
        raise ValueError(f"Pipeline '{builder.name}' has no steps.")

    # ── Create @op for each step ──────────────────────────────

    ops: dict[str, OpDefinition] = {}

    for step_id, step_ref in steps.items():
        # Determine input names from dependencies
        ins = {}
        if step_ref.depends_on:
            for dep_id in step_ref.depends_on:
                # Use Nothing type — we just need ordering, not data passing
                ins[dep_id] = In(Nothing)

        op_fn = _make_op_fn(
            step_name=step_ref.step_name,
            global_overrides=global_overrides,
            step_overrides=step_ref.overrides,
            on_success=step_ref.on_success_callbacks or None,
            on_failure=step_ref.on_failure_callbacks or None,
            on_retry=step_ref.on_retry_callbacks or None,
        )

        op_name = step_id  # use the unique step_id as op name

        op_def = OpDefinition(
            name=op_name,
            compute_fn=op_fn,
            ins=ins,
            description=f"Step: {step_ref.step_name}",
            tags={"module": step_ref.step_name.rsplit(".", 1)[0] if "." in step_ref.step_name else ""},
        )
        ops[step_id] = op_def

    # ── Build dependency dict ─────────────────────────────────

    # Dagster dependencies format:
    # {
    #     "op_name": {
    #         "input_name": DependencyDefinition("upstream_op_name"),
    #     }
    # }
    dep_dict: dict[str, dict[str, DependencyDefinition]] = {}

    for step_id, step_ref in steps.items():
        if step_ref.depends_on:
            dep_dict[step_id] = {}
            for dep_id in step_ref.depends_on:
                dep_dict[step_id][dep_id] = DependencyDefinition(dep_id)

    # ── Create graph → job ────────────────────────────────────

    graph_def = GraphDefinition(
        name=builder.name,
        node_defs=list(ops.values()),
        dependencies=dep_dict,
        description=f"Auto-generated from DSL pipeline '{builder.name}'",
    )

    job_def = graph_def.to_job(
        name=builder.name,
        tags=builder.metadata,
        **job_kwargs,
    )

    log.info(
        "Created Dagster job '%s' with %d ops: %s",
        builder.name,
        len(ops),
        ", ".join(ops.keys()),
    )

    return job_def
