"""Context-oriented DSL for orchestrating habr modules via Dagster.

Public API:
    pipeline()          – context manager to build a pipeline
    PipelineBuilder     – builder class for declaring steps & dependencies
    StepRef             – reference to a step in the graph
    to_dagster_job()    – translate builder into a Dagster @job

Example:
    from dagster_dsl import pipeline

    with pipeline("habr_full") as p:
        parse = p.step("document_parser.parse_csv",
                        input_file="data/articles.csv")
        raptor = p.step("raptor_pipeline.run").after(parse)

    job = p.to_dagster_job()
"""
from dagster_dsl.pipeline_builder import pipeline, PipelineBuilder, StepRef
from dagster_dsl.pipeline_runner import run_pipeline
from dagster_dsl.job_factory import to_dagster_job
from dagster_dsl.contexts import (
    PipelineContext,
    StepContext,
    StepContextRegistry,
    pipeline_context,
    step_context,
    custom_step_context,
    current_pipeline,
    current_step,
    current_step_ctx,
    requires_step_context,
)
from dagster_dsl.steps import StepDefinition, StepRegistry, register_step, execute_step_with_callbacks
from dagster_dsl.callbacks import CallbackConfig, CallbackRegistry, register_callback
from dagster_dsl.yaml_loader import load_pipeline_yaml, load_pipeline_dict
from dagster_dsl.pipeline_schema import PipelineYaml, StepYaml
from dagster_dsl.config_utils import (
    deep_merge,
    flat_to_nested,
    filter_global_for_schema,
    dict_to_hydra_overrides,
    resolve_step_overrides,
    inspect_pipeline_config,
)

__all__ = [
    # Builder DSL
    "pipeline",
    "PipelineBuilder",
    "StepRef",
    "to_dagster_job",
    "run_pipeline",
    # Context system
    "PipelineContext",
    "StepContext",
    "pipeline_context",
    "step_context",
    "current_pipeline",
    "current_step",
    # Custom step contexts (COP Layer 2)
    "StepContextRegistry",
    "custom_step_context",
    "current_step_ctx",
    "requires_step_context",
    # Step registry
    "StepDefinition",
    "StepRegistry",
    "register_step",
    "execute_step_with_callbacks",
    # YAML loader
    "load_pipeline_yaml",
    "load_pipeline_dict",
    "PipelineYaml",
    "StepYaml",
    # Callbacks
    "CallbackConfig",
    "CallbackRegistry",
    "register_callback",
]
