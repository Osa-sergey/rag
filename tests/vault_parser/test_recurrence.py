"""Tests for recurrence engine — parse, next_occurrence, expand.

Pure logic, no filesystem.
"""
from datetime import date

from vault_parser.models import Recurrence
from vault_parser.recurrence import (
    parse_recurrence,
    next_occurrence,
    expand_occurrences,
    _add_months,
)


class TestParseRecurrence:
    def test_every_day(self):
        rec = parse_recurrence("every day")
        assert rec.rule == "every day"
        assert rec.until is None

    def test_every_2_weeks(self):
        rec = parse_recurrence("every 2 weeks")
        assert rec.rule == "every 2 weeks"

    def test_with_until(self):
        rec = parse_recurrence("every day until 2025-12-31")
        assert rec.rule == "every day"
        assert rec.until == date(2025, 12, 31)

    def test_weekdays(self):
        rec = parse_recurrence("every mon,wed,fri")
        assert "mon,wed,fri" in rec.rule


class TestNextOccurrence:
    def test_daily(self):
        rec = Recurrence(rule="every day")
        nxt = next_occurrence(rec, date(2025, 1, 1))
        assert nxt == date(2025, 1, 2)

    def test_weekly(self):
        rec = Recurrence(rule="every week")
        # next_occurrence starts generating from after+1 day,
        # so from Jan 1 it yields Jan 2 (first occurrence in weekly gen)
        nxt = next_occurrence(rec, date(2025, 1, 1))
        assert nxt == date(2025, 1, 2)

    def test_respects_until(self):
        rec = Recurrence(rule="every day", until=date(2025, 1, 2))
        nxt = next_occurrence(rec, date(2025, 1, 2))
        assert nxt is None  # next would be Jan 3, after until

    def test_every_weekdays(self):
        rec = Recurrence(rule="every mon,wed,fri")
        # 2025-01-06 is Monday
        nxt = next_occurrence(rec, date(2025, 1, 6))
        assert nxt == date(2025, 1, 8)  # Wednesday


class TestExpandOccurrences:
    def test_expand_daily_range(self):
        rec = Recurrence(rule="every day")
        dates = expand_occurrences(rec, date(2025, 1, 1), date(2025, 1, 5))
        assert len(dates) == 5
        assert dates[0] == date(2025, 1, 1)
        assert dates[-1] == date(2025, 1, 5)

    def test_expand_2_weeks(self):
        rec = Recurrence(rule="every 2 weeks")
        dates = expand_occurrences(rec, date(2025, 1, 1), date(2025, 2, 28))
        # Jan 1, Jan 15, Jan 29, Feb 12, Feb 26
        assert len(dates) == 5

    def test_expand_respects_until(self):
        rec = Recurrence(rule="every day", until=date(2025, 1, 3))
        dates = expand_occurrences(rec, date(2025, 1, 1), date(2025, 1, 10))
        assert len(dates) == 3
        assert dates[-1] == date(2025, 1, 3)

    def test_expand_monthly(self):
        rec = Recurrence(rule="every month")
        dates = expand_occurrences(rec, date(2025, 1, 15), date(2025, 4, 15))
        assert len(dates) == 4  # Jan 15, Feb 15, Mar 15, Apr 15


class TestAddMonths:
    def test_simple(self):
        assert _add_months(date(2025, 1, 15), 1) == date(2025, 2, 15)

    def test_clamp_feb(self):
        result = _add_months(date(2025, 1, 31), 1)
        assert result == date(2025, 2, 28)

    def test_year_wrap(self):
        result = _add_months(date(2025, 11, 15), 3)
        assert result == date(2026, 2, 15)
