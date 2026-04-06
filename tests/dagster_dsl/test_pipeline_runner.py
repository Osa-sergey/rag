"""Tests for dagster_dsl.pipeline_runner — context propagation across steps."""
import pytest
from dataclasses import dataclass, field

from dagster_dsl.contexts import (
    StepContextRegistry,
    current_step_ctx,
    requires_step_context,
)
from dagster_dsl.pipeline_builder import PipelineBuilder
from dagster_dsl.pipeline_runner import run_pipeline
from dagster_dsl.steps import StepDefinition, StepRegistry, register_step


# ── Test Context Classes ──────────────────────────────────────


@dataclass
class ParseCtx:
    output_dir: str = ""
    files: list[str] = field(default_factory=list)


@dataclass
class RaptorCtx:
    indexed_count: int = 0


@dataclass
class TopicsCtx:
    topic_count: int = 0


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clean_registries():
    """Save and restore registries between tests."""
    step_reg = StepRegistry()
    saved_steps = dict(step_reg._steps)
    saved_ctx_vars = dict(StepContextRegistry._vars)
    step_reg.clear()
    yield
    step_reg._steps = saved_steps
    StepContextRegistry._vars = saved_ctx_vars


# ── Tests ─────────────────────────────────────────────────────


class TestRunPipelineContextPropagation:
    def test_downstream_sees_upstream_context(self):
        """Downstream step can read data from upstream step's context."""
        results = {}

        @register_step("test_parse.run", context_class=ParseCtx)
        def parse_step(**kwargs):
            ctx = current_step_ctx(ParseCtx)
            ctx.output_dir = "parsed/"
            ctx.files = ["a.yaml", "b.yaml"]
            return {"parsed": 2}

        @register_step("test_raptor.run")
        def raptor_step(**kwargs):
            # Read upstream ParseCtx
            parse = current_step_ctx(ParseCtx)
            results["raptor_saw_files"] = list(parse.files)
            results["raptor_saw_dir"] = parse.output_dir
            return {"indexed": len(parse.files)}

        builder = PipelineBuilder("test_pipe")
        p = builder.step("test_parse.run", step_id="parse")
        r = builder.step("test_raptor.run", step_id="raptor").after(p)

        run_results = run_pipeline(builder)

        assert results["raptor_saw_files"] == ["a.yaml", "b.yaml"]
        assert results["raptor_saw_dir"] == "parsed/"
        assert run_results["parse"] == {"parsed": 2}
        assert run_results["raptor"] == {"indexed": 2}

    def test_three_level_propagation(self):
        """Third step can see contexts from both first and second steps."""
        results = {}

        @register_step("lvl1.run", context_class=ParseCtx)
        def lvl1(**kwargs):
            ctx = current_step_ctx(ParseCtx)
            ctx.files = ["doc.yaml"]
            return "lvl1_done"

        @register_step("lvl2.run", context_class=RaptorCtx)
        def lvl2(**kwargs):
            # Can see ParseCtx from step 1
            parse = current_step_ctx(ParseCtx)
            ctx = current_step_ctx(RaptorCtx)
            ctx.indexed_count = len(parse.files) * 10
            return "lvl2_done"

        @register_step("lvl3.run")
        def lvl3(**kwargs):
            # Can see BOTH ParseCtx and RaptorCtx
            parse = current_step_ctx(ParseCtx)
            raptor = current_step_ctx(RaptorCtx)
            results["files"] = parse.files
            results["indexed"] = raptor.indexed_count
            return "lvl3_done"

        builder = PipelineBuilder("three_lvl")
        s1 = builder.step("lvl1.run", step_id="s1")
        s2 = builder.step("lvl2.run", step_id="s2").after(s1)
        s3 = builder.step("lvl3.run", step_id="s3").after(s2)

        run_pipeline(builder)

        assert results["files"] == ["doc.yaml"]
        assert results["indexed"] == 10

    def test_missing_context_raises(self):
        """Step with @requires_step_context fails if prerequisite not met."""

        @register_step("no_ctx.run")
        @requires_step_context(ParseCtx)
        def needs_parse(**kwargs):
            return "unreachable"

        builder = PipelineBuilder("fail_pipe")
        builder.step("no_ctx.run", step_id="s1")

        with pytest.raises(RuntimeError, match="ParseCtx"):
            run_pipeline(builder)

    def test_contexts_cleaned_up_after_run(self):
        """After run_pipeline completes, all custom contexts are deactivated."""

        @register_step("cleanup.run", context_class=ParseCtx)
        def cleanup_step(**kwargs):
            ctx = current_step_ctx(ParseCtx)
            ctx.output_dir = "test/"
            return "done"

        builder = PipelineBuilder("cleanup_pipe")
        builder.step("cleanup.run", step_id="s1")

        run_pipeline(builder)

        # Context should be deactivated after run_pipeline exits
        assert StepContextRegistry.has_active(ParseCtx) is False

    def test_parallel_deps_both_visible(self):
        """When two parallel steps both have contexts, a downstream sees both."""
        results = {}

        @register_step("par_raptor.run", context_class=RaptorCtx)
        def par_raptor(**kwargs):
            ctx = current_step_ctx(RaptorCtx)
            ctx.indexed_count = 42
            return "raptor_done"

        @register_step("par_topics.run", context_class=TopicsCtx)
        def par_topics(**kwargs):
            ctx = current_step_ctx(TopicsCtx)
            ctx.topic_count = 7
            return "topics_done"

        @register_step("par_concepts.run")
        def par_concepts(**kwargs):
            raptor = current_step_ctx(RaptorCtx)
            topics = current_step_ctx(TopicsCtx)
            results["indexed"] = raptor.indexed_count
            results["topics"] = topics.topic_count
            return "concepts_done"

        builder = PipelineBuilder("par_pipe")
        s_raptor = builder.step("par_raptor.run", step_id="raptor")
        s_topics = builder.step("par_topics.run", step_id="topics")
        s_concepts = builder.step("par_concepts.run", step_id="concepts").after(
            s_raptor, s_topics
        )

        run_pipeline(builder)

        assert results["indexed"] == 42
        assert results["topics"] == 7

    def test_pipeline_context_available(self):
        """Steps inside run_pipeline can access the pipeline context."""
        from dagster_dsl.contexts import current_pipeline

        results = {}

        @register_step("pipe_check.run")
        def pipe_check(**kwargs):
            pipe = current_pipeline()
            results["name"] = pipe.name
            results["overrides"] = dict(pipe.overrides)
            return "ok"

        builder = PipelineBuilder("my_named_pipe")
        builder._global_overrides["log_level"] = "DEBUG"
        builder.step("pipe_check.run", step_id="s1")

        run_pipeline(builder)

        assert results["name"] == "my_named_pipe"
        assert results["overrides"]["log_level"] == "DEBUG"

    def test_context_via_with_context_method(self):
        """StepRef.with_context() overrides registry's context_class."""
        results = {}

        @register_step("override_ctx.run")
        def override_step(**kwargs):
            ctx = current_step_ctx(RaptorCtx)
            ctx.indexed_count = 99
            results["value"] = ctx.indexed_count
            return "ok"

        builder = PipelineBuilder("override_pipe")
        builder.step("override_ctx.run", step_id="s1").with_context(RaptorCtx)

        run_pipeline(builder)

        assert results["value"] == 99
