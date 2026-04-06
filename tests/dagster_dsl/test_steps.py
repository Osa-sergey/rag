"""Tests for dagster_dsl.steps — step registry and execution."""
import pytest

from dagster_dsl.steps import StepDefinition, StepRegistry, register_step


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear registry before each test."""
    registry = StepRegistry()
    # Save existing steps (from module_steps imports)
    saved = dict(registry._steps)
    registry.clear()
    yield registry
    # Restore
    registry._steps = saved


# ── StepDefinition ────────────────────────────────────────────


class TestStepDefinition:
    def test_name_parsing(self):
        sd = StepDefinition(name="raptor_pipeline.run")
        assert sd.module_name == "raptor_pipeline"
        assert sd.command_name == "run"

    def test_explicit_module(self):
        sd = StepDefinition(name="custom", module_name="my_module", command_name="my_cmd")
        assert sd.module_name == "my_module"
        assert sd.command_name == "my_cmd"

    def test_tags(self):
        sd = StepDefinition(name="a.b", tags={"env": "prod"})
        assert sd.tags["env"] == "prod"


# ── StepRegistry ─────────────────────────────────────────────


class TestStepRegistry:
    def test_register_and_get(self, clean_registry):
        registry = clean_registry
        sd = StepDefinition(name="test.step", description="A test step")
        registry.register(sd)
        assert registry.get("test.step") is sd
        assert registry.has("test.step")
        assert "test.step" in registry

    def test_get_missing_raises(self, clean_registry):
        with pytest.raises(KeyError, match="не зарегистрирован"):
            clean_registry.get("nonexistent.step")

    def test_list_steps(self, clean_registry):
        registry = clean_registry
        registry.register(StepDefinition(name="b.cmd"))
        registry.register(StepDefinition(name="a.cmd"))
        assert registry.list_steps() == ["a.cmd", "b.cmd"]  # sorted

    def test_singleton(self):
        r1 = StepRegistry()
        r2 = StepRegistry()
        assert r1 is r2

    def test_len(self, clean_registry):
        registry = clean_registry
        assert len(registry) == 0
        registry.register(StepDefinition(name="a.b"))
        assert len(registry) == 1


# ── @register_step decorator ────────────────────────────────


class TestRegisterStepDecorator:
    def test_decorator_registers(self, clean_registry):
        @register_step("test.decorated", description="Decorated step")
        def my_step(cfg):
            return "result"

        registry = clean_registry
        assert registry.has("test.decorated")
        sd = registry.get("test.decorated")
        assert sd.description == "Decorated step"
        assert sd.execute_fn is my_step

    def test_decorated_fn_still_callable(self, clean_registry):
        @register_step("test.callable")
        def my_step(**kwargs):
            return 42

        assert my_step(x=1) == 42
