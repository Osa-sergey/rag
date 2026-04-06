"""Pydantic schemas for YAML pipeline definitions.

Validates the structure of a YAML pipeline file:
    - Pipeline-level: name, config, metadata, steps
    - Step-level: module, config, depends_on, on_success, on_failure, on_retry
    - Graph: no cycles, valid depends_on references
"""
from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import BaseModel, Field, model_validator

from dagster_dsl.callbacks import CallbackConfig


# ── Step Schema ───────────────────────────────────────────────


class StepYaml(BaseModel):
    """Schema for a single step in the YAML pipeline.

    Example YAML::

        parse:
          module: document_parser.parse_csv
          defaults:                        # Hydra config imports (scenario switching)
            - embeddings: huggingface
            - stores@stores.qdrant: qdrant
          config:
            input_file: data/articles.csv
            output_dir: parsed_yaml
          depends_on: [download]
          provides: [parsed_yaml]          # context outputs for downstream
          requires: []                     # context inputs from upstream
          on_success:
            - log_result
          on_failure:
            - retry:
                max_attempts: 3
    """

    module: str = Field(..., description="Зарегистрированный шаг (module.command)")
    defaults: list[Any] = Field(
        default_factory=list,
        description="Hydra defaults — импорт конфигов (как в config.yaml defaults: секции)",
    )
    config: dict[str, Any] = Field(default_factory=dict, description="Step-level config overrides")
    outputs: dict[str, str] = Field(
        default_factory=dict,
        description="Декларация именованных выходов шага (output_name → type_hint)",
    )
    depends_on: list[str] = Field(default_factory=list, description="Список step_id зависимостей")
    inputs: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Входные данные из других шагов (param_name → ${{ steps.X.Y }} или литерал). "
            "Значения резолвятся в runtime и мержатся поверх config."
        ),
    )
    on_success: list[Any] = Field(default_factory=list, description="Callbacks при успехе")
    on_failure: list[Any] = Field(default_factory=list, description="Callbacks при ошибке")
    on_retry: list[Any] = Field(default_factory=list, description="Callbacks при повторе")

    def parsed_on_success(self) -> list[CallbackConfig]:
        return [CallbackConfig.from_yaml_item(item) for item in self.on_success]

    def parsed_on_failure(self) -> list[CallbackConfig]:
        return [CallbackConfig.from_yaml_item(item) for item in self.on_failure]

    def parsed_on_retry(self) -> list[CallbackConfig]:
        return [CallbackConfig.from_yaml_item(item) for item in self.on_retry]

    model_config = {"extra": "forbid"}


# ── Pipeline Schema ──────────────────────────────────────────


class PipelineYaml(BaseModel):
    """Root schema for a YAML pipeline definition.

    Example YAML::

        name: habr_full_pipeline
        config:
          stores.neo4j.uri: bolt://prod:7687
        metadata:
          owner: data-team
        steps:
          parse:
            module: document_parser.parse_csv
            config:
              input_file: data/articles.csv
          raptor:
            module: raptor_pipeline.run
            depends_on: [parse]
    """

    name: str = Field(..., description="Имя пайплайна")
    config: dict[str, Any] = Field(default_factory=dict, description="Глобальные config overrides")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Метаданные пайплайна")
    steps: dict[str, StepYaml] = Field(..., description="Шаги пайплайна (step_id → StepYaml)")

    @model_validator(mode="after")
    def validate_depends_on_references(self) -> "PipelineYaml":
        """Check that all depends_on entries reference existing step IDs."""
        step_ids = set(self.steps.keys())
        errors = []
        for step_id, step in self.steps.items():
            for dep in step.depends_on:
                if dep not in step_ids:
                    errors.append(
                        f"Step '{step_id}': depends_on '{dep}' — "
                        f"шаг не найден. Доступные: {sorted(step_ids)}"
                    )
        if errors:
            raise ValueError("\n".join(errors))
        return self

    @model_validator(mode="after")
    def validate_no_cycles(self) -> "PipelineYaml":
        """Check that the step graph has no cycles (topological sort)."""
        # Kahn's algorithm
        in_degree: dict[str, int] = {sid: 0 for sid in self.steps}
        adj: dict[str, list[str]] = {sid: [] for sid in self.steps}
        for step_id, step in self.steps.items():
            for dep in step.depends_on:
                adj[dep].append(step_id)
                in_degree[step_id] += 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            current = queue.pop(0)
            visited += 1
            for neighbor in adj[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited != len(self.steps):
            raise ValueError(
                f"Pipeline '{self.name}' содержит цикл в графе зависимостей! "
                f"Обработано {visited} из {len(self.steps)} шагов."
            )
        return self

    model_config = {"extra": "forbid"}
