"""Pydantic configuration schemas for Vault Parser.

Cross-field validations:
  - edit mode requires date
  - add-task action requires text
  - done/cancel/progress actions require query
  - output.max_items >= 1
  - sleep_quality/morning_mood in 1..10 range
  - energy values in 1..10 range
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Enums ─────────────────────────────────────────────────────

class Mode(str, Enum):
    list_tasks = "list-tasks"
    search = "search"
    stats = "stats"
    wellness = "wellness"
    people = "people"
    edit = "edit"
    parse = "parse"


class TaskStatus(str, Enum):
    open = "open"
    done = "done"
    cancelled = "cancelled"
    in_progress = "in_progress"


class Priority(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    normal = "normal"


class OutputFormat(str, Enum):
    table = "table"
    json = "json"
    csv = "csv"


class EditAction(str, Enum):
    create = "create"
    set_sleep = "set-sleep"
    set_energy = "set-energy"
    set_focus = "set-focus"
    add_task = "add-task"
    done = "done"
    cancel = "cancel"
    progress = "progress"
    set_gratitude = "set-gratitude"
    set_notes = "set-notes"
    set_problem = "set-problem"
    think_about = "think-about"
    read = "read"
    list = "list"
    delete = "delete"


# ── Sub-configs ───────────────────────────────────────────────

class VaultConfig(BaseModel):
    """Пути к Obsidian-вольту."""
    path: str = Field(..., description="Корневая директория с заметками")
    daily_dir: str = Field("daily", description="Подпапка ежедневных заметок")
    weekly_dir: str = Field("weekly", description="Подпапка недельных заметок")
    monthly_dir: str = Field("monthly", description="Подпапка месячных заметок")
    people_dir: Optional[str] = Field(None, description="Директория реестра людей")
    template_path: Optional[str] = Field(None, description="Путь к шаблону дневной заметки")


class OutputConfig(BaseModel):
    """Параметры вывода."""
    format: OutputFormat = Field(OutputFormat.table, description="Формат вывода")
    max_items: int = Field(50, ge=1, le=1000, description="Лимит строк")
    show_raw: bool = Field(False, description="Показывать исходный markdown")


# ── Root config ───────────────────────────────────────────────

class VaultParserConfig(BaseModel):
    """Корневая конфигурация Vault Parser.

    Cross-field validations:
      - edit mode requires date
      - add-task action requires text
      - done/cancel/progress actions require query
    """
    vault: VaultConfig

    # Swappable implementations (dotted path → validated via resolve_class)
    parser_class: str = Field(
        "vault_parser.parser.VaultParser",
        description="Dotted path к классу-реализации BaseVaultParser",
    )
    editor_class: str = Field(
        "vault_parser.writer.editor.DailyNoteEditor",
        description="Dotted path к классу-реализации BaseNoteEditor",
    )

    # Mode
    mode: Mode = Field(Mode.list_tasks, description="Режим работы")

    # Filters
    status: Optional[TaskStatus] = Field(None, description="Фильтр по статусу")
    priority: Optional[Priority] = Field(None, description="Фильтр по приоритету")
    date_range: Optional[str] = Field(None, description="Фильтр по дате")
    person: Optional[str] = Field(None, description="Фильтр по человеку")
    section: Optional[str] = Field(None, description="Фильтр по секции")
    query: Optional[str] = Field(None, description="Полнотекстовый поиск")

    # Edit mode
    action: Optional[EditAction] = Field(None, description="Действие в edit mode")
    date: Optional[str] = Field(None, description="Дата заметки (YYYY-MM-DD)")
    text: Optional[str] = Field(None, description="Текст задачи / секции")
    items: Optional[str] = Field(None, description="Элементы через ;")
    people_param: Optional[str] = Field(None, alias="people", description="Люди через ,")
    time_slot: Optional[str] = Field(None, description="Временной слот HH:MM-HH:MM")
    scheduled_date: Optional[str] = Field(None, description="Запланированная дата")
    start_date: Optional[str] = Field(None, description="Дата начала")
    due_date: Optional[str] = Field(None, description="Дедлайн")
    recurrence: Optional[str] = Field(None, description="Периодичность")
    what: Optional[str] = Field(None, description="Проблема: что")
    cause: Optional[str] = Field(None, description="Проблема: причина")
    consequences: Optional[str] = Field(None, description="Проблема: последствия")

    # Sleep fields
    bed_time_start: Optional[str] = Field(None)
    sleep_start: Optional[str] = Field(None)
    sleep_end: Optional[str] = Field(None)
    sleep_duration: Optional[str] = Field(None)
    sleep_quality: Optional[int] = Field(None, ge=1, le=10, description="Качество сна 1-10")
    quick_fall_asleep: Optional[bool] = Field(None)
    night_awakenings: Optional[bool] = Field(None)
    deep_sleep: Optional[bool] = Field(None)
    remembered_dreams: Optional[bool] = Field(None)
    no_nightmare: Optional[bool] = Field(None)
    morning_mood: Optional[int] = Field(None, ge=1, le=10, description="Утреннее настроение 1-10")
    no_phone: Optional[bool] = Field(None)
    physical_exercise: Optional[bool] = Field(None)
    late_dinner: Optional[bool] = Field(None)

    # Energy fields
    morning: Optional[int] = Field(None, ge=1, le=10, description="Утренняя энергия 1-10")
    day_energy: Optional[int] = Field(None, ge=1, le=10, description="Дневная энергия 1-10")
    evening: Optional[int] = Field(None, ge=1, le=10, description="Вечерняя энергия 1-10")

    # Output
    output: OutputConfig = Field(default_factory=OutputConfig)

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_edit_mode(self) -> "VaultParserConfig":
        if self.mode == Mode.edit:
            if not self.date:
                raise ValueError("mode=edit требует указания date (YYYY-MM-DD)")
            if self.action == EditAction.add_task and not self.text:
                raise ValueError("action=add-task требует указания text")
            if self.action in (EditAction.done, EditAction.cancel, EditAction.progress):
                if not self.query:
                    raise ValueError(
                        f"action={self.action.value} требует указания query "
                        f"для поиска задачи"
                    )
        if self.mode == Mode.search and not self.query:
            raise ValueError("mode=search требует указания query")
        return self

    @field_validator("date_range")
    @classmethod
    def validate_date_range(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid_shortcuts = {"today", "this_week", "this_month"}
        if v.lower() in valid_shortcuts:
            return v
        import re
        if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            return v
        if re.match(r"^\d{4}-\d{2}-\d{2}\.\.\d{4}-\d{2}-\d{2}$", v):
            return v
        raise ValueError(
            f"Неверный формат date_range: '{v}'. "
            f"Допустимо: today, this_week, this_month, YYYY-MM-DD, YYYY-MM-DD..YYYY-MM-DD"
        )
