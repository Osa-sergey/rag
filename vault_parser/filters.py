"""Task filtering utilities for vault notes."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Sequence

from vault_parser.models import Priority, TaskStatus, VaultTask


def filter_tasks(
    tasks: Sequence[VaultTask],
    *,
    status: TaskStatus | str | None = None,
    priority: Priority | str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    person: str | None = None,
    section: str | None = None,
    query: str | None = None,
    has_time_slot: bool | None = None,
    has_scheduled: bool | None = None,
) -> list[VaultTask]:
    """Apply multiple filters to a list of tasks.

    All filters are AND-ed together. Pass ``None`` to skip a filter.
    """
    result = list(tasks)

    if status is not None:
        if isinstance(status, str):
            status = TaskStatus(status)
        result = [t for t in result if t.status == status]

    if priority is not None:
        if isinstance(priority, str):
            priority = Priority(priority)
        result = [t for t in result if t.priority == priority]

    if date_from is not None:
        result = [t for t in result if t.source_date and t.source_date >= date_from]

    if date_to is not None:
        result = [t for t in result if t.source_date and t.source_date <= date_to]

    if person is not None:
        p_lower = person.lower()
        result = [t for t in result if any(p.lower() == p_lower for p in t.people)]

    if section is not None:
        s_lower = section.lower()
        result = [t for t in result if s_lower in t.section.lower()]

    if query is not None:
        q = query.lower()
        result = [t for t in result if q in t.text.lower() or q in t.raw_line.lower()]

    if has_time_slot is not None:
        result = [t for t in result if (t.time_slot is not None) == has_time_slot]

    if has_scheduled is not None:
        result = [t for t in result if (t.scheduled_date is not None) == has_scheduled]

    return result


# ── Shorthand date presets ───────────────────────────────────────────

def tasks_today(tasks: Sequence[VaultTask]) -> list[VaultTask]:
    today = date.today()
    return filter_tasks(tasks, date_from=today, date_to=today)


def tasks_this_week(tasks: Sequence[VaultTask]) -> list[VaultTask]:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return filter_tasks(tasks, date_from=monday, date_to=sunday)


def tasks_this_month(tasks: Sequence[VaultTask]) -> list[VaultTask]:
    today = date.today()
    first_day = today.replace(day=1)
    if today.month == 12:
        last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return filter_tasks(tasks, date_from=first_day, date_to=last_day)


def overdue_tasks(tasks: Sequence[VaultTask]) -> list[VaultTask]:
    """Return open tasks with a scheduled date in the past."""
    today = date.today()
    return [
        t for t in tasks
        if t.status == TaskStatus.OPEN
        and t.scheduled_date is not None
        and t.scheduled_date < today
    ]
