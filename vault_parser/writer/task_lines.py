"""Task line formatting for Obsidian markdown."""
from __future__ import annotations

import re
from datetime import date

from vault_parser.models import Recurrence, TaskStatus

# Status checkbox markers
STATUS_CHECKBOX = {
    TaskStatus.OPEN: "- [ ] ",
    TaskStatus.DONE: "- [x] ",
    TaskStatus.CANCELLED: "- [-] ",
    TaskStatus.IN_PROGRESS: "- [/] ",
}

CHECKBOX_RE = re.compile(r"^- \[(.)\] ")


def format_task_line(
    text: str,
    *,
    status: TaskStatus = TaskStatus.OPEN,
    scheduled_date: date | None = None,
    start_date: date | None = None,
    due_date: date | None = None,
    time_slot: str | None = None,
    people: list[str] | None = None,
    completion_date: date | None = None,
    recurrence: str | Recurrence | None = None,
) -> str:
    """Build an Obsidian-compatible task line.

    Args:
        text: Task description.
        status: Checkbox status.
        scheduled_date: ``⏳ YYYY-MM-DD`` marker.
        start_date: ``🛫 YYYY-MM-DD`` marker.
        due_date: ``📅 YYYY-MM-DD`` marker.
        time_slot: ``HH:MM-HH:MM`` time range prefix.
        people: List of person filenames for ``[[Person]]`` links.
        completion_date: ``✅ YYYY-MM-DD`` (auto-set for done tasks).
        recurrence: ``🔁 every ...`` recurrence rule (str or Recurrence).

    Returns:
        Complete markdown line.
    """
    parts: list[str] = []

    # Checkbox
    parts.append(STATUS_CHECKBOX[status])

    # Time slot prefix
    if time_slot:
        parts.append(f"{time_slot} ")

    # Task text with people links inlined
    task_text = text
    if people:
        for person in people:
            if f"[[{person}" not in task_text:
                task_text += f" [[{person}]]"
    parts.append(task_text)

    # Start date
    if start_date:
        parts.append(f" 🛫 {start_date}")

    # Due date
    if due_date:
        parts.append(f" 📅 {due_date}")

    # Recurrence
    if recurrence:
        if isinstance(recurrence, Recurrence):
            parts.append(f" {recurrence}")
        else:
            parts.append(f" 🔁 {recurrence}")

    # Scheduled date
    if scheduled_date:
        parts.append(f" ⏳ {scheduled_date}")

    # Completion date (auto-set today for done tasks)
    if status == TaskStatus.DONE:
        comp = completion_date or date.today()
        parts.append(f" ✅ {comp}")

    return "".join(parts)
