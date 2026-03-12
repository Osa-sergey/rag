"""Tests for DailyNoteEditor — CRUD, tasks, wellness sections.

All tests use tmp_path — no real Obsidian vault.
"""
from datetime import date

from vault_parser.models import TaskStatus
from vault_parser.writer.editor import DailyNoteEditor


class TestEditorCreateAndExists:
    """Note creation and existence checks."""

    def test_exists_false(self, editor):
        assert editor.exists("2025-12-01") is False

    def test_create_and_exists(self, editor):
        editor.create_from_template("2025-12-01")
        assert editor.exists("2025-12-01") is True

    def test_create_generates_file(self, editor, daily_dir):
        editor.create_from_template("2025-12-01")
        assert (daily_dir / "2025-12-01.md").exists()


class TestEditorRead:
    """Reading notes."""

    def test_read_nonexistent_returns_none(self, editor):
        assert editor.read("2099-01-01") is None

    def test_read_returns_daynote(self, editor_with_note):
        note = editor_with_note.read("2025-12-01")
        assert note is not None
        assert note.date == date(2025, 12, 1)

    def test_read_raw_returns_string(self, editor_with_note):
        raw = editor_with_note.read_raw("2025-12-01")
        assert isinstance(raw, str)
        assert "---" in raw

    def test_read_raw_nonexistent(self, editor):
        assert editor.read_raw("2099-01-01") is None


class TestEditorTasks:
    """Task add / update / list / delete."""

    def test_add_task(self, editor):
        editor.create_from_template("2025-12-01")
        editor.add_task("2025-12-01", "новая задача", section="main")
        raw = editor.read_raw("2025-12-01")
        assert "новая задача" in raw

    def test_add_task_with_people(self, editor):
        editor.create_from_template("2025-12-01")
        editor.add_task(
            "2025-12-01", "митинг",
            section="main",
            people=["Иванов Иван"],
            time_slot="10:00-10:30",
        )
        raw = editor.read_raw("2025-12-01")
        assert "[[Иванов Иван]]" in raw
        assert "10:00-10:30" in raw

    def test_update_task_done(self, editor_with_note):
        result = editor_with_note.update_task_status(
            "2025-12-01", "стендап", TaskStatus.DONE
        )
        assert result is True
        raw = editor_with_note.read_raw("2025-12-01")
        # The line should now have [x] instead of [ ]
        assert "[x]" in raw or "- [x]" in raw

    def test_update_task_cancel(self, editor_with_note):
        result = editor_with_note.update_task_status(
            "2025-12-01", "стендап", TaskStatus.CANCELLED
        )
        assert result is True

    def test_update_nonexistent_task(self, editor_with_note):
        result = editor_with_note.update_task_status(
            "2025-12-01", "несуществующая задача xyz", TaskStatus.DONE
        )
        assert result is False

    def test_list_tasks(self, editor_with_note):
        tasks = editor_with_note.list_tasks("2025-12-01")
        assert isinstance(tasks, list)
        assert len(tasks) >= 4  # main(2) + secondary(2) + think_about(1)

    def test_delete_task(self, editor_with_note):
        result = editor_with_note.delete_task("2025-12-01", "стендап")
        assert result is True
        raw = editor_with_note.read_raw("2025-12-01")
        assert "стендап" not in raw

    def test_delete_nonexistent(self, editor_with_note):
        result = editor_with_note.delete_task(
            "2025-12-01", "несуществующая задача"
        )
        assert result is False


class TestEditorWellness:
    """Sleep, energy, focus section updates."""

    def test_set_sleep(self, editor_with_note):
        editor_with_note.set_sleep("2025-12-01", sleep_quality=9)
        raw = editor_with_note.read_raw("2025-12-01")
        assert "sleep-quality: 9" in raw or "sleep_quality: 9" in raw

    def test_set_energy_partial(self, editor_with_note):
        """Only update morning, preserve day and evening."""
        editor_with_note.set_energy("2025-12-01", morning=9)
        note = editor_with_note.read("2025-12-01")
        assert note.energy.morning_energy == 9
        # day-energy should still be 7 from the stub
        assert note.energy.day_energy == 7

    def test_set_focus(self, editor_with_note):
        editor_with_note.set_focus("2025-12-01", ["Первый фокус", "Второй фокус"])
        raw = editor_with_note.read_raw("2025-12-01")
        assert "Первый фокус" in raw
        assert "Второй фокус" in raw

    def test_set_gratitude(self, editor_with_note):
        editor_with_note.set_gratitude("2025-12-01", "Отличный день")
        raw = editor_with_note.read_raw("2025-12-01")
        assert "Отличный день" in raw
