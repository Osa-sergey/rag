"""Abstract bases for vault parser and note editors."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vault_parser.models import DayNote, VaultTask, WeeklyNote, MonthlyNote
    from vault_parser.people import PeopleRegistry


class BaseVaultParser(ABC):
    """Abstract base for vault note parsers.

    Parses an entire Obsidian vault directory into structured
    DayNote / WeeklyNote / MonthlyNote objects.
    """

    @abstractmethod
    def parse_all(self) -> dict[str, list[DayNote] | list[WeeklyNote] | list[MonthlyNote]]:
        """Parse all notes (daily, weekly, monthly).

        Returns:
            Dict with keys ``'daily'``, ``'weekly'``, ``'monthly'``.
        """
        ...

    @abstractmethod
    def all_tasks(self) -> list[VaultTask]:
        """Extract all tasks across all daily and weekly notes.

        Returns:
            Flat list of VaultTask objects.
        """
        ...

    @abstractmethod
    def parse_daily_notes(self) -> list[DayNote]:
        """Parse daily notes, sorted by date ascending."""
        ...

    @abstractmethod
    def parse_weekly_notes(self) -> list[WeeklyNote]:
        """Parse weekly notes, sorted by week ascending."""
        ...

    @abstractmethod
    def parse_monthly_notes(self) -> list[MonthlyNote]:
        """Parse monthly notes, sorted by month ascending."""
        ...

    @property
    @abstractmethod
    def people_registry(self) -> PeopleRegistry | None:
        """Return loaded PeopleRegistry, or None if people_dir was not set."""
        ...


class BaseNoteEditor(ABC):
    """Base for any note editor (daily / weekly / monthly).

    Provides only the universal operations that apply to
    any type of Obsidian note regardless of its structure.
    """

    @abstractmethod
    def exists(self, note_date: str | date) -> bool:
        """Check if a note exists for this date."""
        ...

    @abstractmethod
    def read(self, note_date: str | date) -> DayNote | None:
        """Parse and return structured content of a note.

        Returns:
            Parsed note object, or None if the file doesn't exist.
        """
        ...

    @abstractmethod
    def read_raw(self, note_date: str | date) -> str | None:
        """Return raw markdown content.

        Returns:
            Markdown string, or None if the file doesn't exist.
        """
        ...

    @abstractmethod
    def create_from_template(
        self, note_date: str | date, template_path: str | Path | None = None,
    ) -> Path:
        """Create a new note from a template.

        Returns:
            Path to the created file.

        Raises:
            FileExistsError: If a note already exists for this date.
        """
        ...


class BaseDailyNoteEditor(BaseNoteEditor):
    """Editor for daily notes — adds task management.

    Task operations are universal across any daily note format.
    """

    @abstractmethod
    def add_task(
        self, note_date: str | date, text: str, *,
        section: str = "main",
        scheduled_date: date | None = None,
        start_date: date | None = None,
        due_date: date | None = None,
        time_slot: str | None = None,
        people: list[str] | None = None,
        completion_date: date | None = None,
        recurrence: str | None = None,
    ) -> None:
        """Add a task to a section.

        Args:
            note_date: Target date.
            text: Task description.
            section: ``'main'`` or ``'secondary'``.
        """
        ...

    @abstractmethod
    def update_task_status(
        self, note_date: str | date, query: str, new_status: Any, *,
        completion_date: date | None = None,
    ) -> bool:
        """Update the status of a task matching the query substring.

        Returns:
            True if a task was found and updated.
        """
        ...

    @abstractmethod
    def list_tasks(self, note_date: str | date) -> list[VaultTask]:
        """List all tasks in a note (for preview / confirmation).

        Returns:
            List of VaultTask objects with ``raw_line`` and ``section`` populated.

        Raises:
            FileNotFoundError: If the note doesn't exist.
        """
        ...

    @abstractmethod
    def delete_task(self, note_date: str | date, query: str) -> bool:
        """Delete a task whose text matches the query substring.

        The first matching checkbox line is removed entirely from the file.

        Args:
            note_date: Target date.
            query: Substring to match against the task line (case-insensitive).

        Returns:
            True if a task was found and deleted.

        Raises:
            FileNotFoundError: If the note doesn't exist.
        """
        ...


class BaseWellnessEditor(ABC):
    """Mixin for wellness / reflection operations.

    These are OPTIONAL and specific to note formats that track
    sleep, energy, focus, gratitude, problems, etc.

    Compose with BaseDailyNoteEditor::

        class DailyNoteEditor(BaseDailyNoteEditor, BaseWellnessEditor):
            ...
    """

    @abstractmethod
    def set_sleep(self, note_date: str | date, **kwargs: Any) -> None:
        """Update sleep data in frontmatter.

        Args:
            **kwargs: bed_time_start, sleep_start, sleep_end,
                sleep_duration, sleep_quality, quick_fall_asleep,
                night_awakenings, deep_sleep, remembered_dreams,
                no_nightmare, morning_mood, no_phone,
                physical_exercise, late_dinner.
        """
        ...

    @abstractmethod
    def set_energy(
        self, note_date: str | date, *,
        morning: int | None = None,
        day: int | None = None,
        evening: int | None = None,
    ) -> None:
        """Update energy levels in frontmatter."""
        ...

    @abstractmethod
    def set_focus(self, note_date: str | date, items: list[str]) -> None:
        """Set the focus items bullet list."""
        ...

    @abstractmethod
    def set_gratitude(self, note_date: str | date, text: str) -> None:
        """Set the gratitude section."""
        ...

    @abstractmethod
    def set_notes(self, note_date: str | date, text: str) -> None:
        """Set the notes section."""
        ...

    @abstractmethod
    def set_problem(
        self, note_date: str | date,
        what: str, cause: str = "", consequences: str = "",
    ) -> None:
        """Set the problem/post-mortem section."""
        ...

    @abstractmethod
    def add_think_about(self, note_date: str | date, text: str) -> None:
        """Append an item to the 'things to think about' section."""
        ...
