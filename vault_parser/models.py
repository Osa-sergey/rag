"""Data models for parsed Obsidian vault notes."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from enum import Enum
from pathlib import Path
from typing import Any


# ── Enums ────────────────────────────────────────────────────────────
class TaskStatus(str, Enum):
    """Obsidian checkbox status."""
    OPEN = "open"           # - [ ]
    DONE = "done"           # - [x]
    CANCELLED = "cancelled" # - [-]
    IN_PROGRESS = "in_progress"  # - [/]


class Priority(str, Enum):
    """Task priority inferred from section and/or emoji markers."""
    CRITICAL = "critical"   # ⏫
    HIGH = "high"           # 🔺  or  «Фокус дня»
    MEDIUM = "medium"       # 🔼  or  «Основные дела»
    LOW = "low"             # 🔽  or  «Второстепенные задачи»
    NORMAL = "normal"       # no marker, or other sections


class NoteType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# ── Value Objects ────────────────────────────────────────────────────
@dataclass(frozen=True)
class WikiLink:
    """Parsed ``[[Target|Alias]]`` link."""
    target: str
    alias: str | None = None

    def display_name(self) -> str:
        return self.alias if self.alias else self.target

    def __str__(self) -> str:
        if self.alias:
            return f"[[{self.target}|{self.alias}]]"
        return f"[[{self.target}]]"


@dataclass(frozen=True)
class TimeSlot:
    """Optional time range for a task, e.g. ``11:30-12:00``."""
    start: time
    end: time

    def __str__(self) -> str:
        return f"{self.start:%H:%M}-{self.end:%H:%M}"


@dataclass
class SleepData:
    """Sleep metrics extracted from daily note YAML frontmatter."""
    bed_time_start: str | None = None
    sleep_start: str | None = None
    sleep_end: str | None = None
    sleep_duration: str | None = None
    sleep_quality: int | None = None
    quick_fall_asleep: bool = False
    night_awakenings: bool = False
    deep_sleep: bool = False
    remembered_dreams: bool = False
    no_nightmare: bool = False
    morning_mood: int | None = None
    no_phone: bool = False
    physical_exercise: bool = False
    late_dinner: bool = False

    def duration_minutes(self) -> int | None:
        """Parse ``H:MM`` or ``HH:MM`` into total minutes."""
        if not self.sleep_duration:
            return None
        parts = self.sleep_duration.split(":")
        if len(parts) != 2:
            return None
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            return None


@dataclass
class EnergyData:
    """Energy levels extracted from daily note YAML frontmatter."""
    morning_energy: int | None = None
    day_energy: int | None = None
    evening_energy: int | None = None

    def average(self) -> float | None:
        vals = [v for v in (self.morning_energy, self.day_energy, self.evening_energy) if v is not None]
        return sum(vals) / len(vals) if vals else None


# ── Task ─────────────────────────────────────────────────────────────
@dataclass
class VaultTask:
    """A single task extracted from an Obsidian note."""
    text: str                             # cleaned text (no checkbox / emoji)
    status: TaskStatus = TaskStatus.OPEN
    priority: Priority = Priority.NORMAL
    completion_date: date | None = None   # ✅ YYYY-MM-DD
    scheduled_date: date | None = None    # ⏳ YYYY-MM-DD
    time_slot: TimeSlot | None = None     # 11:30-12:00
    source_file: Path | None = None
    source_date: date | None = None       # date from filename
    section: str = ""                     # section heading the task lives under
    wiki_links: list[WikiLink] = field(default_factory=list)
    people: list[str] = field(default_factory=list)  # display names from wiki-links
    tags: list[str] = field(default_factory=list)     # #tag items
    inline_comment: str | None = None     # text in parentheses at the end
    raw_line: str = ""                    # original markdown line

    # Convenience
    @property
    def is_open(self) -> bool:
        return self.status == TaskStatus.OPEN

    @property
    def is_done(self) -> bool:
        return self.status == TaskStatus.DONE

    def as_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "status": self.status.value,
            "priority": self.priority.value,
            "completion_date": str(self.completion_date) if self.completion_date else None,
            "scheduled_date": str(self.scheduled_date) if self.scheduled_date else None,
            "time_slot": str(self.time_slot) if self.time_slot else None,
            "source_file": str(self.source_file) if self.source_file else None,
            "source_date": str(self.source_date) if self.source_date else None,
            "section": self.section,
            "wiki_links": [str(wl) for wl in self.wiki_links],
            "people": self.people,
            "tags": self.tags,
            "inline_comment": self.inline_comment,
        }


# ── Reflection blocks (used in weekly / monthly) ────────────────────
@dataclass
class ReflectionBlock:
    """A named section of free-form text (achievements, insights, problems, etc.)."""
    heading: str
    content: str


# ── Note-level containers ────────────────────────────────────────────
@dataclass
class DayNote:
    """Fully parsed daily note."""
    date: date
    source_file: Path
    note_type: NoteType = NoteType.DAILY

    # Frontmatter
    sleep: SleepData = field(default_factory=SleepData)
    energy: EnergyData = field(default_factory=EnergyData)
    raw_frontmatter: dict[str, Any] = field(default_factory=dict)

    # Sections
    focus: list[str] = field(default_factory=list)          # «Фокус дня» bullet items
    tasks: list[VaultTask] = field(default_factory=list)     # all tasks (Основные + Второстепенные + Надо подумать)
    gratitude: str = ""                                      # «Чему я рад и что получилось»
    problems: list[ReflectionBlock] = field(default_factory=list)  # «Что пошло не так» sub-sections
    notes_text: str = ""                                     # «Заметки»
    think_about: list[VaultTask] = field(default_factory=list)  # «Надо подумать о»

    # Derived
    wiki_links: list[WikiLink] = field(default_factory=list)

    @property
    def all_tasks(self) -> list[VaultTask]:
        return self.tasks + self.think_about

    @property
    def open_tasks(self) -> list[VaultTask]:
        return [t for t in self.all_tasks if t.is_open]

    @property
    def done_tasks(self) -> list[VaultTask]:
        return [t for t in self.all_tasks if t.is_done]


@dataclass
class WeeklyNote:
    """Parsed weekly note."""
    year: int
    week: int
    source_file: Path
    note_type: NoteType = NoteType.WEEKLY

    # Tasks from «Список задач» section
    tasks: list[VaultTask] = field(default_factory=list)

    # Structured review sections
    focus: list[str] = field(default_factory=list)               # «Основной фокус»
    achievements: list[str] = field(default_factory=list)        # «Ключевые достижения»
    insights: list[str] = field(default_factory=list)            # «Новые инсайты»
    plan_deviations: list[str] = field(default_factory=list)     # «Причины отклонений»
    problems: list[str] = field(default_factory=list)            # «Что тормозило»
    solutions: list[str] = field(default_factory=list)           # «Возможные решения»
    reflections: list[ReflectionBlock] = field(default_factory=list)

    # Week mark (1-10 self-assessment)
    week_mark: int | None = None

    # Findings
    resources: list[str] = field(default_factory=list)           # links / books / videos

    wiki_links: list[WikiLink] = field(default_factory=list)

    @property
    def date_label(self) -> str:
        return f"{self.year}-W{self.week:02d}"


@dataclass
class MonthlyNote:
    """Parsed monthly note."""
    year: int
    month: int
    source_file: Path
    note_type: NoteType = NoteType.MONTHLY

    # Sections (all free-text / bullet content)
    dynamics: str = ""              # «Общая динамика месяца»
    achievements: list[str] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    plan_vs_fact: str = ""          # «Сравнение планов и факта»
    skills: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    solutions: list[str] = field(default_factory=list)
    self_assessment: str = ""       # includes score
    month_score: int | None = None  # 1-10
    resources: list[str] = field(default_factory=list)
    reflection: str = ""            # «Рефлексия»

    wiki_links: list[WikiLink] = field(default_factory=list)

    @property
    def date_label(self) -> str:
        return f"{self.year}-{self.month:02d}"
