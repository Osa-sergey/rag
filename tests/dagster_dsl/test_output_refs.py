import pytest
from pydantic import BaseModel
from dagster_dsl.pipeline_builder import PipelineBuilder
from dagster_dsl.steps import register_step, StepRegistry
from dagster_dsl.yaml_loader import load_pipeline_dict
from dagster_dsl.pipeline_runner import run_pipeline

class DummyConfig(BaseModel):
    my_str: str = "default"
    my_int: int = 0
    my_list: list[str] = []

@pytest.fixture(autouse=True)
def clean_registries():
    reg = StepRegistry()
    saved = dict(reg._steps)
    reg.clear()
    
    @register_step("dummy.produce")
    def produce(**kwargs):
        # We simulate returning a dict that matches what downstream needs
        return {
            "out_str": "hello",
            "out_int": 42,
            "out_list": ["a", "b"],
        }
        
    @register_step("dummy.consume", schema_class=DummyConfig, config_dir="", config_name="")
    def consume(my_str: str, my_int: int, my_list: list[str], **kwargs):
        return {
            "got_str": my_str,
            "got_int": my_int,
            "got_list": my_list,
        }

    # Hack config dir for dummy tests
    step_def = reg.get("dummy.consume")
    step_def.config_dir = "dagster_dsl/conf" # arbitrary valid dir for hydra
    step_def.config_name = "config"

    # Actually, hydra config loader needs a real config dir or we can omit it if no schema?
    # Wait, yaml_loader validates only if schema_class AND config_dir.
    # So if we set config_dir=None, it won't run Hydra validation, only our pre-validation.
    # Let's test that first, or we can just not rely on Hydra for this unit test if config_dir is None.
    # Let's ensure config_dir = None so Hydra logic is bypassed for dummy.consume.
    step_def.config_dir = None

    yield
    reg._steps = saved

def test_valid_output_refs():
    pipeline_def = {
        "name": "test_refs",
        "steps": {
            "step_A": {
                "module": "dummy.produce",
                "outputs": {
                    "out_str": "str",
                    "out_int": "int",
                    "out_list": "list",
                }
            },
            "step_B": {
                "module": "dummy.consume",
                "depends_on": ["step_A"],
                "config": {
                    "my_str": "${{ steps.step_A.out_str }}",
                    "my_int": "${{ steps.step_A.out_int }}",
                    "my_list": "${{ steps.step_A.out_list }}",
                }
            }
        }
    }
    
    builder = load_pipeline_dict(pipeline_def)
    assert len(builder.steps) == 2
    
    # Run and verify runtime substitution
    results = run_pipeline(builder)
    
    assert "step_B" in results
    res_b = results["step_B"]
    assert res_b["got_str"] == "hello"
    assert res_b["got_int"] == 42
    assert res_b["got_list"] == ["a", "b"]

def test_invalid_ref_unknown_step():
    pipeline_def = {
        "name": "test_refs",
        "steps": {
            "step_B": {
                "module": "dummy.consume",
                "config": {
                    "my_str": "${{ steps.unknown.out_str }}"
                }
            }
        }
    }
    with pytest.raises(ValueError, match="Ссылка на неизвестный шаг 'unknown'"):
        load_pipeline_dict(pipeline_def)

def test_invalid_ref_not_in_depends_on():
    pipeline_def = {
        "name": "test_refs",
        "steps": {
            "step_A": {
                "module": "dummy.produce",
                "outputs": {"out_str": "str"}
            },
            "step_B": {
                "module": "dummy.consume",
                # Missing depends_on: ["step_A"]
                "config": {
                    "my_str": "${{ steps.step_A.out_str }}"
                }
            }
        }
    }
    with pytest.raises(ValueError, match="Шаг 'step_A' должен быть в depends_on"):
        load_pipeline_dict(pipeline_def)

def test_invalid_ref_missing_output():
    pipeline_def = {
        "name": "test_refs",
        "steps": {
            "step_A": {
                "module": "dummy.produce",
                "outputs": {}  # Missing out_str declaring
            },
            "step_B": {
                "module": "dummy.consume",
                "depends_on": ["step_A"],
                "config": {
                    "my_str": "${{ steps.step_A.out_str }}"
                }
            }
        }
    }
    with pytest.raises(ValueError, match="Шаг 'step_A' не объявляет output 'out_str'"):
        load_pipeline_dict(pipeline_def)

def test_invalid_ref_type_mismatch():
    pipeline_def = {
        "name": "test_refs",
        "steps": {
            "step_A": {
                "module": "dummy.produce",
                "outputs": {"out_int": "str"}  # Declared as str, but target expects int
            },
            "step_B": {
                "module": "dummy.consume",
                "depends_on": ["step_A"],
                "config": {
                    "my_int": "${{ steps.step_A.out_int }}"
                }
            }
        }
    }
    with pytest.raises(ValueError, match="Несовпадение типов для 'my_int'"):
        load_pipeline_dict(pipeline_def)

def test_inputs_section_runtime_substitution():
    """inputs values are resolved and merged on top of config at runtime."""
    pipeline_def = {
        "name": "test_inputs",
        "steps": {
            "step_A": {
                "module": "dummy.produce",
                "outputs": {
                    "out_str": "str",
                    "out_int": "int",
                }
            },
            "step_B": {
                "module": "dummy.consume",
                "depends_on": ["step_A"],
                "config": {
                    "my_list": [],
                },
                "inputs": {
                    "my_str": "${{ steps.step_A.out_str }}",
                    "my_int": "${{ steps.step_A.out_int }}",
                },
            }
        }
    }

    builder = load_pipeline_dict(pipeline_def)
    results = run_pipeline(builder)

    assert results["step_B"]["got_str"] == "hello"
    assert results["step_B"]["got_int"] == 42

def test_inputs_invalid_ref_raises():
    """Bad refs in inputs are caught at load time."""
    pipeline_def = {
        "name": "test_inputs",
        "steps": {
            "step_B": {
                "module": "dummy.consume",
                "inputs": {
                    "my_str": "${{ steps.missing.out_str }}"
                }
            }
        }
    }
    with pytest.raises(ValueError, match="Ссылка на неизвестный шаг 'missing'"):
        load_pipeline_dict(pipeline_def)

def test_inputs_override_config():
    """inputs values take precedence over config values."""
    pipeline_def = {
        "name": "test_inputs_override",
        "steps": {
            "step_A": {
                "module": "dummy.produce",
                "outputs": {
                    "out_str": "str",
                }
            },
            "step_B": {
                "module": "dummy.consume",
                "depends_on": ["step_A"],
                "config": {
                    "my_str": "from_config",
                    "my_int": 0,
                    "my_list": [],
                },
                "inputs": {
                    "my_str": "${{ steps.step_A.out_str }}",
                },
            }
        }
    }

    builder = load_pipeline_dict(pipeline_def)
    results = run_pipeline(builder)

    # inputs should win over config
    assert results["step_B"]["got_str"] == "hello"
