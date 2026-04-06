"""CLI for dagster_dsl — pipeline inspection and validation tools.

Commands:
    inspect   — Show effective config for each step after merging
    validate  — Validate pipeline YAML (structure + step configs)
    list-steps — List all registered pipeline steps

Usage::

    python -m dagster_dsl.cli inspect dagster_dsl/examples/pipelines/habr_full.yaml
    python -m dagster_dsl.cli validate dagster_dsl/examples/pipelines/habr_full.yaml
    python -m dagster_dsl.cli list-steps

    # If installed as entry point:
    dagster-dsl inspect path/to/pipeline.yaml
    dagster-dsl inspect path/to/pipeline.yaml --step raptor
    dagster-dsl validate path/to/pipeline.yaml
"""
from __future__ import annotations

import sys
from pathlib import Path

import click


# ─────────────────────────────────────────────────────────────
# CLI group
# ─────────────────────────────────────────────────────────────


@click.group("dagster-dsl")
def cli() -> None:
    """🔧 dagster_dsl — pipeline DSL tools."""


# ─────────────────────────────────────────────────────────────
# inspect
# ─────────────────────────────────────────────────────────────


@cli.command("inspect")
@click.argument("pipeline_yaml", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--step", "-s",
    default=None,
    metavar="STEP_ID",
    help="Show only the specified step (by step_id). Default: all steps.",
)
@click.option(
    "--no-color", is_flag=True, default=False,
    help="Disable Rich colour output (plain text).",
)
@click.option(
    "--json", "as_json", is_flag=True, default=False,
    help="Output effective configs as JSON.",
)
def inspect_cmd(pipeline_yaml: Path, step: str | None, no_color: bool, as_json: bool) -> None:
    """Show effective (post-merge) config for each step in PIPELINE_YAML.

    For each step prints:
    \b
      • Keys inherited from global config (filtered to this step's schema)
      • Keys filtered out (not in schema)
      • Step-specific overrides
      • Final merged config (what Hydra will see)

    Example::

        dagster-dsl inspect habr_full.yaml
        dagster-dsl inspect habr_full.yaml --step raptor
        dagster-dsl inspect habr_full.yaml --json
    """
    # Register all module steps so registry is populated
    try:
        import dagster_dsl.module_steps  # noqa: F401
    except Exception:
        pass

    from dagster_dsl.yaml_loader import load_pipeline_dict
    from dagster_dsl.config_utils import (
        flat_to_nested,
        filter_global_for_schema,
        deep_merge,
        dict_to_hydra_overrides,
        inspect_pipeline_config,
        _format_dict,
    )
    from dagster_dsl.steps import StepRegistry

    import yaml as _yaml
    from pydantic import ValidationError
    from dagster_dsl.pipeline_schema import PipelineYaml
    from dagster_dsl.pipeline_builder import PipelineBuilder

    raw = _yaml.safe_load(pipeline_yaml.read_text(encoding="utf-8"))

    # For inspect we only need structural validation — skip Hydra config validation
    # (config validation is the job of `dagster-dsl validate`)
    try:
        pipeline_model = PipelineYaml.model_validate(raw)
    except ValidationError as e:
        click.secho(f"❌ Pipeline structure error:", fg="red", err=True)
        for err in e.errors():
            loc = " → ".join(str(x) for x in err["loc"])
            click.secho(f"   {loc}: {err['msg']}", fg="red", err=True)
        sys.exit(1)

    # Build PipelineBuilder directly from schema (skip Hydra validation)
    from dagster_dsl.callbacks import CallbackConfig
    builder = PipelineBuilder(pipeline_model.name)
    # Store nested config dict directly (config_override kwargs are flat only)
    if pipeline_model.config:
        builder._global_overrides.update(pipeline_model.config)
    if pipeline_model.metadata:
        builder.meta(**pipeline_model.metadata)

    step_refs: dict = {}
    for step_id, step_yaml in pipeline_model.steps.items():
        ref = builder.step(step_yaml.module, step_id=step_id, **step_yaml.config)
        ref.provides = list(step_yaml.provides)
        ref.requires = list(step_yaml.requires)
        ref.hydra_defaults = list(step_yaml.defaults)
        ref.on_success_callbacks = step_yaml.parsed_on_success()
        ref.on_failure_callbacks = step_yaml.parsed_on_failure()
        ref.on_retry_callbacks = step_yaml.parsed_on_retry()
        step_refs[step_id] = ref
    for step_id, step_yaml in pipeline_model.steps.items():
        if step_yaml.depends_on:
            step_refs[step_id].after(*[step_refs[d] for d in step_yaml.depends_on])

    if as_json:
        _print_as_json(builder, step)
        return

    if step is not None:
        # Single-step mode
        if step not in builder.steps:
            available = ", ".join(builder.steps.keys())
            click.secho(
                f"❌ Step '{step}' not found.\n   Available: {available}",
                fg="red", err=True,
            )
            sys.exit(1)
        _print_single_step(builder, step, no_color)
    else:
        # All steps
        inspect_pipeline_config(builder, use_rich=not no_color)


def _print_single_step(builder, step_id: str, no_color: bool) -> None:
    """Print the resolved config for a single step."""
    from dagster_dsl.config_utils import (
        flat_to_nested, filter_global_for_schema, deep_merge,
        dict_to_hydra_overrides, _format_dict,
    )
    from dagster_dsl.steps import StepRegistry

    registry = StepRegistry()
    global_nested = flat_to_nested(builder.global_overrides)
    step_ref = builder.steps[step_id]
    step_name = step_ref.step_name
    step_nested = flat_to_nested(step_ref.overrides)

    step_def = registry.get(step_name) if registry.has(step_name) else None
    schema_class = step_def.schema_class if step_def else None

    filtered_global = filter_global_for_schema(global_nested, schema_class) if schema_class else global_nested
    filtered_out = {k for k in global_nested if k not in filtered_global}
    merged = deep_merge(filtered_global, step_nested)
    overrides = dict_to_hydra_overrides(merged)

    lines = [
        f"{'─' * 60}",
        f"Step: {step_id}  [{step_name}]",
        f"Schema: {schema_class.__name__ if schema_class else '(none)'}",
    ]
    if step_ref.depends_on:
        lines.append(f"Depends on: {step_ref.depends_on}")
    if filtered_global:
        lines.append("\nFrom global (matched schema):")
        lines.append(_format_dict(filtered_global, indent=2, suffix=" [global]"))
    if filtered_out:
        lines.append("\nFiltered from global (not in schema):")
        for k in filtered_out:
            lines.append(f"  ✗ {k}")
    if step_nested:
        lines.append("\nStep-specific:")
        lines.append(_format_dict(step_nested, indent=2, suffix=" [step]"))
    lines.append("\nEffective config (Hydra overrides):")
    for o in overrides:
        lines.append(f"  {o}")

    text = "\n".join(lines)
    if no_color:
        click.echo(text)
    else:
        try:
            from rich.console import Console
            from rich.syntax import Syntax
            Console().print(Syntax(text, "text", theme="monokai", background_color="default"))
        except ImportError:
            click.echo(text)


def _print_as_json(builder, step_id: str | None) -> None:
    """Print effective configs as JSON."""
    import json
    from dagster_dsl.config_utils import flat_to_nested, filter_global_for_schema, deep_merge
    from dagster_dsl.steps import StepRegistry

    registry = StepRegistry()
    global_nested = flat_to_nested(builder.global_overrides)

    output: dict = {"pipeline": builder.name, "steps": {}}
    steps = {step_id: builder.steps[step_id]} if step_id else builder.steps

    for sid, ref in steps.items():
        step_def = registry.get(ref.step_name) if registry.has(ref.step_name) else None
        schema_class = step_def.schema_class if step_def else None
        filtered_global = filter_global_for_schema(global_nested, schema_class) if schema_class else global_nested
        merged = deep_merge(filtered_global, flat_to_nested(ref.overrides))
        output["steps"][sid] = {
            "module": ref.step_name,
            "schema": schema_class.__name__ if schema_class else None,
            "effective_config": merged,
        }

    click.echo(json.dumps(output, indent=2, default=str))


# ─────────────────────────────────────────────────────────────
# validate
# ─────────────────────────────────────────────────────────────


@cli.command("validate")
@click.argument("pipeline_yaml", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--skip-config", is_flag=True, default=False,
              help="Skip per-step config validation (only check structure).")
def validate_cmd(pipeline_yaml: Path, skip_config: bool) -> None:
    """Validate PIPELINE_YAML structure and per-step configs.

    Checks:
    \b
      1. YAML structure (name, steps, depends_on references, cycles)
      2. provides/requires context contracts
      3. Per-step config validity via Pydantic schemas (unless --skip-config)

    Example::

        dagster-dsl validate habr_full.yaml
        dagster-dsl validate habr_full.yaml --skip-config
    """
    try:
        import dagster_dsl.module_steps  # noqa: F401
    except Exception:
        pass

    import yaml as _yaml
    from pydantic import ValidationError
    from dagster_dsl.pipeline_schema import PipelineYaml

    raw = _yaml.safe_load(pipeline_yaml.read_text(encoding="utf-8"))

    click.echo(f"Validating: {pipeline_yaml}")

    # Step 1: structural
    try:
        PipelineYaml.model_validate(raw)
        click.secho("  ✅ Structure valid", fg="green")
    except ValidationError as e:
        click.secho("  ❌ Structure errors:", fg="red")
        for err in e.errors():
            loc = " → ".join(str(x) for x in err["loc"])
            click.secho(f"     {loc}: {err['msg']}", fg="red")
        sys.exit(1)

    if skip_config:
        click.secho("  ⏭  Config validation skipped (--skip-config)", fg="yellow")
        return

    # Step 2: full load with config validation
    from dagster_dsl.yaml_loader import load_pipeline_dict
    try:
        load_pipeline_dict(raw, source=str(pipeline_yaml))
        click.secho("  ✅ All step configs valid", fg="green")
        click.secho("\n✅ Pipeline is valid!", fg="green", bold=True)
    except ValueError as e:
        click.secho(f"  ❌ Config errors:\n{e}", fg="red")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
# list-steps
# ─────────────────────────────────────────────────────────────


@cli.command("list-steps")
@click.option("--module", "-m", default=None, metavar="MODULE",
              help="Filter by module prefix (e.g. raptor_pipeline).")
def list_steps_cmd(module: str | None) -> None:
    """List all registered pipeline steps.

    Example::

        dagster-dsl list-steps
        dagster-dsl list-steps --module raptor_pipeline
    """
    try:
        import dagster_dsl.module_steps  # noqa: F401
    except Exception:
        pass

    from dagster_dsl.steps import StepRegistry

    registry = StepRegistry()
    steps = registry.list_steps()

    if module:
        steps = [s for s in steps if s.startswith(module)]

    if not steps:
        click.secho("No steps registered." if not module else f"No steps for module '{module}'.",
                    fg="yellow")
        return

    click.echo(f"\nRegistered steps ({len(steps)}):\n")
    current_module = None
    for step_name in steps:
        mod = step_name.rsplit(".", 1)[0] if "." in step_name else step_name
        if mod != current_module:
            click.secho(f"  {mod}/", fg="cyan", bold=True)
            current_module = mod
        step_def = registry.get(step_name)
        desc = f"  — {step_def.description}" if step_def.description else ""
        schema = f" [{step_def.schema_class.__name__}]" if step_def.schema_class else " [no schema]"
        cmd = step_name.rsplit(".", 1)[1] if "." in step_name else step_name
        click.echo(f"    {cmd}{schema}{desc}")

    click.echo()


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for `dagster-dsl` console script."""
    cli()


if __name__ == "__main__":
    main()
