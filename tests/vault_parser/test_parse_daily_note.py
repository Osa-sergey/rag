"""Tests for parse_daily_note — full file → DayNote."""
from datetime import date

from vault_parser.models import NoteType, TaskStatus, Priority
from vault_parser.parser import parse_daily_note


class TestParseDailyNote:
    """Full daily note parsing from a stub file."""

    def test_basic_metadata(self, daily_note_file):
        note = parse_daily_note(daily_note_file)
        assert note.date == date(2025, 12, 1)
        assert note.note_type == NoteType.DAILY

    def test_sleep_extracted(self, daily_note_file):
        note = parse_daily_note(daily_note_file)
        assert note.sleep.sleep_quality == 7
        assert note.sleep.bed_time_start == "23:00"
        assert note.sleep.deep_sleep is True
        assert note.sleep.late_dinner is True

    def test_energy_extracted(self, daily_note_file):
        note = parse_daily_note(daily_note_file)
        assert note.energy.morning_energy == 6
        assert note.energy.day_energy == 7
        assert note.energy.evening_energy == 5

    def test_all_tasks_parsed(self, daily_note_file):
        note = parse_daily_note(daily_note_file)
        tasks = note.all_tasks
        # 2 main + 2 secondary + 1 think_about = 5
        assert len(tasks) >= 4

    def test_task_statuses(self, daily_note_file):
        note = parse_daily_note(daily_note_file)
        statuses = {t.text: t.status for t in note.all_tasks}
        # "стендап" should be OPEN, "код ревью" should be DONE
        open_tasks = [t for t in note.all_tasks if t.status == TaskStatus.OPEN]
        done_tasks = [t for t in note.all_tasks if t.status == TaskStatus.DONE]
        assert len(open_tasks) >= 1
        assert len(done_tasks) >= 1

    def test_cancelled_task(self, daily_note_file):
        note = parse_daily_note(daily_note_file)
        cancelled = [t for t in note.all_tasks if t.status == TaskStatus.CANCELLED]
        assert len(cancelled) >= 1

    def test_in_progress_task(self, daily_note_file):
        note = parse_daily_note(daily_note_file)
        in_progress = [t for t in note.all_tasks if t.status == TaskStatus.IN_PROGRESS]
        assert len(in_progress) >= 1

    def test_sections_content(self, daily_note_file):
        note = parse_daily_note(daily_note_file)
        assert note.focus  # ["Модуль тестирования", "Ревью кода"]
        assert "тестирования" in note.focus[0].lower() or "тестирования" in " ".join(note.focus).lower()

    def test_gratitude_text(self, daily_note_file):
        note = parse_daily_note(daily_note_file)
        assert "много дел" in note.gratitude.lower()

    def test_notes_text(self, daily_note_file):
        note = parse_daily_note(daily_note_file)
        assert "интересный" in note.notes_text.lower()

    def test_empty_note(self, daily_dir):
        """A minimal note with just a date filename."""
        note_file = daily_dir / "2025-01-01.md"
        note_file.write_text("", encoding="utf-8")
        note = parse_daily_note(note_file)
        assert note.date == date(2025, 1, 1)
        assert len(note.all_tasks) == 0
