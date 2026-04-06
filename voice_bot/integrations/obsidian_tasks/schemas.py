"""Bot-layer data models for Obsidian task management.

ObsidianTask is a simplified, JSON-serializable view of a VaultTask,
designed for Telegram FSM state storage and inline keyboard rendering.

Fields mirror everything vault_parser can write via DailyNoteEditor.add_task().
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date

from pydantic import BaseModel


# ── Config ────────────────────────────────────────────────────


class ObsidianConfig(BaseModel):
    """Configuration for Obsidian vault integration."""

    vault_path: str = ""
    daily_notes_folder: str = "Daily"       # YYYY-MM-DD.md files location
    tasks_folder: str = "Tasks"             # fallback (not used by DailyNoteEditor)
    people_folder: str = "People"           # folder with person .md files
    default_date: str = "today"

    model_config = {"extra": "allow"}


# ── Bot task model ────────────────────────────────────────────


@dataclass
class ObsidianTask:
    """Simplified task model for Telegram FSM.

    All date fields are ISO strings (YYYY-MM-DD) or empty.
    people is a list of canonical names matching vault People/ files.
    """

    title: str
    date: str = ""              # due date (📅 YYYY-MM-DD)
    status: str = "todo"        # "todo" | "done" | "cancelled"
    priority: str = "normal"    # "high" | "medium" | "low" | "normal"
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    # Extended task fields (all optional)
    start_date: str = ""        # 🛫 YYYY-MM-DD  — when work on the task begins
    scheduled_date: str = ""    # ⏳ YYYY-MM-DD  — scheduled/deferred date
    time_slot: str = ""         # HH:MM-HH:MM
    recurrence: str = ""        # "every day" | "every mon,wed,fri" | etc.
    people: list[str] = field(default_factory=list)  # canonical vault person names

    # Location metadata (set by vault when reading, used for edits/deletes)
    file_path: str = ""
    line_number: int = -1       # logical task index within the day

    # ── Serialization (FSM state) ──────────────────────────────

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, s: str) -> "ObsidianTask":
        d = json.loads(s)
        d.setdefault("tags", [])
        d.setdefault("people", [])
        d.setdefault("start_date", "")
        d.setdefault("scheduled_date", "")
        d.setdefault("time_slot", "")
        d.setdefault("recurrence", "")
        return cls(**d)

    # ── Display ────────────────────────────────────────────────

    def format_preview(self, index: int | None = None) -> str:
        """One-liner for task list view."""
        status_emoji = {"todo": "☐", "done": "✅", "cancelled": "❌"}.get(self.status, "☐")
        priority_str = {
            "high": " ⏫", "medium": " 🔼", "low": " 🔽", "normal": "",
        }.get(self.priority, "")
        date_str  = f"  📅 _{self.date}_" if self.date else ""
        tags_str  = " " + " ".join(f"#{t}" for t in self.tags) if self.tags else ""
        peop_str  = " " + " ".join(f"[[{p}]]" for p in self.people) if self.people else ""
        prefix    = f"*{index}.* " if index is not None else ""
        return f"{prefix}{status_emoji} {self.title}{priority_str}{tags_str}{peop_str}{date_str}"

    def format_full_preview(self) -> str:
        """Full card for confirmation screen."""
        priority_label = {
            "high": "⏫ Высокий", "medium": "🔼 Средний",
            "low": "🔽 Низкий",   "normal": "📋 Обычный",
        }.get(self.priority, "📋 Обычный")

        lines = ["*📋 Новая задача — подтвердите:*\n"]
        lines.append(f"📌 *{self.title}*")
        lines.append(f"🏷 Приоритет: {priority_label}")
        lines.append(f"📅 Срок (due): {self.date or '—'}")
        if self.start_date:
            lines.append(f"🛫 Начало: {self.start_date}")
        if self.scheduled_date:
            lines.append(f"⏳ Запланировано: {self.scheduled_date}")
        if self.time_slot:
            lines.append(f"🕐 Время: {self.time_slot}")
        if self.recurrence:
            lines.append(f"🔁 Повтор: {self.recurrence}")
        if self.people:
            lines.append(f"👤 Люди: {', '.join(self.people)}")
        if self.tags:
            lines.append(f"🔖 Теги: {' '.join(f'#{t}' for t in self.tags)}")
        if self.notes:
            lines.append(f"📝 {self.notes}")
        return "\n".join(lines)


# ── LLM extraction models ─────────────────────────────────────


@dataclass
class ExtractedTask:
    """Task data returned by the LLM extractor."""

    title: str
    date_raw: str = ""          # as spoken: "завтра", "в пятницу"
    date: str = ""              # YYYY-MM-DD (DateParser resolves date_raw)
    priority: str = "normal"
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    # Extended fields
    start_date_raw: str = ""    # "со следующей недели", "с понедельника"
    start_date: str = ""
    scheduled_date_raw: str = ""
    scheduled_date: str = ""
    time_slot: str = ""         # "10:00-11:00" or ""
    recurrence: str = ""        # "every day", "every monday" etc.
    people: list[str] = field(default_factory=list)  # names as spoken


@dataclass
class ExtractedTaskQuery:
    """Query parameters for task_show intent."""

    date_raw: str = ""
    date: str = ""
    date_end: str = ""
    show_done: bool = False


@dataclass
class ExtractedTaskUpdate:
    """Update request: which task to find + what to change."""

    search_query: str = ""       # keywords to match task title
    search_date: str = ""        # YYYY-MM-DD to narrow search (optional)
    # Fields to change (empty string / empty list = don't change)
    new_title: str = ""
    new_date: str = ""           # YYYY-MM-DD
    new_priority: str = ""       # high|medium|low|normal
    new_recurrence: str = ""
    new_time_slot: str = ""
    people_add: list[str] = field(default_factory=list)
    people_remove: list[str] = field(default_factory=list)


# ── Agenda model ──────────────────────────────────────────────


@dataclass
class AgendaData:
    """Structured day agenda built from vault daily note."""

    day: date
    weekday: str = ""                              # «понедельник»
    focus: list[str] = field(default_factory=list)  # «Фокус дня» bullet items
    tasks_by_priority: dict = field(default_factory=dict)  # {"high": [ObsidianTask], ...}
    total: int = 0
    done: int = 0
    open: int = 0
    people_involved: list[str] = field(default_factory=list)  # unique people
    summary: str = ""                               # LLM-generated 1–3 sentence summary
