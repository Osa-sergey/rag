"""Tests for dagster_dsl.pipeline_schema — YAML pipeline validation."""
import pytest
from pydantic import ValidationError

from dagster_dsl.pipeline_schema import PipelineYaml, StepYaml


# ── StepYaml ──────────────────────────────────────────────────


class TestStepYaml:
    def test_basic(self):
        step = StepYaml(module="raptor_pipeline.run")
        assert step.module == "raptor_pipeline.run"
        assert step.config == {}
        assert step.depends_on == []

    def test_with_all_fields(self):
        step = StepYaml(
            module="raptor_pipeline.run",
            defaults=[{"embeddings": "huggingface"}],
            config={"input_dir": "data/"},
            depends_on=["parse"],
            on_success=["log_result"],
            on_failure=[{"retry": {"max_attempts": 3}}],
        )
        assert step.defaults == [{"embeddings": "huggingface"}]

    def test_parsed_callbacks(self):
        step = StepYaml(
            module="test.step",
            on_success=["log_result", {"notify": {"message": "Done"}}],
        )
        cbs = step.parsed_on_success()
        assert len(cbs) == 2
        assert cbs[0].name == "log_result"
        assert cbs[1].name == "notify"
        assert cbs[1].params["message"] == "Done"

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            StepYaml(module="test.step", unknown_field="value")


# ── PipelineYaml ──────────────────────────────────────────────


class TestPipelineYaml:
    def test_basic_pipeline(self):
        p = PipelineYaml(
            name="test",
            steps={
                "a": StepYaml(module="a.cmd"),
                "b": StepYaml(module="b.cmd", depends_on=["a"]),
            },
        )
        assert p.name == "test"
        assert len(p.steps) == 2

    def test_invalid_depends_on(self):
        """depends_on references non-existent step."""
        with pytest.raises(ValidationError, match="шаг не найден"):
            PipelineYaml(
                name="test",
                steps={
                    "a": StepYaml(module="a.cmd", depends_on=["nonexistent"]),
                },
            )

    def test_cycle_detection(self):
        """Cycle in depends_on graph."""
        with pytest.raises(ValidationError, match="цикл"):
            PipelineYaml(
                name="test",
                steps={
                    "a": StepYaml(module="a.cmd", depends_on=["b"]),
                    "b": StepYaml(module="b.cmd", depends_on=["a"]),
                },
            )

    def test_global_config(self):
        p = PipelineYaml(
            name="test",
            config={"stores.neo4j.uri": "bolt://prod:7687"},
            steps={"a": StepYaml(module="a.cmd")},
        )
        assert p.config["stores.neo4j.uri"] == "bolt://prod:7687"

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            PipelineYaml(
                name="test",
                steps={"a": StepYaml(module="a.cmd")},
                unknown="value",
            )

    def test_from_dict(self):
        """Test model_validate from dict (as YAML would be loaded)."""
        raw = {
            "name": "test_pipeline",
            "config": {"log_level": "DEBUG"},
            "metadata": {"owner": "team"},
            "steps": {
                "parse": {
                    "module": "document_parser.parse_csv",
                    "config": {"input_file": "data.csv"},
                    "on_success": ["log_result"],
                },
                "raptor": {
                    "module": "raptor_pipeline.run",
                    "depends_on": ["parse"],
                    "config": {"input_dir": "parsed_yaml"},
                },
            },
        }
        p = PipelineYaml.model_validate(raw)
        assert p.name == "test_pipeline"
        assert len(p.steps) == 2
