"""Declarative pipeline builder — fluent Python DSL.

Provides a context-manager-based API for describing execution graphs:

    with pipeline("my_pipeline") as p:
        p.config_override("stores.neo4j.uri", "bolt://prod:7687")
        parse = p.step("document_parser.parse_csv", input_file="data.csv")
        raptor = p.step("raptor_pipeline.run").after(parse)
        topics = p.step("topic_modeler.train").after(parse)
        concepts = p.step("concept_builder.process").after(raptor, topics)

    job = p.to_dagster_job()   # translates the DAG into a Dagster @job

The builder stores the DAG internally as an adjacency list and delegates
Dagster translation to ``job_factory.to_dagster_job()``.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Optional


# ── StepRef ───────────────────────────────────────────────────


@dataclass
class StepRef:
    """Reference to a step in the pipeline DAG.

    Returned by ``PipelineBuilder.step()`` and supports chaining via
    ``.after()`` and ``.override()``.

    Attributes:
        id:         Unique step id within the pipeline (auto-generated).
        step_name:  Registry name (e.g. ``"raptor_pipeline.run"``).
        overrides:  Step-level Hydra overrides.
        depends_on: List of StepRef IDs this step depends on.
        provides:   Context tags this step creates (e.g. ["parsed_yaml"]).
        requires:   Context tags this step requires from upstream.
        hydra_defaults: Hydra defaults imports for config composition.
        on_success_callbacks: Callbacks invoked on success.
        on_failure_callbacks: Callbacks invoked on failure.
        on_retry_callbacks:   Callbacks invoked on retry.
    """

    id: str
    step_name: str
    overrides: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    hydra_defaults: list[Any] = field(default_factory=list)
    on_success_callbacks: list = field(default_factory=list)
    on_failure_callbacks: list = field(default_factory=list)
    on_retry_callbacks: list = field(default_factory=list)
    context_class: Optional[type] = None
    outputs: dict[str, str] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)

    def after(self, *deps: "StepRef") -> "StepRef":
        """Declare dependencies — this step runs after all ``deps``.

        Returns ``self`` for chaining::

            raptor = p.step("raptor_pipeline.run").after(parse)
        """
        for dep in deps:
            if dep.id not in self.depends_on:
                self.depends_on.append(dep.id)
        return self

    def override(self, **kv: Any) -> "StepRef":
        """Add step-level config overrides.

        Returns ``self`` for chaining::

            raptor = p.step("raptor_pipeline.run") \\
                      .override(input_dir="other/", max_concurrency=4)
        """
        self.overrides.update(kv)
        return self

    def input(self, **kv: Any) -> "StepRef":
        """Declare step inputs — values from upstream steps.

        These are resolved at runtime and merged on top of config overrides.
        In Python DSL, use ``${{ steps.X.Y }}`` strings or call with
        literal values for testing::

            raptor = p.step("raptor_pipeline.run") \\
                      .after(parse) \\
                      .input(input_dir="${{ steps.parse.output_dir }}")
        """
        self.inputs.update(kv)
        return self

    def on_success(self, *callbacks) -> "StepRef":
        """Add callbacks for success outcome."""
        self.on_success_callbacks.extend(callbacks)
        return self

    def on_failure(self, *callbacks) -> "StepRef":
        """Add callbacks for failure outcome."""
        self.on_failure_callbacks.extend(callbacks)
        return self

    def on_retry(self, *callbacks) -> "StepRef":
        """Add callbacks for retry outcome."""
        self.on_retry_callbacks.extend(callbacks)
        return self

    def with_context(self, ctx_class: type) -> "StepRef":
        """Declare the custom context class this step provides.

        Returns ``self`` for chaining::

            raptor = p.step("raptor_pipeline.run") \\
                      .with_context(RaptorContext)
        """
        self.context_class = ctx_class
        return self


# ── PipelineBuilder ───────────────────────────────────────────


class PipelineBuilder:
    """Builder for constructing a pipeline DAG declaratively.

    Usage::

        with pipeline("my_pipeline") as p:
            ...

        # Or without context manager:
        p = PipelineBuilder("my_pipeline")
        p.step(...)
        p.to_dagster_job()
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._global_overrides: dict[str, Any] = {}
        self._steps: dict[str, StepRef] = {}
        self._step_counter: int = 0
        self._metadata: dict[str, Any] = {}

    # ── Global config ─────────────────────────────────────────

    def config_override(self, *args: str, **kwargs: Any) -> "PipelineBuilder":
        """Set global Hydra overrides for the entire pipeline.

        Supports two calling styles::

            # Positional pairs:
            p.config_override(
                "stores.neo4j.uri", "bolt://prod:7687",
                "stores.qdrant.host", "prod-qdrant",
            )

            # Keyword arguments:
            p.config_override(input_dir="data/", log_level="INFO")

        Returns ``self`` for chaining.
        """
        # Positional: alternating key, value
        if args:
            if len(args) % 2 != 0:
                raise ValueError(
                    "config_override() positional args must be key-value pairs. "
                    f"Got {len(args)} args (odd number)."
                )
            for i in range(0, len(args), 2):
                self._global_overrides[args[i]] = args[i + 1]
        self._global_overrides.update(kwargs)
        return self

    def meta(self, **kv: Any) -> "PipelineBuilder":
        """Attach metadata to the pipeline (tags, owner, schedule, etc.)."""
        self._metadata.update(kv)
        return self

    # ── Step creation ─────────────────────────────────────────

    def step(self, step_name: str, *, step_id: Optional[str] = None, **overrides: Any) -> StepRef:
        """Add a step to the pipeline.

        Args:
            step_name: Registry name (e.g. ``"raptor_pipeline.run"``).
            step_id:   Optional custom id. Auto-generated if None.
            **overrides: Step-level config overrides.

        Returns:
            A ``StepRef`` that can be used in ``.after()`` calls.
        """
        if step_id is None:
            self._step_counter += 1
            # Derive a readable id: raptor_pipeline_run_1
            clean = step_name.replace(".", "_")
            step_id = f"{clean}_{self._step_counter}"

        ref = StepRef(id=step_id, step_name=step_name, overrides=overrides)
        self._steps[step_id] = ref
        return ref

    # ── Graph inspection ──────────────────────────────────────

    @property
    def steps(self) -> dict[str, StepRef]:
        """All declared steps, keyed by step_id."""
        return dict(self._steps)

    @property
    def global_overrides(self) -> dict[str, Any]:
        """Global Hydra overrides."""
        return dict(self._global_overrides)

    @property
    def metadata(self) -> dict[str, Any]:
        return dict(self._metadata)

    def topology_sort(self) -> list[StepRef]:
        """Return steps in topological order (Kahn's algorithm).

        Raises ``ValueError`` if the graph has cycles.
        """
        in_degree: dict[str, int] = {sid: 0 for sid in self._steps}
        for ref in self._steps.values():
            for dep_id in ref.depends_on:
                in_degree[ref.id] = in_degree.get(ref.id, 0)  # ensure exists
                in_degree[ref.id] += 1  # wrong! count in-edges not out-edges

        # Re-compute correctly
        in_degree = {sid: 0 for sid in self._steps}
        adj: dict[str, list[str]] = {sid: [] for sid in self._steps}
        for ref in self._steps.values():
            for dep_id in ref.depends_on:
                adj[dep_id].append(ref.id)
                in_degree[ref.id] += 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        result: list[StepRef] = []

        while queue:
            # Sort for deterministic order
            queue.sort()
            current = queue.pop(0)
            result.append(self._steps[current])
            for neighbor in adj[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self._steps):
            raise ValueError(
                f"Pipeline '{self.name}' contains a cycle! "
                f"Processed {len(result)} of {len(self._steps)} steps."
            )

        return result

    # ── Dagster integration ───────────────────────────────────

    def to_dagster_job(self, **job_kwargs: Any):
        """Translate the builder into a Dagster @job.

        Delegates to ``dagster_dsl.job_factory.to_dagster_job()``.
        """
        from dagster_dsl.job_factory import to_dagster_job

        return to_dagster_job(self, **job_kwargs)

    # ── String representation ─────────────────────────────────

    def __repr__(self) -> str:
        step_names = [f"{ref.step_name} ({ref.id})" for ref in self._steps.values()]
        return f"PipelineBuilder(name={self.name!r}, steps=[{', '.join(step_names)}])"

    def describe(self) -> str:
        """Human-readable description of the pipeline DAG."""
        lines = [f"Pipeline: {self.name}"]
        if self._global_overrides:
            lines.append(f"  Global overrides: {self._global_overrides}")
        lines.append(f"  Steps ({len(self._steps)}):")
        for ref in self.topology_sort():
            deps = f" ← [{', '.join(ref.depends_on)}]" if ref.depends_on else ""
            ovr = f" overrides={ref.overrides}" if ref.overrides else ""
            lines.append(f"    {ref.id}: {ref.step_name}{deps}{ovr}")
        return "\n".join(lines)


# ── Context Manager: pipeline() ──────────────────────────────


@contextmanager
def pipeline(name: str, **global_overrides: Any):
    """Context manager for building a pipeline declaratively.

    Example::

        with pipeline("habr_full") as p:
            parse = p.step("document_parser.parse_csv", input_file="data.csv")
            raptor = p.step("raptor_pipeline.run").after(parse)
        job = p.to_dagster_job()

    Yields a ``PipelineBuilder`` instance.
    """
    builder = PipelineBuilder(name)
    if global_overrides:
        builder.config_override(**global_overrides)
    yield builder
