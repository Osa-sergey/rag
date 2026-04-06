"""Tests for dagster_dsl.yaml_loader — YAML pipeline loading + validation."""
import pytest
import tempfile
from pathlib import Path

from dagster_dsl.yaml_loader import load_pipeline_yaml, load_pipeline_dict
from dagster_dsl.pipeline_builder import PipelineBuilder
from dagster_dsl.steps import StepRegistry, StepDefinition


@pytest.fixture(autouse=True)
def register_test_steps():
    """Register dummy steps for testing YAML loading."""
    registry = StepRegistry()
    saved = dict(registry._steps)

    # Register test steps
    for name in ["a.cmd", "b.cmd", "c.cmd", "d.cmd"]:
        registry.register(StepDefinition(name=name, description=f"Test step {name}"))

    yield registry
    registry._steps = saved


def _write_yaml(content: str) -> Path:
    """Write YAML content to a temp file and return the path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    return Path(f.name)


# ── load_pipeline_dict ────────────────────────────────────────


class TestLoadPipelineDict:
    def test_basic_pipeline(self, register_test_steps):
        raw = {
            "name": "test",
            "steps": {
                "step_a": {"module": "a.cmd", "config": {"key": "val"}},
                "step_b": {"module": "b.cmd", "depends_on": ["step_a"]},
            },
        }
        builder = load_pipeline_dict(raw)
        assert isinstance(builder, PipelineBuilder)
        assert builder.name == "test"
        assert len(builder.steps) == 2

    def test_global_overrides(self, register_test_steps):
        raw = {
            "name": "test",
            "config": {"log_level": "DEBUG", "db_host": "prod"},
            "steps": {"a": {"module": "a.cmd"}},
        }
        builder = load_pipeline_dict(raw)
        assert builder.global_overrides["log_level"] == "DEBUG"
        assert builder.global_overrides["db_host"] == "prod"

    def test_metadata(self, register_test_steps):
        raw = {
            "name": "test",
            "metadata": {"owner": "team", "schedule": "daily"},
            "steps": {"a": {"module": "a.cmd"}},
        }
        builder = load_pipeline_dict(raw)
        assert builder.metadata["owner"] == "team"

    def test_dependencies(self, register_test_steps):
        raw = {
            "name": "test",
            "steps": {
                "a": {"module": "a.cmd"},
                "b": {"module": "b.cmd", "depends_on": ["a"]},
                "c": {"module": "c.cmd", "depends_on": ["a", "b"]},
            },
        }
        builder = load_pipeline_dict(raw)
        steps = builder.steps
        assert "a" in steps["b"].depends_on
        assert "a" in steps["c"].depends_on
        assert "b" in steps["c"].depends_on

    def test_callbacks_attached(self, register_test_steps):
        raw = {
            "name": "test",
            "steps": {
                "a": {
                    "module": "a.cmd",
                    "on_success": ["log_result"],
                    "on_failure": [{"retry": {"max_attempts": 3}}],
                },
            },
        }
        builder = load_pipeline_dict(raw)
        step = builder.steps["a"]
        assert len(step.on_success_callbacks) == 1
        assert step.on_success_callbacks[0].name == "log_result"
        assert len(step.on_failure_callbacks) == 1
        assert step.on_failure_callbacks[0].name == "retry"

    def test_hydra_defaults(self, register_test_steps):
        raw = {
            "name": "test",
            "steps": {
                "a": {
                    "module": "a.cmd",
                    "defaults": [{"embeddings": "huggingface"}],
                },
            },
        }
        builder = load_pipeline_dict(raw)
        assert builder.steps["a"].hydra_defaults == [{"embeddings": "huggingface"}]

    def test_unregistered_module_raises(self, register_test_steps):
        raw = {
            "name": "test",
            "steps": {"a": {"module": "nonexistent.step"}},
        }
        with pytest.raises(ValueError, match="не зарегистрирован"):
            load_pipeline_dict(raw)

    def test_invalid_structure_raises(self, register_test_steps):
        raw = {"steps": {"a": {"module": "a.cmd"}}}  # missing 'name'
        with pytest.raises(ValueError, match="Ошибка валидации"):
            load_pipeline_dict(raw)

    def test_topology_preserved(self, register_test_steps):
        """Steps preserve topological order."""
        raw = {
            "name": "test",
            "steps": {
                "a": {"module": "a.cmd"},
                "b": {"module": "b.cmd", "depends_on": ["a"]},
                "c": {"module": "c.cmd", "depends_on": ["a"]},
                "d": {"module": "d.cmd", "depends_on": ["b", "c"]},
            },
        }
        builder = load_pipeline_dict(raw)
        order = builder.topology_sort()
        ids = [s.id for s in order]
        assert ids.index("a") < ids.index("b")
        assert ids.index("a") < ids.index("c")
        assert ids.index("b") < ids.index("d")
        assert ids.index("c") < ids.index("d")


# ── load_pipeline_yaml ────────────────────────────────────────


class TestLoadPipelineYaml:
    def test_load_from_file(self, register_test_steps):
        yaml_content = """
name: from_file
steps:
  step1:
    module: a.cmd
    config:
      key: value
  step2:
    module: b.cmd
    depends_on: [step1]
"""
        path = _write_yaml(yaml_content)
        try:
            builder = load_pipeline_yaml(path)
            assert builder.name == "from_file"
            assert len(builder.steps) == 2
        finally:
            path.unlink()

    def test_file_not_found(self, register_test_steps):
        with pytest.raises(FileNotFoundError, match="не найден"):
            load_pipeline_yaml("/nonexistent/path.yaml")

    def test_full_yaml_with_callbacks_and_context(self, register_test_steps):
        yaml_content = """
name: full_test
config:
  log_level: DEBUG
metadata:
  owner: test-team
steps:
  parse:
    module: a.cmd
    on_success:
      - log_result
  index:
    module: b.cmd
    depends_on: [parse]
    on_failure:
      - retry:
          max_attempts: 2
          delay: 5
  concepts:
    module: c.cmd
    depends_on: [index]
"""
        path = _write_yaml(yaml_content)
        try:
            builder = load_pipeline_yaml(path)
            assert builder.name == "full_test"
            assert builder.global_overrides["log_level"] == "DEBUG"
            assert builder.metadata["owner"] == "test-team"
            assert len(builder.steps["index"].on_failure_callbacks) == 1
        finally:
            path.unlink()
