"""Typed step output references for Dagster DSL pipelines.

``StepOutputRef`` encapsulates a reference to another step's output
(``${{ steps.<step_id>.<output_key> }}``).  It is a **DSL-level** object:
module schemas stay unchanged, and full Pydantic validation of the
resolved value happens at runtime after substitution.

Lifecycle::

    YAML load ──► parse_ref("${{ steps.A.x }}")
                   ├─ validate: step exists, in depends_on, key declared
                   ├─ type-check: output type compatible with target field
                   └─ mock_value() → dummy for Hydra compose

    Runtime   ──► resolve(results) → real value
                   └─ re-validate config with Pydantic (full constraints)
"""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

__all__ = ["StepOutputRef"]

_REF_RE = re.compile(
    r"^\$\{\{\s*steps\.([a-zA-Z0-9_\-]+)\.([a-zA-Z0-9_\-]+)\s*\}\}$"
)

# Mapping: declared output type string → Python type
_TYPE_MAP: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
}

# Dummy values that pass Hydra / Pydantic validation w/o triggering
# ge=, le=, etc. constraints — intentionally "neutral".
_MOCK_VALUES: dict[str, Any] = {
    "str": "__ref__",
    "int": 1,
    "float": 1.0,
    "bool": True,
    "list": [],
    "dict": {},
}


class StepOutputRef(BaseModel):
    """A typed reference to a named output of an upstream step.

    Created at YAML load time, resolved at runtime.
    """

    step_id: str = Field(..., description="Source step ID")
    output_key: str = Field(..., description="Key in source step's outputs")
    expected_type: str = Field(
        ..., description="Declared type of the output (str, int, …)"
    )

    # ── Factory ───────────────────────────────────────────────

    @classmethod
    def parse_ref(cls, raw: str) -> StepOutputRef | None:
        """Try to parse ``${{ steps.X.Y }}`` into a ``StepOutputRef``.

        Returns ``None`` if *raw* does not match the reference syntax.
        """
        m = _REF_RE.match(raw.strip())
        if m is None:
            return None
        return cls(
            step_id=m.group(1),
            output_key=m.group(2),
            expected_type="",  # filled by caller after validation
        )

    # ── Validation helpers (called at YAML load) ──────────────

    @staticmethod
    def is_type_compatible(declared_type: str, target_annotation: Any) -> bool:
        """Check that *declared_type* (from ``outputs:``) is compatible
        with the Pydantic field *target_annotation*.

        Compatibility rules:

        ============  ==============================================
        declared_type Compatible target annotations
        ============  ==============================================
        str           str, Path, Optional[str], Any
        int           int, float, Optional[int], Any
        float         float, int, Optional[float], Any
        list          list[…], Sequence[…], Any
        dict          dict[…], Mapping[…], Any
        bool          bool, Any
        ============  ==============================================
        """
        if target_annotation is None:
            return True  # cannot verify — assume ok

        type_name = getattr(
            target_annotation, "__name__", str(target_annotation)
        ).lower()

        compat: dict[str, tuple[str, ...]] = {
            "str": ("str", "path", "any"),
            "int": ("int", "float", "any"),
            "float": ("float", "int", "any"),
            "list": ("list", "sequence", "any"),
            "dict": ("dict", "mapping", "any"),
            "bool": ("bool", "any"),
        }
        allowed = compat.get(declared_type, ())
        if any(kw in type_name for kw in allowed):
            return True
        # Last resort: Any in the leaf
        if "any" in type_name.split(".")[-1]:
            return True
        return False

    # ── Mock value for Hydra ──────────────────────────────────

    def mock_value(self) -> Any:
        """Return a neutral dummy value suitable for Hydra compose.

        The value is type-correct but intentionally "safe" so it doesn't
        trigger complex ``ge=`` / ``le=`` / cross-field validators.
        Full Pydantic re-validation runs at **runtime** after resolve().
        """
        return _MOCK_VALUES.get(self.expected_type, "__ref__")

    # ── Runtime resolution ────────────────────────────────────

    def resolve(self, results: dict[str, Any]) -> Any:
        """Substitute the reference with the actual value from *results*.

        Args:
            results: ``{step_id: step_result_dict, …}`` accumulated by
                     ``pipeline_runner.run_pipeline``.

        Raises:
            ValueError: Step not found in results.
            KeyError:   Output key not present in step result.
        """
        step_result = results.get(self.step_id)
        if step_result is None:
            raise ValueError(
                f"Шаг '{self.step_id}' не найден в результатах pipeline"
            )
        if not isinstance(step_result, dict):
            raise ValueError(
                f"Результат шага '{self.step_id}' не является dict"
            )
        if self.output_key not in step_result:
            raise KeyError(
                f"Шаг '{self.step_id}' не вернул ключ '{self.output_key}'"
            )
        value = step_result[self.output_key]

        # Optional: runtime type sanity check
        expected_py = _TYPE_MAP.get(self.expected_type)
        if expected_py is not None and not isinstance(value, expected_py):
            raise TypeError(
                f"Шаг '{self.step_id}' output '{self.output_key}': "
                f"ожидался {self.expected_type}, получен {type(value).__name__}"
            )
        return value
