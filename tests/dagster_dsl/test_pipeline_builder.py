"""Tests for dagster_dsl.pipeline_builder — DSL builder and DAG construction."""
import pytest

from dagster_dsl.pipeline_builder import pipeline, PipelineBuilder, StepRef


# ── StepRef ───────────────────────────────────────────────────


class TestStepRef:
    def test_basic_creation(self):
        ref = StepRef(id="s1", step_name="raptor_pipeline.run")
        assert ref.id == "s1"
        assert ref.step_name == "raptor_pipeline.run"
        assert ref.depends_on == []
        assert ref.overrides == {}

    def test_after_chaining(self):
        s1 = StepRef(id="s1", step_name="a.b")
        s2 = StepRef(id="s2", step_name="c.d")
        s3 = StepRef(id="s3", step_name="e.f")

        result = s3.after(s1, s2)
        assert result is s3  # returns self for chaining
        assert s3.depends_on == ["s1", "s2"]

    def test_after_no_duplicates(self):
        s1 = StepRef(id="s1", step_name="a.b")
        s2 = StepRef(id="s2", step_name="c.d")
        s2.after(s1)
        s2.after(s1)  # duplicate
        assert s2.depends_on == ["s1"]

    def test_override_chaining(self):
        ref = StepRef(id="s1", step_name="a.b")
        result = ref.override(input_dir="data/", max_concurrency=4)
        assert result is ref
        assert ref.overrides == {"input_dir": "data/", "max_concurrency": 4}


# ── PipelineBuilder ──────────────────────────────────────────


class TestPipelineBuilder:
    def test_basic_pipeline(self):
        p = PipelineBuilder("test_pipeline")
        s1 = p.step("module_a.cmd1")
        s2 = p.step("module_b.cmd2")
        s2.after(s1)

        assert len(p.steps) == 2
        assert p.name == "test_pipeline"

    def test_config_override_kwargs(self):
        p = PipelineBuilder("test")
        p.config_override(input_dir="data/", log_level="INFO")
        assert p.global_overrides == {"input_dir": "data/", "log_level": "INFO"}

    def test_config_override_positional(self):
        p = PipelineBuilder("test")
        p.config_override(
            "stores.neo4j.uri", "bolt://prod:7687",
            "stores.qdrant.host", "prod-qdrant",
        )
        assert p.global_overrides == {
            "stores.neo4j.uri": "bolt://prod:7687",
            "stores.qdrant.host": "prod-qdrant",
        }

    def test_config_override_odd_args_raises(self):
        p = PipelineBuilder("test")
        with pytest.raises(ValueError, match="key-value pairs"):
            p.config_override("key1", "val1", "key2")

    def test_step_auto_id(self):
        p = PipelineBuilder("test")
        s1 = p.step("raptor_pipeline.run")
        s2 = p.step("raptor_pipeline.run")  # same step name, but different id
        assert s1.id != s2.id
        assert "raptor_pipeline_run" in s1.id

    def test_step_custom_id(self):
        p = PipelineBuilder("test")
        s1 = p.step("raptor_pipeline.run", step_id="my_custom_id")
        assert s1.id == "my_custom_id"

    def test_step_overrides(self):
        p = PipelineBuilder("test")
        s1 = p.step("raptor_pipeline.run", input_dir="data/", max_concurrency=4)
        assert s1.overrides == {"input_dir": "data/", "max_concurrency": 4}

    def test_topology_sort_linear(self):
        """A → B → C should sort as [A, B, C]."""
        p = PipelineBuilder("test")
        a = p.step("a.cmd", step_id="a")
        b = p.step("b.cmd", step_id="b").after(a)
        c = p.step("c.cmd", step_id="c").after(b)

        order = p.topology_sort()
        ids = [s.id for s in order]
        assert ids == ["a", "b", "c"]

    def test_topology_sort_diamond(self):
        """Diamond dependency: A → B,C → D.

           A
          / \\
         B   C
          \\ /
           D
        """
        p = PipelineBuilder("test")
        a = p.step("a.cmd", step_id="a")
        b = p.step("b.cmd", step_id="b").after(a)
        c = p.step("c.cmd", step_id="c").after(a)
        d = p.step("d.cmd", step_id="d").after(b, c)

        order = p.topology_sort()
        ids = [s.id for s in order]

        # A must be first, D must be last
        assert ids[0] == "a"
        assert ids[-1] == "d"
        # B and C must be between A and D
        assert set(ids[1:3]) == {"b", "c"}

    def test_topology_sort_parallel(self):
        """Independent steps can be in any order."""
        p = PipelineBuilder("test")
        p.step("a.cmd", step_id="a")
        p.step("b.cmd", step_id="b")
        p.step("c.cmd", step_id="c")

        order = p.topology_sort()
        assert len(order) == 3

    def test_topology_sort_cycle_detection(self):
        """Cycle should raise ValueError."""
        p = PipelineBuilder("test")
        a = p.step("a.cmd", step_id="a")
        b = p.step("b.cmd", step_id="b").after(a)
        # Create cycle: a → b → a (manually)
        a.depends_on.append("b")

        with pytest.raises(ValueError, match="cycle"):
            p.topology_sort()

    def test_metadata(self):
        p = PipelineBuilder("test")
        p.meta(owner="data-team", schedule="daily")
        assert p.metadata == {"owner": "data-team", "schedule": "daily"}

    def test_describe(self):
        p = PipelineBuilder("test")
        a = p.step("a.cmd", step_id="a")
        b = p.step("b.cmd", step_id="b").after(a)
        desc = p.describe()
        assert "test" in desc
        assert "a.cmd" in desc
        assert "b.cmd" in desc

    def test_repr(self):
        p = PipelineBuilder("test")
        p.step("a.cmd")
        r = repr(p)
        assert "test" in r
        assert "a.cmd" in r


# ── Context Manager: pipeline() ──────────────────────────────


class TestPipelineContextManager:
    def test_context_manager(self):
        with pipeline("test_pipeline") as p:
            assert isinstance(p, PipelineBuilder)
            s1 = p.step("a.cmd")
            s2 = p.step("b.cmd").after(s1)

        assert len(p.steps) == 2

    def test_context_manager_with_overrides(self):
        with pipeline("test", input_dir="data/") as p:
            pass
        assert p.global_overrides == {"input_dir": "data/"}

    def test_full_dsl_example(self):
        """Test the full DSL as shown in the README."""
        with pipeline("habr_full") as p:
            p.config_override(
                "stores.neo4j.uri", "bolt://prod:7687",
            )
            parse = p.step("document_parser.parse_csv",
                input_file="data.csv",
                output_dir="parsed_yaml",
            )
            raptor = p.step("raptor_pipeline.run",
                input_dir="parsed_yaml",
            ).after(parse)
            topics = p.step("topic_modeler.train").after(parse)
            concepts = p.step("concept_builder.process",
                base_article="986380",
            ).after(raptor, topics)

        # Verify structure
        assert len(p.steps) == 4
        assert p.global_overrides["stores.neo4j.uri"] == "bolt://prod:7687"

        # Check dependencies
        s = p.steps
        raptor_ref = s[raptor.id]
        topics_ref = s[topics.id]
        concepts_ref = s[concepts.id]

        assert parse.id in raptor_ref.depends_on
        assert parse.id in topics_ref.depends_on
        assert raptor.id in concepts_ref.depends_on
        assert topics.id in concepts_ref.depends_on

        # Topology sort should work
        order = p.topology_sort()
        ids = [x.id for x in order]
        assert ids.index(parse.id) < ids.index(raptor.id)
        assert ids.index(parse.id) < ids.index(topics.id)
        assert ids.index(raptor.id) < ids.index(concepts.id)
        assert ids.index(topics.id) < ids.index(concepts.id)
