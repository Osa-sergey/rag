"""COP-based context system for pipeline orchestration.

Uses ``contextvars`` (Python 3.7+) to propagate pipeline- and step-level
contexts through the call stack — following the Context-Oriented Programming
paradigm described in ``08_context_oriented.md``.

Key concepts:
    PipelineContext  – global overrides, pipeline name, metadata
    StepContext      – step-level overrides, inputs/outputs, module reference
    @requires_context("pipeline") – decorator that ensures a context is active

Per-step custom contexts (COP Layer 2):
    StepContextRegistry         – one ContextVar per custom context class
    custom_step_context(inst)   – activate a typed step context
    current_step_ctx(cls)       – typed accessor: get active context by class
    @requires_step_context(cls) – decorator guard for custom contexts
"""
from __future__ import annotations

from contextvars import ContextVar
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Type, TypeVar


T = TypeVar("T")


# ── Context Data Classes ──────────────────────────────────────


@dataclass
class PipelineContext:
    """Global pipeline-level context.

    Stores the pipeline name, global Hydra-style overrides that apply to ALL
    steps, and arbitrary metadata (tags, owner, schedule, etc.).
    """

    name: str
    overrides: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def set_override(self, key: str, value: Any) -> None:
        """Set or update a single Hydra override."""
        self.overrides[key] = value

    def set_overrides(self, **kv: Any) -> None:
        """Batch-set Hydra overrides."""
        self.overrides.update(kv)


@dataclass
class StepContext:
    """Step-level context.

    Stores the step name (``module.command``), step-level overrides that merge
    on top of the pipeline overrides, and per-step metadata.
    """

    step_name: str
    module: str = ""
    command: str = ""
    overrides: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if "." in self.step_name and not self.module:
            parts = self.step_name.rsplit(".", 1)
            self.module = parts[0]
            self.command = parts[1]

    @property
    def merged_overrides(self) -> dict[str, Any]:
        """Merge pipeline-level overrides with step-level overrides.

        Step-level overrides take precedence.
        """
        try:
            pipeline_ctx = current_pipeline()
            merged = {**pipeline_ctx.overrides, **self.overrides}
        except RuntimeError:
            merged = dict(self.overrides)
        return merged


# ── ContextVars ───────────────────────────────────────────────

_pipeline_ctx: ContextVar[PipelineContext] = ContextVar("pipeline")
_step_ctx: ContextVar[StepContext] = ContextVar("step")


# ── Context Managers ──────────────────────────────────────────


@contextmanager
def pipeline_context(name: str, **overrides: Any):
    """Activate a pipeline context — like ``with(pipeline)`` in Kotlin COP.

    Inside this block ``current_pipeline()`` returns the active context
    and any ``@requires_context("pipeline")`` function can be called.

    Example::

        with pipeline_context("my_pipeline", **{"stores.neo4j.uri": "bolt://prod:7687"}) as ctx:
            ctx.set_override("log_level", "DEBUG")
            run_step(...)
    """
    ctx = PipelineContext(name=name, overrides=dict(overrides))
    token = _pipeline_ctx.set(ctx)
    try:
        yield ctx
    finally:
        _pipeline_ctx.reset(token)


@contextmanager
def step_context(step_name: str, **overrides: Any):
    """Activate a step context.

    Example::

        with step_context("raptor_pipeline.run", input_dir="my/data") as ctx:
            print(ctx.module)  # "raptor_pipeline"
            execute_current_step()
    """
    ctx = StepContext(step_name=step_name, overrides=dict(overrides))
    token = _step_ctx.set(ctx)
    try:
        yield ctx
    finally:
        _step_ctx.reset(token)


# ── Accessors ─────────────────────────────────────────────────


def current_pipeline() -> PipelineContext:
    """Retrieve the active pipeline context or raise ``RuntimeError``."""
    try:
        return _pipeline_ctx.get()
    except LookupError:
        raise RuntimeError(
            "❌ Нет активного PipelineContext! "
            "Оберните вызов в pipeline_context()."
        )


def current_step() -> StepContext:
    """Retrieve the active step context or raise ``RuntimeError``."""
    try:
        return _step_ctx.get()
    except LookupError:
        raise RuntimeError(
            "❌ Нет активного StepContext! "
            "Оберните вызов в step_context()."
        )


# ── Decorator: @requires_context ─────────────────────────────

# Registry of context vars by name — mirrors the COP decorator pattern.
_CONTEXT_REGISTRY: dict[str, ContextVar] = {
    "pipeline": _pipeline_ctx,
    "step": _step_ctx,
}


def requires_context(*context_names: str):
    """Decorator that checks required contexts are active before calling.

    Analogous to Kotlin ``context(LoggingContext, AuthContext)`` —
    but checked at runtime (Python limitation).

    Example::

        @requires_context("pipeline", "step")
        def run_business_logic():
            ctx = current_pipeline()
            step = current_step()
            ...

    If a context is missing, raises ``RuntimeError`` with a clear message.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            missing = []
            for name in context_names:
                cv = _CONTEXT_REGISTRY.get(name)
                if cv is None:
                    missing.append(f"{name} (не зарегистрирован)")
                else:
                    try:
                        cv.get()
                    except LookupError:
                        missing.append(name)

            if missing:
                raise RuntimeError(
                    f"❌ Функция {fn.__name__}() требует контексты: "
                    f"{', '.join(context_names)}.\n"
                    f"   Отсутствуют: {', '.join(missing)}.\n"
                    f"   Оберните вызов в соответствующий context manager."
                )
            return fn(*args, **kwargs)

        wrapper._required_contexts = context_names  # type: ignore[attr-defined]
        return wrapper

    return decorator


# ══════════════════════════════════════════════════════════════
# Per-Step Custom Contexts (COP Layer 2)
# ══════════════════════════════════════════════════════════════


class StepContextRegistry:
    """Registry of per-class ContextVars for custom step contexts.

    Each custom context class gets its own ``ContextVar``, created on first
    registration. This ensures multiple custom contexts can be active
    simultaneously (e.g. ``RaptorContext`` + ``ParseContext``).

    Usage::

        # Automatic — via custom_step_context():
        with custom_step_context(RaptorContext(max_concurrency=8)) as ctx:
            ctx.knowledge_graph_ready = True

        # Manual lookup:
        cv = StepContextRegistry.get_or_create(RaptorContext)
    """

    _vars: dict[type, ContextVar] = {}

    @classmethod
    def get_or_create(cls, ctx_class: type) -> ContextVar:
        """Get or create a ``ContextVar`` for the given context class."""
        if ctx_class not in cls._vars:
            cls._vars[ctx_class] = ContextVar(f"step_ctx_{ctx_class.__name__}")
        return cls._vars[ctx_class]

    @classmethod
    def has_active(cls, ctx_class: type) -> bool:
        """Check if a context of the given class is currently active."""
        if ctx_class not in cls._vars:
            return False
        try:
            cls._vars[ctx_class].get()
            return True
        except LookupError:
            return False

    @classmethod
    def clear(cls) -> None:
        """Remove all registered context vars (for testing)."""
        cls._vars.clear()


@contextmanager
def custom_step_context(ctx_instance: T) -> T:
    """Activate a custom step context.

    The context is available inside the ``with`` block via the yielded
    value **or** via ``current_step_ctx(ClassName)``.

    Example::

        @dataclass
        class RaptorContext:
            max_concurrency: int = 4
            knowledge_graph_ready: bool = False

        with custom_step_context(RaptorContext(max_concurrency=8)) as ctx:
            # Both work:
            print(ctx.max_concurrency)                        # via yield
            print(current_step_ctx(RaptorContext).max_concurrency)  # via accessor
    """
    cv = StepContextRegistry.get_or_create(type(ctx_instance))
    token = cv.set(ctx_instance)
    try:
        yield ctx_instance
    finally:
        cv.reset(token)


def current_step_ctx(ctx_class: Type[T]) -> T:
    """Retrieve the active custom step context by class.

    Type-safe accessor — returns an instance of ``ctx_class``.

    Example::

        ctx = current_step_ctx(RaptorContext)
        print(ctx.max_concurrency)

    Raises ``RuntimeError`` if no context of the given class is active.
    """
    cv = StepContextRegistry.get_or_create(ctx_class)
    try:
        return cv.get()
    except LookupError:
        raise RuntimeError(
            f"❌ Нет активного контекста {ctx_class.__name__}! "
            f"Убедитесь, что шаг-prerequisite, предоставляющий этот контекст, "
            f"уже выполнен. Активируйте через custom_step_context({ctx_class.__name__}(...))."
        )


def requires_step_context(*context_classes: type):
    """Decorator that checks required custom step contexts are active.

    If any of the specified context classes are not active, raises
    ``RuntimeError`` listing all missing contexts — indicating which
    prerequisite steps have not been executed.

    Example::

        @requires_step_context(RaptorContext, ParseContext)
        def build_concepts():
            raptor = current_step_ctx(RaptorContext)
            parsed = current_step_ctx(ParseContext)
            ...

    Call without the required contexts active::

        build_concepts()
        # RuntimeError: ❌ Функция build_concepts() требует контексты шагов:
        #    RaptorContext, ParseContext.
        #    Отсутствуют: RaptorContext, ParseContext.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            missing = []
            for cls in context_classes:
                if not StepContextRegistry.has_active(cls):
                    missing.append(cls.__name__)

            if missing:
                required_names = ", ".join(c.__name__ for c in context_classes)
                raise RuntimeError(
                    f"❌ Функция {fn.__name__}() требует контексты шагов: "
                    f"{required_names}.\n"
                    f"   Отсутствуют: {', '.join(missing)}.\n"
                    f"   Выполните шаги-prerequisites, предоставляющие эти контексты."
                )
            return fn(*args, **kwargs)

        wrapper._required_step_contexts = context_classes  # type: ignore[attr-defined]
        return wrapper

    return decorator
