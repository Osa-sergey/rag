"""Tests for dagster_dsl.contexts — COP context system."""
import pytest
from dataclasses import dataclass

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
    requires_context,
    requires_step_context,
)


# ── PipelineContext ───────────────────────────────────────────


class TestPipelineContext:
    def test_activation(self):
        """Pipeline context is accessible inside the context manager."""
        with pipeline_context("test_pipeline", input_dir="data/"):
            ctx = current_pipeline()
            assert ctx.name == "test_pipeline"
            assert ctx.overrides["input_dir"] == "data/"

    def test_yields_context(self):
        """Pipeline context manager yields the context object."""
        with pipeline_context("test_pipeline", key="val") as ctx:
            assert isinstance(ctx, PipelineContext)
            assert ctx.name == "test_pipeline"
            assert ctx is current_pipeline()

    def test_deactivation(self):
        """Pipeline context is not accessible outside the context manager."""
        with pipeline_context("test"):
            pass  # active inside
        with pytest.raises(RuntimeError, match="Нет активного PipelineContext"):
            current_pipeline()

    def test_nested_contexts(self):
        """Inner pipeline context overrides outer."""
        with pipeline_context("outer", log_level="INFO"):
            assert current_pipeline().name == "outer"
            with pipeline_context("inner", log_level="DEBUG"):
                ctx = current_pipeline()
                assert ctx.name == "inner"
                assert ctx.overrides["log_level"] == "DEBUG"
            # Outer restored
            assert current_pipeline().name == "outer"
            assert current_pipeline().overrides["log_level"] == "INFO"

    def test_set_override(self):
        ctx = PipelineContext(name="test")
        ctx.set_override("key", "value")
        assert ctx.overrides["key"] == "value"

    def test_set_overrides_batch(self):
        ctx = PipelineContext(name="test")
        ctx.set_overrides(a=1, b=2)
        assert ctx.overrides == {"a": 1, "b": 2}


# ── StepContext ───────────────────────────────────────────────


class TestStepContext:
    def test_activation(self):
        with step_context("raptor_pipeline.run", input_dir="data/"):
            ctx = current_step()
            assert ctx.step_name == "raptor_pipeline.run"
            assert ctx.module == "raptor_pipeline"
            assert ctx.command == "run"

    def test_yields_context(self):
        """Step context manager yields the context object."""
        with step_context("raptor_pipeline.run", key="val") as ctx:
            assert isinstance(ctx, StepContext)
            assert ctx.step_name == "raptor_pipeline.run"
            assert ctx is current_step()

    def test_deactivation(self):
        with step_context("test.step"):
            pass
        with pytest.raises(RuntimeError, match="Нет активного StepContext"):
            current_step()

    def test_module_command_parsing(self):
        ctx = StepContext(step_name="topic_modeler.train")
        assert ctx.module == "topic_modeler"
        assert ctx.command == "train"

    def test_merged_overrides_with_pipeline(self):
        """Step overrides merge with pipeline overrides (step wins)."""
        with pipeline_context("p", log_level="INFO", input_dir="global/"):
            ctx = StepContext(
                step_name="test.step",
                overrides={"input_dir": "step/", "extra_key": "val"},
            )
            merged = ctx.merged_overrides
            assert merged["log_level"] == "INFO"  # from pipeline
            assert merged["input_dir"] == "step/"  # step wins
            assert merged["extra_key"] == "val"

    def test_merged_overrides_without_pipeline(self):
        """Without pipeline context, only step overrides are used."""
        ctx = StepContext(step_name="test.step", overrides={"key": "val"})
        assert ctx.merged_overrides == {"key": "val"}


# ── @requires_context ─────────────────────────────────────────


class TestRequiresContext:
    def test_success_with_context(self):
        @requires_context("pipeline")
        def guarded_fn():
            return "ok"

        with pipeline_context("test"):
            assert guarded_fn() == "ok"

    def test_failure_without_context(self):
        @requires_context("pipeline")
        def guarded_fn():
            return "ok"

        with pytest.raises(RuntimeError, match="требует контексты: pipeline"):
            guarded_fn()

    def test_multiple_contexts_required(self):
        @requires_context("pipeline", "step")
        def guarded_fn():
            return "ok"

        # Missing both
        with pytest.raises(RuntimeError, match="pipeline.*step"):
            guarded_fn()

        # Missing step
        with pipeline_context("test"):
            with pytest.raises(RuntimeError, match="step"):
                guarded_fn()

        # Both present
        with pipeline_context("test"):
            with step_context("test.step"):
                assert guarded_fn() == "ok"

    def test_decorator_preserves_metadata(self):
        @requires_context("pipeline")
        def my_function():
            """My docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."
        assert my_function._required_contexts == ("pipeline",)


# ══════════════════════════════════════════════════════════════
# Custom Step Contexts (COP Layer 2)
# ══════════════════════════════════════════════════════════════


@dataclass
class AlphaContext:
    """Test custom context A."""
    value: str = "alpha"
    processed: bool = False


@dataclass
class BetaContext:
    """Test custom context B."""
    count: int = 0
    ready: bool = False


@pytest.fixture(autouse=True)
def clean_step_context_registry():
    """Clear custom step context registry between tests."""
    saved = dict(StepContextRegistry._vars)
    yield
    StepContextRegistry._vars = saved


class TestCustomStepContext:
    def test_activation_via_yield(self):
        """Custom context is accessible via the yielded value."""
        with custom_step_context(AlphaContext(value="test")) as ctx:
            assert ctx.value == "test"
            assert isinstance(ctx, AlphaContext)

    def test_activation_via_accessor(self):
        """Custom context is accessible via current_step_ctx()."""
        with custom_step_context(AlphaContext(value="hello")):
            ctx = current_step_ctx(AlphaContext)
            assert ctx.value == "hello"
            assert isinstance(ctx, AlphaContext)

    def test_yield_and_accessor_same_object(self):
        """Yielded context and accessor return the same instance."""
        with custom_step_context(AlphaContext()) as yielded:
            accessed = current_step_ctx(AlphaContext)
            assert yielded is accessed

    def test_deactivation(self):
        """Custom context is not accessible outside the with block."""
        with custom_step_context(AlphaContext()):
            pass
        with pytest.raises(RuntimeError, match="Нет активного контекста AlphaContext"):
            current_step_ctx(AlphaContext)

    def test_multiple_custom_contexts(self):
        """Two different custom context classes can be active simultaneously."""
        with custom_step_context(AlphaContext(value="a")):
            with custom_step_context(BetaContext(count=42)):
                alpha = current_step_ctx(AlphaContext)
                beta = current_step_ctx(BetaContext)
                assert alpha.value == "a"
                assert beta.count == 42

    def test_nested_same_class(self):
        """Inner context of same class overrides outer, restores on exit."""
        with custom_step_context(AlphaContext(value="outer")) as outer:
            assert current_step_ctx(AlphaContext).value == "outer"

            with custom_step_context(AlphaContext(value="inner")) as inner:
                assert current_step_ctx(AlphaContext).value == "inner"
                assert inner is not outer

            # Outer restored
            assert current_step_ctx(AlphaContext).value == "outer"

    def test_mutation_visible(self):
        """Mutations to the context are visible via the accessor."""
        with custom_step_context(AlphaContext(processed=False)):
            ctx = current_step_ctx(AlphaContext)
            ctx.processed = True
            assert current_step_ctx(AlphaContext).processed is True

    def test_works_alongside_pipeline_and_step_contexts(self):
        """Custom contexts coexist with pipeline and step contexts."""
        with pipeline_context("test_pipe"):
            with step_context("test.step"):
                with custom_step_context(AlphaContext(value="custom")):
                    assert current_pipeline().name == "test_pipe"
                    assert current_step().step_name == "test.step"
                    assert current_step_ctx(AlphaContext).value == "custom"


class TestHasActive:
    def test_not_active(self):
        assert StepContextRegistry.has_active(AlphaContext) is False

    def test_active(self):
        with custom_step_context(AlphaContext()):
            assert StepContextRegistry.has_active(AlphaContext) is True
        assert StepContextRegistry.has_active(AlphaContext) is False

    def test_one_active_other_not(self):
        with custom_step_context(AlphaContext()):
            assert StepContextRegistry.has_active(AlphaContext) is True
            assert StepContextRegistry.has_active(BetaContext) is False


class TestRequiresStepContext:
    def test_success_with_context(self):
        @requires_step_context(AlphaContext)
        def needs_alpha():
            return current_step_ctx(AlphaContext).value

        with custom_step_context(AlphaContext(value="ok")):
            assert needs_alpha() == "ok"

    def test_failure_without_context(self):
        @requires_step_context(AlphaContext)
        def needs_alpha():
            return "unreachable"

        with pytest.raises(RuntimeError, match="AlphaContext"):
            needs_alpha()

    def test_multiple_required(self):
        @requires_step_context(AlphaContext, BetaContext)
        def needs_both():
            return "ok"

        # Missing both
        with pytest.raises(RuntimeError, match="AlphaContext.*BetaContext"):
            needs_both()

        # Missing BetaContext
        with custom_step_context(AlphaContext()):
            with pytest.raises(RuntimeError, match="BetaContext"):
                needs_both()

        # Both present — OK
        with custom_step_context(AlphaContext()):
            with custom_step_context(BetaContext()):
                assert needs_both() == "ok"

    def test_decorator_preserves_metadata(self):
        @requires_step_context(AlphaContext)
        def documented():
            """My docs."""
            pass

        assert documented.__name__ == "documented"
        assert documented.__doc__ == "My docs."
        assert documented._required_step_contexts == (AlphaContext,)

    def test_error_message_lists_missing(self):
        @requires_step_context(AlphaContext, BetaContext)
        def fn():
            pass

        with custom_step_context(AlphaContext()):
            with pytest.raises(RuntimeError) as exc_info:
                fn()
            msg = str(exc_info.value)
            assert "BetaContext" in msg
            assert "AlphaContext" not in msg.split("Отсутствуют:")[1]


class TestStepContextRegistryClear:
    def test_clear(self):
        """StepContextRegistry.clear() removes all registered context vars."""
        StepContextRegistry.get_or_create(AlphaContext)
        StepContextRegistry.get_or_create(BetaContext)
        assert len(StepContextRegistry._vars) >= 2
        StepContextRegistry.clear()
        assert len(StepContextRegistry._vars) == 0
