"""Obsidian vault adapter for the voice bot.

Wraps vault_parser.DailyNoteEditor (file I/O) and PeopleRegistry (person lookup).
Resolves spoken person names to canonical vault names before writing.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

from vault_parser.models import Priority, TaskStatus, VaultTask
from vault_parser.parser import parse_daily_note
from vault_parser.people import PeopleRegistry, load_people_registry
from vault_parser.writer import DailyNoteEditor

from voice_bot.integrations.obsidian_tasks.schemas import AgendaData, ObsidianConfig, ObsidianTask

logger = logging.getLogger(__name__)

# ── Priority / status mappings ────────────────────────────────

_PRIORITY_TO_BOT = {
    Priority.CRITICAL: "high",
    Priority.HIGH:     "high",
    Priority.MEDIUM:   "medium",
    Priority.LOW:      "low",
    Priority.NORMAL:   "normal",
}

_BOT_TO_VAULT_PRIORITY = {
    "high":   Priority.HIGH,
    "medium": Priority.MEDIUM,
    "low":    Priority.LOW,
    "normal": Priority.NORMAL,
}

_STATUS_TO_BOT = {
    TaskStatus.OPEN:        "todo",
    TaskStatus.DONE:        "done",
    TaskStatus.CANCELLED:   "cancelled",
    TaskStatus.IN_PROGRESS: "todo",
}

_BOT_SECTION = {
    "high":   "main",
    "medium": "main",
    "low":    "secondary",
    "normal": "main",
}


class ObsidianVault:
    """Voice-bot facade over vault_parser DailyNoteEditor + PeopleRegistry.

    Task flow:
      1. LLM extracts task text with people names as spoken.
      2. resolve_people() maps spoken names → canonical vault names.
      3. add_task() writes the note using DailyNoteEditor.add_task().

    Usage::

        vault = ObsidianVault(config)
        # Optionally load people registry for name resolution
        vault.load_people_registry()

        task.people = vault.resolve_people(["Маша", "Котиков"])
        vault.add_task(task)
        tasks = vault.read_tasks(date.today())
        vault.mark_done(tasks[0])
    """

    def __init__(self, config: ObsidianConfig) -> None:
        self._root = Path(config.vault_path)
        self._config = config
        daily_dir = self._root / config.daily_notes_folder
        daily_dir.mkdir(parents=True, exist_ok=True)
        self._editor = DailyNoteEditor(daily_dir)
        self._registry: PeopleRegistry | None = None
        logger.info(
            "ObsidianVault ready (vault=%s, daily=%s)",
            self._root, daily_dir,
        )

    # ── People registry ────────────────────────────────────────

    def load_people_registry(self) -> None:
        """Load the People registry from vault. Safe to call even if folder missing."""
        people_dir = self._root / self._config.people_folder
        if people_dir.exists():
            self._registry = load_people_registry(people_dir)
            logger.info(
                "PeopleRegistry loaded: %d people from %s",
                len(self._registry), people_dir,
            )
        else:
            logger.warning("People directory not found: %s", people_dir)
            self._registry = None

    def all_people_names(self) -> list[str]:
        """Return all canonical person names (for inline keyboard dropdowns)."""
        if not self._registry:
            return []
        return self._registry.all_names()

    def resolve_people(self, spoken_names: list[str]) -> list[str]:
        """Map spoken/partial names to canonical vault person names.

        Falls back to the spoken name if not found in the registry.
        """
        if not self._registry or not spoken_names:
            return spoken_names
        resolved = []
        for name in spoken_names:
            person = self._registry.lookup(name)
            resolved.append(person.name if person else name)
        return resolved

    # ── Read ───────────────────────────────────────────────────

    def read_tasks(self, day: date, include_done: bool = True) -> list[ObsidianTask]:
        """Read all tasks for a specific day via vault_parser."""
        if not self._editor.exists(day):
            return []
        try:
            vault_tasks: list[VaultTask] = self._editor.list_tasks(day)
        except Exception as e:
            logger.warning("Failed to read tasks for %s: %s", day, e)
            return []

        result = []
        for i, vt in enumerate(vault_tasks):
            if not include_done and vt.status == TaskStatus.DONE:
                continue
            bot_task = self._vault_to_bot(vt)
            bot_task.file_path = str(self._editor._path(day))
            bot_task.line_number = i
            result.append(bot_task)

        logger.debug("Read %d tasks for %s", len(result), day)
        return result

    def read_tasks_range(
        self,
        start: date,
        end: date,
        include_done: bool = False,
    ) -> dict[date, list[ObsidianTask]]:
        result: dict[date, list[ObsidianTask]] = {}
        current = start
        while current <= end:
            tasks = self.read_tasks(current, include_done=include_done)
            if tasks:
                result[current] = tasks
            current += timedelta(days=1)
        return result

    # ── Write ──────────────────────────────────────────────────

    def add_task(self, task: ObsidianTask) -> ObsidianTask:
        """Add a task to the appropriate daily note, passing all enriched fields.

        Creates the note from built-in template if it doesn't exist.
        """
        task_date = self._resolve_date(task.date or task.scheduled_date or "")
        if not self._editor.exists(task_date):
            self._editor.create_from_template(task_date)

        section    = _BOT_SECTION.get(task.priority, "main")
        due_date   = date.fromisoformat(task.date) if task.date else None
        start_date = date.fromisoformat(task.start_date) if task.start_date else None
        sched_date = date.fromisoformat(task.scheduled_date) if task.scheduled_date else None

        # Resolve people names to canonical names
        people = self.resolve_people(task.people) if task.people else None

        self._editor.add_task(
            task_date,
            task.title,
            section=section,
            due_date=due_date,
            start_date=start_date,
            scheduled_date=sched_date,
            time_slot=task.time_slot or None,
            recurrence=task.recurrence or None,
            people=people,
        )

        task.file_path = str(self._editor._path(task_date))
        logger.info(
            "Added task '%s' to %s [%s] people=%s recurrence=%s",
            task.title, task_date, section, people, task.recurrence,
        )
        return task

    def mark_done(self, task: ObsidianTask) -> bool:
        task_date = self._resolve_date(task.date)
        if not self._editor.exists(task_date):
            return False
        result = self._editor.update_task_status(task_date, task.title, TaskStatus.DONE)
        if result:
            task.status = "done"
        return result

    def delete_task(self, task: ObsidianTask) -> bool:
        task_date = self._resolve_date(task.date)
        if not self._editor.exists(task_date):
            return False
        return self._editor.delete_task(task_date, task.title)

    def update_task(self, old_task: ObsidianTask, new_task: ObsidianTask) -> bool:
        """Delete old and re-add new (simplest atomic approach)."""
        self.delete_task(old_task)
        self.add_task(new_task)
        return True

    # ── Agenda ──────────────────────────────────────────────────

    _WEEKDAY_RU = [
        "понедельник", "вторник", "среда", "четверг",
        "пятница", "суббота", "воскресенье",
    ]

    def build_agenda(self, day: date) -> AgendaData:
        """Build a structured agenda from a daily note using vault_parser.

        Parses the full daily note to extract focus items, all tasks (grouped
        by priority, sorted by time_slot), and unique people involved.
        """
        note_path = self._editor._path(day)
        weekday = self._WEEKDAY_RU[day.weekday()]

        # Empty agenda if note doesn't exist
        if not note_path.exists():
            return AgendaData(day=day, weekday=weekday)

        try:
            day_note = parse_daily_note(note_path)
        except Exception as e:
            logger.warning("Failed to parse daily note for %s: %s", day, e)
            return AgendaData(day=day, weekday=weekday)

        # Focus items
        focus = list(day_note.focus)

        # Collect all tasks as bot models
        all_bot_tasks = [self._vault_to_bot(vt) for vt in day_note.all_tasks]

        # Sort: tasks with time_slot first (ascending), rest after
        def _sort_key(t: ObsidianTask):
            return (0 if t.time_slot else 1, t.time_slot or "")
        all_bot_tasks.sort(key=_sort_key)

        # Group by priority
        groups: dict[str, list[ObsidianTask]] = {}
        for t in all_bot_tasks:
            groups.setdefault(t.priority, []).append(t)

        # Ordered priority groups
        priority_order = ["high", "medium", "normal", "low"]
        tasks_by_priority = {
            p: groups[p] for p in priority_order if p in groups
        }

        # Stats
        total = len(all_bot_tasks)
        done = sum(1 for t in all_bot_tasks if t.status == "done")
        open_count = total - done

        # Unique people
        people_set: set[str] = set()
        for t in all_bot_tasks:
            people_set.update(t.people)

        return AgendaData(
            day=day,
            weekday=weekday,
            focus=focus,
            tasks_by_priority=tasks_by_priority,
            total=total,
            done=done,
            open=open_count,
            people_involved=sorted(people_set),
        )

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _resolve_date(date_str: str) -> date:
        if not date_str:
            return date.today()
        try:
            return date.fromisoformat(date_str)
        except ValueError:
            return date.today()

    @staticmethod
    def _vault_to_bot(vt: VaultTask) -> ObsidianTask:
        """Convert VaultTask → ObsidianTask, mapping all enriched fields."""
        due = vt.due_date or vt.source_date or date.today()
        return ObsidianTask(
            title=vt.text,
            date=due.isoformat(),
            status=_STATUS_TO_BOT.get(vt.status, "todo"),
            priority=_PRIORITY_TO_BOT.get(vt.priority, "normal"),
            tags=list(vt.tags),
            notes=vt.inline_comment or "",
            start_date=vt.start_date.isoformat() if vt.start_date else "",
            scheduled_date=vt.scheduled_date.isoformat() if vt.scheduled_date else "",
            time_slot=str(vt.time_slot) if vt.time_slot else "",
            recurrence=str(vt.recurrence) if vt.recurrence else "",
            people=[wl.display_name() for wl in vt.wiki_links],
        )
