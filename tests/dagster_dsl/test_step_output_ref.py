"""Unit tests for dagster_dsl.output_ref.StepOutputRef."""
import pytest

from dagster_dsl.output_ref import StepOutputRef


# ── parse_ref ─────────────────────────────────────────────────

class TestParseRef:
    def test_valid_simple(self):
        ref = StepOutputRef.parse_ref("${{ steps.parse.output_dir }}")
        assert ref is not None
        assert ref.step_id == "parse"
        assert ref.output_key == "output_dir"

    def test_valid_with_spaces(self):
        ref = StepOutputRef.parse_ref("  ${{  steps.step_A.out_str  }}  ")
        assert ref is not None
        assert ref.step_id == "step_A"
        assert ref.output_key == "out_str"

    def test_valid_with_dashes(self):
        ref = StepOutputRef.parse_ref("${{ steps.my-step.my-key }}")
        assert ref is not None
        assert ref.step_id == "my-step"
        assert ref.output_key == "my-key"

    def test_not_a_ref_plain_string(self):
        assert StepOutputRef.parse_ref("hello world") is None

    def test_not_a_ref_partial(self):
        assert StepOutputRef.parse_ref("prefix ${{ steps.a.b }}") is None

    def test_not_a_ref_empty(self):
        assert StepOutputRef.parse_ref("") is None

    def test_not_a_ref_wrong_prefix(self):
        assert StepOutputRef.parse_ref("${{ outputs.a.b }}") is None


# ── is_type_compatible ────────────────────────────────────────

class TestTypeCompatibility:
    def test_str_to_str(self):
        assert StepOutputRef.is_type_compatible("str", str) is True

    def test_int_to_int(self):
        assert StepOutputRef.is_type_compatible("int", int) is True

    def test_int_to_float(self):
        assert StepOutputRef.is_type_compatible("int", float) is True

    def test_str_to_int_fails(self):
        assert StepOutputRef.is_type_compatible("str", int) is False

    def test_list_to_list(self):
        assert StepOutputRef.is_type_compatible("list", list) is True

    def test_dict_to_dict(self):
        assert StepOutputRef.is_type_compatible("dict", dict) is True

    def test_bool_to_bool(self):
        assert StepOutputRef.is_type_compatible("bool", bool) is True

    def test_any_always_ok(self):
        assert StepOutputRef.is_type_compatible("dict", None) is True


# ── mock_value ────────────────────────────────────────────────

class TestMockValue:
    def test_str_mock(self):
        ref = StepOutputRef(step_id="a", output_key="b", expected_type="str")
        assert isinstance(ref.mock_value(), str)

    def test_int_mock(self):
        ref = StepOutputRef(step_id="a", output_key="b", expected_type="int")
        assert isinstance(ref.mock_value(), int)

    def test_list_mock(self):
        ref = StepOutputRef(step_id="a", output_key="b", expected_type="list")
        assert isinstance(ref.mock_value(), list)

    def test_unknown_type_falls_back(self):
        ref = StepOutputRef(step_id="a", output_key="b", expected_type="complex")
        assert ref.mock_value() == "__ref__"


# ── resolve ───────────────────────────────────────────────────

class TestResolve:
    def test_resolve_success(self):
        ref = StepOutputRef(step_id="parse", output_key="count", expected_type="int")
        results = {"parse": {"count": 42, "path": "/tmp"}}
        assert ref.resolve(results) == 42

    def test_resolve_missing_step(self):
        ref = StepOutputRef(step_id="missing", output_key="x", expected_type="str")
        with pytest.raises(ValueError, match="не найден"):
            ref.resolve({})

    def test_resolve_missing_key(self):
        ref = StepOutputRef(step_id="parse", output_key="missing", expected_type="str")
        with pytest.raises(KeyError, match="не вернул ключ"):
            ref.resolve({"parse": {"other": 1}})

    def test_resolve_type_mismatch(self):
        ref = StepOutputRef(step_id="parse", output_key="count", expected_type="int")
        with pytest.raises(TypeError, match="ожидался int"):
            ref.resolve({"parse": {"count": "not_an_int"}})

    def test_resolve_non_dict_result(self):
        ref = StepOutputRef(step_id="parse", output_key="count", expected_type="int")
        with pytest.raises(ValueError, match="не является dict"):
            ref.resolve({"parse": "string_result"})
