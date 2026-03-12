"""Tests for filter_tasks and shorthand presets.

Pure logic tests — no filesystem, just in-memory VaultTask lists.
"""
from datetime import date, timedelta

import pytest

from vault_parser.models import Priority, TaskStatus, VaultTask, TimeSlot
from vault_parser.filters import (
    filter_tasks,
    overdue_tasks,
)
from tests.vault_parser.conftest import make_task


@pytest.fixture
def task_list():
    """A representative set of tasks for filtering."""
    return [
        make_task("стендап", TaskStatus.OPEN, Priority.HIGH,
                  section="Основные дела", source_date=date(2025, 12, 1),
                  people=["Иванов Иван"]),
        make_task("ревью", TaskStatus.DONE, Priority.MEDIUM,
                  section="Основные дела", source_date=date(2025, 12, 1)),
        make_task("тесты", TaskStatus.IN_PROGRESS, Priority.LOW,
                  section="Второстепенные задачи", source_date=date(2025, 12, 2)),
        make_task("отменено", TaskStatus.CANCELLED, Priority.NORMAL,
                  section="Основные дела", source_date=date(2025, 12, 3)),
        make_task("просрочено", TaskStatus.OPEN, Priority.HIGH,
                  source_date=date(2025, 11, 1),
                  scheduled_date=date(2025, 11, 15)),
    ]


class TestFilterByStatus:
    def test_open_only(self, task_list):
        result = filter_tasks(task_list, status=TaskStatus.OPEN)
        assert all(t.status == TaskStatus.OPEN for t in result)
        assert len(result) == 2

    def test_done_only(self, task_list):
        result = filter_tasks(task_list, status="done")
        assert len(result) == 1
        assert result[0].text == "ревью"


class TestFilterByPriority:
    def test_high_only(self, task_list):
        result = filter_tasks(task_list, priority=Priority.HIGH)
        assert len(result) == 2  # стендап + просрочено


class TestFilterByDateRange:
    def test_single_day(self, task_list):
        result = filter_tasks(
            task_list,
            date_from=date(2025, 12, 1),
            date_to=date(2025, 12, 1),
        )
        assert len(result) == 2  # стендап + ревью

    def test_range(self, task_list):
        result = filter_tasks(
            task_list,
            date_from=date(2025, 12, 1),
            date_to=date(2025, 12, 2),
        )
        assert len(result) == 3


class TestFilterByPerson:
    def test_person_match(self, task_list):
        result = filter_tasks(task_list, person="Иванов Иван")
        assert len(result) == 1
        assert result[0].text == "стендап"

    def test_case_insensitive(self, task_list):
        result = filter_tasks(task_list, person="иванов иван")
        assert len(result) == 1


class TestFilterByQuery:
    def test_text_match(self, task_list):
        result = filter_tasks(task_list, query="стенд")
        assert len(result) == 1

    def test_no_match(self, task_list):
        result = filter_tasks(task_list, query="xyz_not_found")
        assert len(result) == 0


class TestFilterCombined:
    def test_status_and_priority(self, task_list):
        result = filter_tasks(
            task_list, status=TaskStatus.OPEN, priority=Priority.HIGH
        )
        assert len(result) == 2


class TestOverdueTasks:
    def test_overdue(self, task_list):
        result = overdue_tasks(task_list)
        # "просрочено" has scheduled_date=2025-11-15, status=OPEN
        assert len(result) >= 1
        assert all(t.status == TaskStatus.OPEN for t in result)
        assert all(t.scheduled_date < date.today() for t in result)
