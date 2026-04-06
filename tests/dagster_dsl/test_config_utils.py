"""Tests for dagster_dsl.config_utils — merge, filter, Hydra overrides, inspect."""
import pytest
from pydantic import BaseModel, Field
from typing import Optional

from dagster_dsl.config_utils import (
    deep_merge,
    flat_to_nested,
    filter_global_for_schema,
    dict_to_hydra_overrides,
    resolve_step_overrides,
)


# ── Pydantic schemas for testing ──────────────────────────────

class Neo4jCfg(BaseModel):
    uri: str = "bolt://localhost:7687"
    password: str = "pass"
    user: str = "neo4j"

class StoresCfg(BaseModel):
    neo4j: Neo4jCfg = Field(default_factory=Neo4jCfg)

class FullSchema(BaseModel):
    """Schema that has both log_level and stores."""
    log_level: str = "INFO"
    input_dir: str = "data/"
    stores: StoresCfg = Field(default_factory=StoresCfg)
    class Config:
        extra = "allow"

class SimpleSchema(BaseModel):
    """Schema with no 'stores' field."""
    log_level: str = "INFO"
    input_file: Optional[str] = None
    output_dir: str = "out/"
    class Config:
        extra = "allow"


# ── deep_merge ────────────────────────────────────────────────

class TestDeepMerge:
    def test_flat(self):
        result = deep_merge({"a": 1, "b": 2}, {"b": 99, "c": 3})
        assert result == {"a": 1, "b": 99, "c": 3}

    def test_nested_merge(self):
        base = {"stores": {"neo4j": {"uri": "bolt://dev", "password": "dev"}}}
        override = {"stores": {"neo4j": {"password": "prod"}}}
        result = deep_merge(base, override)
        assert result["stores"]["neo4j"]["uri"] == "bolt://dev"   # kept
        assert result["stores"]["neo4j"]["password"] == "prod"    # overridden

    def test_nested_new_key(self):
        base = {"stores": {"neo4j": {"uri": "bolt://dev"}}}
        override = {"stores": {"qdrant": {"host": "prod-host"}}}
        result = deep_merge(base, override)
        assert result["stores"]["neo4j"]["uri"] == "bolt://dev"
        assert result["stores"]["qdrant"]["host"] == "prod-host"

    def test_override_replaces_non_dict(self):
        result = deep_merge({"key": "old"}, {"key": "new"})
        assert result["key"] == "new"

    def test_does_not_mutate_inputs(self):
        base = {"a": {"b": 1}}
        override = {"a": {"c": 2}}
        deep_merge(base, override)
        assert "c" not in base["a"]


# ── flat_to_nested ─────────────────────────────────────────────

class TestFlatToNested:
    def test_flat_dot_notation(self):
        result = flat_to_nested({
            "stores.neo4j.uri": "bolt://...",
            "log_level": "INFO",
        })
        assert result["stores"]["neo4j"]["uri"] == "bolt://..."
        assert result["log_level"] == "INFO"

    def test_already_nested(self):
        result = flat_to_nested({"stores": {"neo4j": {"uri": "bolt://"}}})
        assert result["stores"]["neo4j"]["uri"] == "bolt://"

    def test_mixed_flat_and_nested(self):
        """Flat dot and nested dict for same prefix merge correctly."""
        result = flat_to_nested({
            "stores.neo4j.uri": "bolt://...",
            "stores": {"qdrant": {"host": "localhost"}},
        })
        assert result["stores"]["neo4j"]["uri"] == "bolt://..."
        assert result["stores"]["qdrant"]["host"] == "localhost"

    def test_empty(self):
        assert flat_to_nested({}) == {}


# ── filter_global_for_schema ──────────────────────────────────

class TestFilterGlobalForSchema:
    def test_removes_unknown_top_level_keys(self):
        global_cfg = {
            "log_level": "INFO",
            "stores": {"neo4j": {"uri": "bolt://..."}},
        }
        # SimpleSchema has no 'stores' field
        result = filter_global_for_schema(global_cfg, SimpleSchema)
        assert "log_level" in result
        assert "stores" not in result

    def test_keeps_known_keys(self):
        global_cfg = {
            "log_level": "INFO",
            "stores": {"neo4j": {"uri": "bolt://..."}},
        }
        # FullSchema has 'stores'
        result = filter_global_for_schema(global_cfg, FullSchema)
        assert "log_level" in result
        assert "stores" in result
        assert result["stores"]["neo4j"]["uri"] == "bolt://..."

    def test_nested_filtering(self):
        """Sub-schema fields are filtered recursively."""
        global_cfg = {
            "stores": {
                "neo4j": {"uri": "bolt://...", "unknown_key": "x"},
            }
        }
        result = filter_global_for_schema(global_cfg, FullSchema)
        neo4j = result["stores"]["neo4j"]
        assert "uri" in neo4j           # known in Neo4jCfg
        assert "unknown_key" not in neo4j   # unknown → filtered

    def test_empty_global(self):
        result = filter_global_for_schema({}, FullSchema)
        assert result == {}

    def test_no_schema_fields_match(self):
        global_cfg = {"completely_foreign": "value", "another": 123}
        result = filter_global_for_schema(global_cfg, SimpleSchema)
        assert result == {}


# ── dict_to_hydra_overrides ───────────────────────────────────

class TestDictToHydraOverrides:
    def test_flat(self):
        overrides = dict_to_hydra_overrides({"log_level": "INFO", "count": 5})
        assert "log_level=INFO" in overrides
        assert "count=5" in overrides

    def test_nested(self):
        overrides = dict_to_hydra_overrides({
            "stores": {"neo4j": {"uri": "bolt://prod:7687"}}
        })
        assert "stores.neo4j.uri=bolt://prod:7687" in overrides

    def test_none_value(self):
        overrides = dict_to_hydra_overrides({"input_file": None})
        assert "input_file=null" in overrides

    def test_bool(self):
        overrides = dict_to_hydra_overrides({"debug": True, "verbose": False})
        assert "debug=true" in overrides
        assert "verbose=false" in overrides

    def test_list(self):
        overrides = dict_to_hydra_overrides({"tags": ["a", "b", "c"]})
        assert "tags=[a,b,c]" in overrides

    def test_empty(self):
        assert dict_to_hydra_overrides({}) == []


# ── resolve_step_overrides ────────────────────────────────────

class TestResolveStepOverrides:
    def test_filters_global_and_merges(self):
        global_cfg = {
            "log_level": "INFO",
            "stores": {"neo4j": {"uri": "bolt://global"}},
        }
        step_cfg = {"output_dir": "out/"}

        overrides, merged = resolve_step_overrides(global_cfg, step_cfg, SimpleSchema)

        # log_level kept (in schema), stores filtered out
        assert any("log_level=INFO" in o for o in overrides)
        assert not any("stores" in o for o in overrides)
        # step config included
        assert any("output_dir=out/" in o for o in overrides)

    def test_step_wins_over_global(self):
        global_cfg = {"stores": {"neo4j": {"password": "global_pass"}}}
        step_cfg = {"stores": {"neo4j": {"password": "step_pass"}}}

        overrides, merged = resolve_step_overrides(global_cfg, step_cfg, FullSchema)

        assert merged["stores"]["neo4j"]["password"] == "step_pass"
        assert any("step_pass" in o for o in overrides)

    def test_no_schema_passes_all(self):
        global_cfg = {"log_level": "DEBUG", "anything": "value"}
        step_cfg = {"extra": "data"}

        overrides, merged = resolve_step_overrides(global_cfg, step_cfg, schema_class=None)

        assert any("log_level=DEBUG" in o for o in overrides)
        assert any("anything=value" in o for o in overrides)
        assert any("extra=data" in o for o in overrides)

    def test_flat_global_normalized(self):
        """Flat dot-notation global config is normalized to nested before filtering."""
        global_cfg = {
            "stores.neo4j.uri": "bolt://flat",
            "log_level": "WARNING",
        }
        step_cfg = {}

        overrides, merged = resolve_step_overrides(global_cfg, step_cfg, FullSchema)

        assert merged["stores"]["neo4j"]["uri"] == "bolt://flat"
        assert merged["log_level"] == "WARNING"
        assert any("stores.neo4j.uri=bolt://flat" in o for o in overrides)

    def test_returns_hydra_strings_and_nested_dict(self):
        global_cfg = {"log_level": "INFO"}
        step_cfg = {"input_file": "data.csv"}

        overrides, merged = resolve_step_overrides(global_cfg, step_cfg, SimpleSchema)

        assert isinstance(overrides, list)
        assert all(isinstance(s, str) for s in overrides)
        assert isinstance(merged, dict)
        assert "log_level" in merged
        assert "input_file" in merged
