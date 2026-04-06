"""
═══════════════════════════════════════════════════════════════════
 Context-Oriented Pipeline — обучающий модуль
═══════════════════════════════════════════════════════════════════

 Демонстрирует полный цикл:
   1. Контексты на базе contextvars (COP)
   2. Реестр шагов с context_class и requires_contexts
   3. Сборка пайплайна из YAML с depends_on
   4. Выполнение с вложенными контекстами (матрёшка)

 Запуск:
   python dagster_dsl/examples/test_context_pipeline.py

 Без внешних зависимостей — только stdlib + dataclasses + yaml.
═══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import functools
import textwrap
import yaml
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# ═══════════════════════════════════════════════════════════════
# 1. КОНТЕКСТЫ  —  COP на базе contextvars
# ═══════════════════════════════════════════════════════════════

# Пайплайн-контекст: «в каком пайплайне мы сейчас работаем»
_pipeline_var: ContextVar[Optional["PipelineCtx"]] = ContextVar(
    "pipeline_ctx", default=None
)


@dataclass
class PipelineCtx:
    """Контекст текущего пайплайна — имя + глобальные настройки."""
    name: str
    config: dict[str, Any] = field(default_factory=dict)


@contextmanager
def pipeline_context(name: str, **config):
    """Активирует контекст пайплайна на время выполнения.

    Пример::
        with pipeline_context("my_pipe", log_level="DEBUG") as ctx:
            print(ctx.name)  # "my_pipe"
    """
    ctx = PipelineCtx(name=name, config=config)
    token = _pipeline_var.set(ctx)
    try:
        yield ctx
    finally:
        _pipeline_var.reset(token)


def current_pipeline() -> PipelineCtx:
    """Получить текущий пайплайн-контекст (или ошибка)."""
    ctx = _pipeline_var.get()
    if ctx is None:
        raise RuntimeError("Нет активного пайплайна! Оберните код в pipeline_context().")
    return ctx


# ── Реестр кастомных контекстов шагов ─────────────────────────

class StepContextRegistry:
    """Реестр ContextVar для каждого класса кастомного контекста.

    Каждый класс (ParseContext, RaptorContext, ...) получает свою
    ContextVar. Это позволяет нескольким контекстам быть активными
    одновременно и не мешать друг другу.
    """
    _vars: dict[type, ContextVar] = {}

    @classmethod
    def get_or_create(cls, ctx_class: type) -> ContextVar:
        if ctx_class not in cls._vars:
            cls._vars[ctx_class] = ContextVar(
                f"step_ctx_{ctx_class.__name__}", default=None
            )
        return cls._vars[ctx_class]

    @classmethod
    def has_active(cls, ctx_class: type) -> bool:
        """Проверить, активен ли контекст данного класса."""
        cv = cls._vars.get(ctx_class)
        return cv is not None and cv.get(None) is not None


@contextmanager
def custom_step_context(instance):
    """Активирует кастомный контекст шага.

    Пример::
        with custom_step_context(ParseContext(output_dir="data/")) as ctx:
            ctx.files = ["a.yaml", "b.yaml"]
    """
    cv = StepContextRegistry.get_or_create(type(instance))
    token = cv.set(instance)
    try:
        yield instance
    finally:
        cv.reset(token)


def current_step_ctx(cls):
    """Получить активный контекст по классу (типобезопасно).

    Пример::
        ctx = current_step_ctx(ParseContext)
        print(ctx.output_dir)
    """
    cv = StepContextRegistry._vars.get(cls)
    if cv is None or cv.get(None) is None:
        raise RuntimeError(
            f"Нет активного контекста {cls.__name__}! "
            f"Убедитесь, что шаг-provider выполнен перед этим шагом."
        )
    return cv.get()


def requires_step_context(*classes):
    """Декоратор: функция упадёт, если нужные контексты не активны.

    Пример::
        @requires_step_context(ParseContext)
        def build_index():
            parse = current_step_ctx(ParseContext)
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            missing = [c.__name__ for c in classes
                       if not StepContextRegistry.has_active(c)]
            if missing:
                raise RuntimeError(
                    f"❌ {fn.__name__}() требует контексты: "
                    f"{', '.join(c.__name__ for c in classes)}.\n"
                    f"   Отсутствуют: {', '.join(missing)}."
                )
            return fn(*args, **kwargs)
        wrapper._required_step_contexts = classes
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════
# 2. РЕЕСТР ШАГОВ  —  регистрация функций как шагов пайплайна
# ═══════════════════════════════════════════════════════════════

@dataclass
class StepDef:
    """Определение шага: имя, функция, контекст который создаёт,
    контексты которые требует."""
    name: str
    fn: Callable
    description: str = ""
    context_class: Optional[type] = None
    requires_contexts: list[type] = field(default_factory=list)


# Глобальный реестр шагов
_step_registry: dict[str, StepDef] = {}


def register_step(
    name: str,
    *,
    description: str = "",
    context_class: Optional[type] = None,
    requires_contexts: Optional[list[type]] = None,
):
    """Декоратор: регистрирует функцию как шаг пайплайна.

    Пример::
        @register_step(
            "document_parser.parse",
            context_class=ParseContext,        # предоставляет
            requires_contexts=[],              # ничего не требует
        )
        def parse(config):
            ...
    """
    def decorator(fn):
        _step_registry[name] = StepDef(
            name=name,
            fn=fn,
            description=description,
            context_class=context_class,
            requires_contexts=requires_contexts or [],
        )
        return fn
    return decorator


# ═══════════════════════════════════════════════════════════════
# 3. BUILDER  —  сборка пайплайна из шагов + depends_on
# ═══════════════════════════════════════════════════════════════

@dataclass
class StepRef:
    """Ссылка на шаг в пайплайне."""
    id: str
    step_name: str
    config: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    context_class: Optional[type] = None

    def after(self, *deps: "StepRef") -> "StepRef":
        """Этот шаг выполняется ПОСЛЕ указанных."""
        for d in deps:
            if d.id not in self.depends_on:
                self.depends_on.append(d.id)
        return self


@dataclass
class PipelineBuilder:
    """Строитель пайплайна — добавляет шаги, устанавливает зависимости."""
    name: str
    _steps: dict[str, StepRef] = field(default_factory=dict)
    _global_config: dict[str, Any] = field(default_factory=dict)

    def config(self, **kv):
        """Глобальные настройки пайплайна."""
        self._global_config.update(kv)
        return self

    def step(self, step_name: str, step_id: str = "", **config) -> StepRef:
        """Добавить шаг в пайплайн."""
        sid = step_id or step_name.replace(".", "_")
        # Берём context_class из реестра шагов
        step_def = _step_registry.get(step_name)
        ctx_cls = step_def.context_class if step_def else None

        ref = StepRef(id=sid, step_name=step_name, config=config,
                      context_class=ctx_cls)
        self._steps[sid] = ref
        return ref

    def topology_sort(self) -> list[StepRef]:
        """Топологическая сортировка (алгоритм Кана)."""
        in_degree = {sid: 0 for sid in self._steps}
        adj: dict[str, list[str]] = defaultdict(list)
        for sid, ref in self._steps.items():
            for dep in ref.depends_on:
                adj[dep].append(sid)
                in_degree[sid] += 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        result = []
        while queue:
            current = queue.pop(0)
            result.append(self._steps[current])
            for neighbor in adj[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self._steps):
            raise ValueError("Цикл в графе зависимостей!")
        return result

    def describe(self) -> str:
        """Текстовое описание DAG."""
        lines = [f"Pipeline: {self.name}", ""]
        for ref in self.topology_sort():
            deps = f" (after: {', '.join(ref.depends_on)})" if ref.depends_on else ""
            ctx = f" [provides: {ref.context_class.__name__}]" if ref.context_class else ""
            step_def = _step_registry.get(ref.step_name)
            req = ""
            if step_def and step_def.requires_contexts:
                req = f" [requires: {', '.join(c.__name__ for c in step_def.requires_contexts)}]"
            lines.append(f"  → {ref.id}: {ref.step_name}{deps}{ctx}{req}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 4. YAML LOADER  —  загрузка пайплайна из YAML
# ═══════════════════════════════════════════════════════════════

def load_pipeline_yaml(yaml_text: str) -> PipelineBuilder:
    """Загрузить пайплайн из YAML строки.

    Формат::
        name: my_pipeline
        config:
          log_level: DEBUG
        steps:
          parse:
            module: document_parser.parse
            config:
              input_file: data.csv
          index:
            module: raptor.index
            depends_on: [parse]
    """
    raw = yaml.safe_load(yaml_text)
    builder = PipelineBuilder(name=raw["name"])

    if "config" in raw:
        builder.config(**raw["config"])

    step_refs = {}
    for step_id, step_cfg in raw["steps"].items():
        module = step_cfg["module"]
        if module not in _step_registry:
            raise ValueError(f"Шаг '{module}' не зарегистрирован!")
        config = step_cfg.get("config", {})
        ref = builder.step(module, step_id=step_id, **config)
        step_refs[step_id] = ref

    # Второй проход — зависимости
    for step_id, step_cfg in raw["steps"].items():
        for dep_id in step_cfg.get("depends_on", []):
            step_refs[step_id].after(step_refs[dep_id])

    return builder


# ═══════════════════════════════════════════════════════════════
# 5. RUNNER  —  выполнение с вложенными контекстами
# ═══════════════════════════════════════════════════════════════

def run_pipeline(builder: PipelineBuilder) -> dict[str, Any]:
    """Выполнить пайплайн: шаги в топологическом порядке,
    контексты вложены матрёшкой (upstream виден downstream).

    Схема вложенности::

        pipeline_context("my_pipe")
          └─ custom_step_context(ParseContext)    ← step "parse"
               ├─ execute parse()                 ← заполняет контекст
               └─ custom_step_context(RaptorCtx)  ← step "index"
                    └─ execute index()             ← видит ParseContext!
    """
    results = {}

    with ExitStack() as stack:
        # Активируем контекст пайплайна
        pipe = stack.enter_context(
            pipeline_context(builder.name, **builder._global_config)
        )

        for step_ref in builder.topology_sort():
            step_def = _step_registry[step_ref.step_name]

            # Проверяем requires_contexts
            all_required = step_def.requires_contexts + list(
                getattr(step_def.fn, "_required_step_contexts", ())
            )
            missing = [c.__name__ for c in all_required
                       if not StepContextRegistry.has_active(c)]
            if missing:
                raise RuntimeError(
                    f"❌ Шаг '{step_ref.id}' требует контексты: "
                    f"{', '.join(missing)}. Выполните prerequisites!"
                )

            # Активируем контекст шага ПЕРЕД выполнением
            # (остаётся активным для downstream-шагов)
            if step_ref.context_class:
                ctx = step_ref.context_class()
                stack.enter_context(custom_step_context(ctx))

            # Выполняем шаг
            merged_config = {**builder._global_config, **step_ref.config}
            print(f"  ▶ {step_ref.id}: {step_ref.step_name}")
            result = step_def.fn(merged_config)
            results[step_ref.id] = result
            print(f"  ✅ {step_ref.id} → {result}")

    return results


# ═══════════════════════════════════════════════════════════════
# 6. ПРИМЕР  —  полный цикл: определение → YAML → выполнение
# ═══════════════════════════════════════════════════════════════

# ── Кастомные контексты ───────────────────────────────────────

@dataclass
class ParseContext:
    """Контекст парсера: какие файлы обработаны."""
    output_dir: str = ""
    files_parsed: list[str] = field(default_factory=list)


@dataclass
class IndexContext:
    """Контекст индексатора: сколько документов проиндексировано."""
    index_name: str = ""
    docs_indexed: int = 0


@dataclass
class TopicContext:
    """Контекст topic modeling: найденные темы."""
    topics: list[str] = field(default_factory=list)


# ── Регистрация шагов ────────────────────────────────────────

@register_step(
    "document_parser.parse",
    description="Парсинг CSV → YAML файлы",
    context_class=ParseContext,               # ← предоставляет ParseContext
)
def parse_step(config):
    ctx = current_step_ctx(ParseContext)
    ctx.output_dir = config.get("output_dir", "parsed/")
    ctx.files_parsed = ["article_001.yaml", "article_002.yaml", "article_003.yaml"]
    return {"parsed": len(ctx.files_parsed), "output_dir": ctx.output_dir}


@register_step(
    "raptor.index",
    description="RAPTOR индексация в вектор-стор",
    context_class=IndexContext,               # ← предоставляет IndexContext
    requires_contexts=[ParseContext],         # ← требует ParseContext
)
def index_step(config):
    # Читаем данные из контекста парсера (upstream)
    parse = current_step_ctx(ParseContext)
    ctx = current_step_ctx(IndexContext)

    ctx.index_name = config.get("index_name", "default")
    ctx.docs_indexed = len(parse.files_parsed)

    print(f"    📂 Индексирую {ctx.docs_indexed} файлов из {parse.output_dir}")
    return {"indexed": ctx.docs_indexed, "index": ctx.index_name}


@register_step(
    "topic_modeler.train",
    description="Обучение тематической модели",
    context_class=TopicContext,               # ← предоставляет TopicContext
    requires_contexts=[ParseContext],         # ← требует ParseContext
)
def topics_step(config):
    parse = current_step_ctx(ParseContext)
    ctx = current_step_ctx(TopicContext)

    # «Извлекаем» темы из спарсенных файлов
    ctx.topics = ["Python", "ML", "DevOps"]
    print(f"    📊 Нашёл {len(ctx.topics)} тем в {len(parse.files_parsed)} файлах")
    return {"topics": ctx.topics}


@register_step(
    "concept_builder.build",
    description="Построение концептов из индекса + тем",
    requires_contexts=[IndexContext, TopicContext],  # ← требует ОБА
)
def concepts_step(config):
    index = current_step_ctx(IndexContext)
    topics = current_step_ctx(TopicContext)

    concepts = [f"{t}_concept" for t in topics.topics]
    print(f"    🧠 Построил {len(concepts)} концептов "
          f"(из {index.docs_indexed} документов, {len(topics.topics)} тем)")
    return {"concepts": concepts}


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # ── Вариант 1: Программная сборка  ────────────────────────

    print("=" * 60)
    print("  Вариант 1: Программная сборка пайплайна")
    print("=" * 60)

    builder = PipelineBuilder("habr_pipeline")
    builder.config(log_level="INFO")

    parse = builder.step("document_parser.parse",
                         output_dir="parsed_yaml")
    index = builder.step("raptor.index",
                         index_name="habr_index").after(parse)
    topics = builder.step("topic_modeler.train").after(parse)
    concepts = builder.step("concept_builder.build").after(index, topics)

    print()
    print(builder.describe())
    print()
    results = run_pipeline(builder)
    print()
    print(f"Результаты: {results}")

    # ── Вариант 2: Из YAML  ──────────────────────────────────

    print()
    print("=" * 60)
    print("  Вариант 2: Загрузка из YAML")
    print("=" * 60)

    yaml_text = textwrap.dedent("""\
        name: habr_yaml_pipeline
        config:
          log_level: DEBUG
        steps:
          parse:
            module: document_parser.parse
            config:
              output_dir: yaml_parsed
          index:
            module: raptor.index
            depends_on: [parse]
            config:
              index_name: yaml_index
          topics:
            module: topic_modeler.train
            depends_on: [parse]
          concepts:
            module: concept_builder.build
            depends_on: [index, topics]
    """)

    print()
    print("YAML:")
    print(yaml_text)

    builder2 = load_pipeline_yaml(yaml_text)
    print(builder2.describe())
    print()
    results2 = run_pipeline(builder2)
    print()
    print(f"Результаты: {results2}")

    # ── Вариант 3: Ошибка — missing context  ─────────────────

    print()
    print("=" * 60)
    print("  Вариант 3: Ошибка — не выполнен prerequisite")
    print("=" * 60)
    print()

    broken_builder = PipelineBuilder("broken_pipe")
    # Пытаемся запустить concept_builder без parse/index/topics
    broken_builder.step("concept_builder.build")

    try:
        run_pipeline(broken_builder)
    except RuntimeError as e:
        print(f"  {e}")

    print()
    print("✅ Демонстрация завершена!")
