"""Recurrence engine — parse and expand recurring task schedules.

Supports cron-like rules at day-level and above:
- ``every day`` / ``every 2 days``
- ``every week`` / ``every 2 weeks``
- ``every month`` / ``every 3 months``
- ``every mon,wed,fri`` — specific days of the week
- Optional ``until YYYY-MM-DD`` end date
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterator

from vault_parser.models import Recurrence

# Day-of-week name → weekday number (Monday=0)
_DOW_MAP = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
    # Russian short forms
    "пн": 0, "вт": 1, "ср": 2, "чт": 3, "пт": 4, "сб": 5, "вс": 6,
}

# Patterns for rule parsing
_EVERY_N_UNIT_RE = re.compile(
    r"every\s+(\d+)\s+(day|days|week|weeks|month|months)", re.IGNORECASE
)
_EVERY_UNIT_RE = re.compile(
    r"every\s+(day|week|month)", re.IGNORECASE
)
_EVERY_DAYS_RE = re.compile(
    r"every\s+([\w,]+)", re.IGNORECASE
)


def parse_recurrence(raw: str) -> Recurrence:
    """Parse a raw recurrence string into a Recurrence object.

    Args:
        raw: String like "every day", "every 2 weeks until 2025-12-31".

    Returns:
        Recurrence object with rule and optional until date.
    """
    until: date | None = None
    rule = raw.strip()

    # Extract "until YYYY-MM-DD"
    m = re.search(r"\s+until\s+(\d{4}-\d{2}-\d{2})", rule)
    if m:
        try:
            until = date.fromisoformat(m.group(1))
        except ValueError:
            pass
        rule = rule[:m.start()].strip()

    return Recurrence(rule=rule, until=until)


def next_occurrence(rec: Recurrence, after: date) -> date | None:
    """Calculate the next occurrence of a recurring task after a given date.

    Args:
        rec: Recurrence rule.
        after: Find the next occurrence strictly after this date.

    Returns:
        Next occurrence date, or None if the recurrence has ended.
    """
    for d in _generate_occurrences(rec, after + timedelta(days=1)):
        if rec.until and d > rec.until:
            return None
        return d
    return None


def expand_occurrences(
    rec: Recurrence,
    start: date,
    end: date,
) -> list[date]:
    """Expand all occurrences of a recurring task within a date range.

    Args:
        rec: Recurrence rule.
        start: Start of the range (inclusive).
        end: End of the range (inclusive).

    Returns:
        List of dates when the task should occur.
    """
    effective_end = min(end, rec.until) if rec.until else end
    result = []
    for d in _generate_occurrences(rec, start):
        if d > effective_end:
            break
        if d >= start:
            result.append(d)
    return result


def _generate_occurrences(rec: Recurrence, from_date: date) -> Iterator[date]:
    """Generate occurrence dates starting from from_date."""
    rule = rec.rule.lower().strip()

    # ── "every N days/weeks/months" ──────────────────────────────
    m = _EVERY_N_UNIT_RE.match(rule)
    if m:
        n = int(m.group(1))
        unit = m.group(2).rstrip("s")  # day/week/month
        yield from _gen_interval(from_date, n, unit)
        return

    # ── "every day/week/month" (N=1) ─────────────────────────────
    m = _EVERY_UNIT_RE.match(rule)
    if m:
        unit = m.group(1).lower()
        yield from _gen_interval(from_date, 1, unit)
        return

    # ── "every mon,wed,fri" — specific weekdays ──────────────────
    m = _EVERY_DAYS_RE.match(rule)
    if m:
        days_str = m.group(1).lower()
        weekdays = []
        for part in days_str.split(","):
            part = part.strip()
            if part in _DOW_MAP:
                weekdays.append(_DOW_MAP[part])

        if weekdays:
            yield from _gen_weekdays(from_date, weekdays)
            return

    # Unknown rule — no occurrences
    return


def _gen_interval(from_date: date, n: int, unit: str) -> Iterator[date]:
    """Generate dates at regular intervals."""
    current = from_date
    max_iterations = 3650  # ~10 years safety limit

    for _ in range(max_iterations):
        yield current
        if unit == "day":
            current += timedelta(days=n)
        elif unit == "week":
            current += timedelta(weeks=n)
        elif unit == "month":
            current = _add_months(current, n)
        else:
            break


def _gen_weekdays(from_date: date, weekdays: list[int]) -> Iterator[date]:
    """Generate dates matching specific weekdays."""
    weekdays_set = set(weekdays)
    current = from_date
    max_iterations = 3650

    for _ in range(max_iterations):
        if current.weekday() in weekdays_set:
            yield current
        current += timedelta(days=1)


def _add_months(d: date, months: int) -> date:
    """Add months to a date, clamping day to month end."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    day = min(d.day, max_day)
    return date(year, month, day)
