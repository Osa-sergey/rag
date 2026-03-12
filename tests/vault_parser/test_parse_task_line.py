"""Tests for parse_task_line — single checkbox line → VaultTask."""
from datetime import date

from vault_parser.models import Priority, TaskStatus, Recurrence
from vault_parser.parser import parse_task_line


class TestParseTaskLineBasicStatus:
    """Status detection from checkbox markers."""

    def test_open_task(self):
        task = parse_task_line("- [ ] стендап")
        assert task is not None
        assert task.status == TaskStatus.OPEN
        assert task.text == "стендап"

    def test_done_task(self):
        task = parse_task_line("- [x] ревью")
        assert task is not None
        assert task.status == TaskStatus.DONE

    def test_done_uppercase(self):
        task = parse_task_line("- [X] ревью")
        assert task.status == TaskStatus.DONE

    def test_cancelled_task(self):
        task = parse_task_line("- [-] отменили")
        assert task is not None
        assert task.status == TaskStatus.CANCELLED

    def test_in_progress_task(self):
        task = parse_task_line("- [/] делаю")
        assert task is not None
        assert task.status == TaskStatus.IN_PROGRESS


class TestParseTaskLinePriority:
    """Priority from emoji markers and section name."""

    def test_high_priority_emoji(self):
        task = parse_task_line("- [ ] 🔺 стендап")
        assert task.priority == Priority.HIGH

    def test_critical_priority_emoji(self):
        task = parse_task_line("- [ ] ⏫ критично")
        assert task.priority == Priority.CRITICAL

    def test_medium_priority_emoji(self):
        task = parse_task_line("- [ ] 🔼 среднее")
        assert task.priority == Priority.MEDIUM

    def test_low_priority_emoji(self):
        task = parse_task_line("- [ ] 🔽 низкое")
        assert task.priority == Priority.LOW

    def test_section_priority_main(self):
        task = parse_task_line("- [ ] задача", section="Основные дела")
        assert task.priority == Priority.MEDIUM

    def test_section_priority_secondary(self):
        task = parse_task_line("- [ ] задача", section="Второстепенные задачи")
        assert task.priority == Priority.LOW

    def test_emoji_overrides_section(self):
        task = parse_task_line("- [ ] ⏫ критично", section="Второстепенные задачи")
        assert task.priority == Priority.CRITICAL


class TestParseTaskLineMetadata:
    """Dates, time slots, wiki-links, tags, recurrence."""

    def test_time_slot(self):
        task = parse_task_line("- [ ] стендап 10:00-10:15")
        assert task.time_slot is not None
        assert str(task.time_slot) == "10:00-10:15"

    def test_wiki_links_people(self):
        task = parse_task_line("- [ ] встреча [[Иванов Иван]]")
        assert task.people == ["Иванов Иван"]

    def test_wiki_link_with_alias(self):
        task = parse_task_line("- [ ] встреча [[Иванов Иван|Ваня]]")
        assert task.people == ["Ваня"]

    def test_multiple_people(self):
        task = parse_task_line("- [ ] митинг [[Иванов Иван]] [[Петров Петр]]")
        assert len(task.people) == 2

    def test_scheduled_date(self):
        task = parse_task_line("- [ ] задача ⏳ 2025-09-01")
        assert task.scheduled_date == date(2025, 9, 1)

    def test_start_and_due_date(self):
        task = parse_task_line("- [ ] задача 🛫 2025-09-01 📅 2025-09-15")
        assert task.start_date == date(2025, 9, 1)
        assert task.due_date == date(2025, 9, 15)

    def test_completion_date(self):
        task = parse_task_line("- [x] задача ✅ 2025-09-05")
        assert task.completion_date == date(2025, 9, 5)

    def test_recurrence(self):
        task = parse_task_line("- [ ] стендап 🔁 every 2 weeks")
        assert task.recurrence is not None
        assert task.recurrence.rule == "every 2 weeks"
        assert task.recurrence.until is None

    def test_recurrence_with_until(self):
        task = parse_task_line(
            "- [ ] стендап 🔁 every day until 2025-12-31"
        )
        assert task.recurrence.until == date(2025, 12, 31)

    def test_tags(self):
        task = parse_task_line("- [ ] код #urgent #review")
        assert "urgent" in task.tags
        assert "review" in task.tags

    def test_source_metadata(self):
        src = date(2025, 12, 1)
        task = parse_task_line(
            "- [ ] задача", source_date=src, section="main"
        )
        assert task.source_date == src
        assert task.section == "main"


class TestParseTaskLineEdgeCases:
    """Non-task lines and edge cases."""

    def test_not_a_task(self):
        assert parse_task_line("обычная строка") is None

    def test_bullet_without_checkbox(self):
        assert parse_task_line("- просто буллет") is None

    def test_empty_string(self):
        assert parse_task_line("") is None

    def test_clean_text_strips_metadata(self):
        task = parse_task_line(
            "- [ ] 🔺 стендап 10:00-10:15 [[Иванов Иван]] ⏳ 2025-09-01"
        )
        assert "🔺" not in task.text
        assert "[[" not in task.text
        assert "10:00-10:15" not in task.text
        assert "⏳" not in task.text
        assert "стендап" in task.text
