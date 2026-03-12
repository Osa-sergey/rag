"""Daily note editor — create, read, and update Obsidian daily notes.

Designed for MCP server integration: each method performs a single
atomic operation on the note file, supporting partial updates.
"""
from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

from vault_parser.models import DayNote, Recurrence, TaskStatus
from vault_parser.parser import parse_daily_note
from vault_parser.writer.frontmatter import (
    FM_KEY_ORDER,
    ENERGY_KWARGS_MAP,
    SLEEP_KWARGS_MAP,
    parse_raw_frontmatter,
    serialize_frontmatter,
)
from vault_parser.writer.sections import heading_level
from vault_parser.writer.task_lines import (
    CHECKBOX_RE,
    STATUS_CHECKBOX,
    format_task_line,
)

from interfaces import BaseDailyNoteEditor, BaseWellnessEditor

logger = logging.getLogger(__name__)


class DailyNoteEditor(BaseDailyNoteEditor, BaseWellnessEditor):
    """Create, read, and update Obsidian daily notes.

    All write methods perform partial updates — only the specified fields
    or sections are modified; everything else is preserved.

    Args:
        daily_dir: Path to the ``daily/`` subdirectory.

    Usage::

        editor = DailyNoteEditor(r"D:\\vault\\project_live\\day_notes\\daily")

        # Create a new note from template
        editor.create_from_template("2025-12-01")

        # Partially update sleep data
        editor.set_sleep("2025-12-01", sleep_quality=8, deep_sleep=True)

        # Add a task with people, dates, and recurrence
        editor.add_task(
            "2025-12-01",
            "стендап",
            section="main",
            people=["Илюхин Влад"],
            time_slot="10:00-10:15",
            recurrence="every mon,wed,fri",
        )

        # Read back structured data
        note = editor.read("2025-12-01")
    """

    def __init__(self, daily_dir: str | Path) -> None:
        self.daily_dir = Path(daily_dir)

    def _path(self, note_date: str | date) -> Path:
        if isinstance(note_date, date):
            note_date = note_date.isoformat()
        return self.daily_dir / f"{note_date}.md"

    # ── Read ─────────────────────────────────────────────────────

    def exists(self, note_date: str | date) -> bool:
        """Check if a daily note exists for this date."""
        return self._path(note_date).exists()

    def read(self, note_date: str | date) -> DayNote | None:
        """Parse and return structured content of a daily note.

        Returns None if the file doesn't exist.
        """
        path = self._path(note_date)
        if not path.exists():
            return None
        return parse_daily_note(path)

    def read_raw(self, note_date: str | date) -> str | None:
        """Return raw markdown content of a daily note."""
        path = self._path(note_date)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    # ── Create ───────────────────────────────────────────────────

    def create_from_template(
        self, note_date: str | date, template_path: str | Path | None = None,
    ) -> Path:
        """Create a new daily note from an Obsidian template file.

        Reads the template from *template_path* (typically ``t_daily.md``).
        Templater expressions (``<% ... %>``) in frontmatter values are
        replaced with empty values.  The body (everything after the second
        ``---``) is copied verbatim.

        If *template_path* is ``None`` or the file doesn't exist, falls back
        to a built-in default template.

        Does NOT overwrite existing files — raises FileExistsError.

        Returns:
            Path to the created file.
        """
        path = self._path(note_date)
        if path.exists():
            raise FileExistsError(f"Note already exists: {path}")

        if template_path and Path(template_path).exists():
            content = self._render_template(Path(template_path))
        else:
            if template_path:
                logger.warning(
                    "Template not found at %s, using built-in default", template_path
                )
            content = self._builtin_template()

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info("Created daily note from template: %s", path)
        return path

    @staticmethod
    def _render_template(template_path: Path) -> str:
        """Read an Obsidian/Templater template and strip dynamic expressions."""
        import re as _re

        raw = template_path.read_text(encoding="utf-8")

        # Split into frontmatter + body
        parts = raw.split("---", 2)
        if len(parts) < 3:
            # No valid frontmatter — return as-is
            return raw

        fm_raw = parts[1]
        body = parts[2]

        # Strip Templater expressions: <% ... %> → empty
        tp_re = _re.compile(r"<%.*?%>", _re.DOTALL)

        clean_lines = []
        for line in fm_raw.split("\n"):
            if ":" in line:
                key, _, value = line.partition(":")
                value = tp_re.sub("", value).strip()
                clean_lines.append(f"{key.rstrip()}: {value}" if value else f"{key.rstrip()}:")
            else:
                clean_lines.append(line)

        return "---\n" + "\n".join(clean_lines) + "\n---" + body

    @staticmethod
    def _builtin_template() -> str:
        """Built-in fallback template."""
        fm: dict[str, Any] = {}
        for key in FM_KEY_ORDER:
            fm[key] = None

        body_lines = [
            "# Планы на день",
            "## Фокус дня",
            "- ",
            "## Основные дела",
            "",
            "## Второстепенные задачи",
            "",
            "---",
            "# Чему я рад и что получилось",
            "",
            "___",
            "# Что пошло не так ",
            "",
            "## Что",
            "### Причина",
            "",
            "### Последствия",
            "",
            "---",
            "# Заметки",
            "",
            "---",
            "# Надо подумать о",
            "",
        ]
        return serialize_frontmatter(fm) + "\n" + "\n".join(body_lines) + "\n"

    # ── Frontmatter updates ──────────────────────────────────────

    def set_sleep(self, note_date: str | date, **kwargs: Any) -> None:
        """Partially update sleep properties in frontmatter.

        Only the specified kwargs are updated; other fields are preserved.

        Args:
            note_date: Target date.
            **kwargs: Any of: bed_time_start, sleep_start, sleep_end,
                sleep_duration, sleep_quality, quick_fall_asleep,
                night_awakenings, deep_sleep, remembered_dreams,
                no_nightmare, morning_mood, no_phone,
                physical_exercise, late_dinner.

        Example::

            editor.set_sleep("2025-12-01", sleep_quality=8, deep_sleep=True)
        """
        updates = {}
        for kwarg, value in kwargs.items():
            yaml_key = SLEEP_KWARGS_MAP.get(kwarg)
            if yaml_key is None:
                raise ValueError(
                    f"Unknown sleep field: {kwarg}. "
                    f"Valid: {list(SLEEP_KWARGS_MAP.keys())}"
                )
            updates[yaml_key] = value
        self._update_frontmatter(note_date, updates)

    def set_energy(
        self,
        note_date: str | date,
        *,
        morning: int | None = None,
        day: int | None = None,
        evening: int | None = None,
    ) -> None:
        """Partially update energy levels in frontmatter."""
        updates = {}
        if morning is not None:
            updates["morning-energy"] = morning
        if day is not None:
            updates["day-energy"] = day
        if evening is not None:
            updates["evening-energy"] = evening
        self._update_frontmatter(note_date, updates)

    def _update_frontmatter(self, note_date: str | date, updates: dict[str, Any]) -> None:
        path = self._path(note_date)
        if not path.exists():
            raise FileNotFoundError(f"Note not found: {path}")

        text = path.read_text(encoding="utf-8")
        fm, body = parse_raw_frontmatter(text)
        fm.update(updates)
        content = serialize_frontmatter(fm) + "\n" + body
        path.write_text(content, encoding="utf-8")
        logger.info("Updated frontmatter for %s: %s", note_date, list(updates.keys()))

    # ── Section updates ──────────────────────────────────────────

    def set_focus(self, note_date: str | date, items: list[str]) -> None:
        """Set the 'Фокус дня' bullet list."""
        content = "\n".join(f"- {item}" for item in items)
        self._update_section(note_date, "## Фокус дня", content)

    def set_gratitude(self, note_date: str | date, text: str) -> None:
        """Set the 'Чему я рад и что получилось' section."""
        self._update_section(note_date, "# Чему я рад и что получилось", text)

    def set_problem(
        self,
        note_date: str | date,
        what: str,
        cause: str = "",
        consequences: str = "",
    ) -> None:
        """Set the 'Что пошло не так' section with sub-headings."""
        content = (
            f"\n## {what}\n"
            f"### Причина\n{cause}\n"
            f"### Последствия\n{consequences}\n"
        )
        self._update_section(note_date, "# Что пошло не так", content)

    def set_notes(self, note_date: str | date, text: str) -> None:
        """Set the 'Заметки' section."""
        self._update_section(note_date, "# Заметки", text)

    def add_think_about(self, note_date: str | date, text: str) -> None:
        """Append a task to the 'Надо подумать о' section."""
        line = format_task_line(text)
        self._append_to_section(note_date, "# Надо подумать о", line)

    # ── Task management ──────────────────────────────────────────

    def add_task(
        self,
        note_date: str | date,
        text: str,
        *,
        section: str = "main",
        status: TaskStatus = TaskStatus.OPEN,
        scheduled_date: date | None = None,
        start_date: date | None = None,
        due_date: date | None = None,
        time_slot: str | None = None,
        people: list[str] | None = None,
        completion_date: date | None = None,
        recurrence: str | Recurrence | None = None,
    ) -> None:
        """Add a task to a section.

        Args:
            note_date: Target date.
            text: Task description text.
            section: ``"main"`` → Основные дела, ``"secondary"`` → Второстепенные задачи.
            status: Checkbox status.
            scheduled_date: ``⏳ YYYY-MM-DD``.
            start_date: ``🛫 YYYY-MM-DD``.
            due_date: ``📅 YYYY-MM-DD``.
            time_slot: ``"HH:MM-HH:MM"`` time range.
            people: List of person filenames, e.g. ``["Котиков Федор"]``.
            completion_date: ``✅ YYYY-MM-DD``.
            recurrence: ``"every day"`` or ``"every mon,wed,fri"`` etc.
        """
        heading = {
            "main": "## Основные дела",
            "secondary": "## Второстепенные задачи",
        }.get(section)
        if heading is None:
            raise ValueError(f"Unknown section: {section}. Use 'main' or 'secondary'.")

        line = format_task_line(
            text,
            status=status,
            scheduled_date=scheduled_date,
            start_date=start_date,
            due_date=due_date,
            time_slot=time_slot,
            people=people,
            completion_date=completion_date,
            recurrence=recurrence,
        )
        self._append_to_section(note_date, heading, line)

    def update_task_status(
        self,
        note_date: str | date,
        query: str,
        new_status: TaskStatus,
        *,
        completion_date: date | None = None,
    ) -> bool:
        """Update the status of a task matching the query substring.

        Returns True if a task was found and updated.
        """
        path = self._path(note_date)
        if not path.exists():
            raise FileNotFoundError(f"Note not found: {path}")

        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        query_lower = query.lower()
        updated = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            m = CHECKBOX_RE.match(stripped)
            if m and query_lower in stripped.lower():
                old_checkbox = m.group(0)
                rest = stripped[len(old_checkbox):]

                # Remove old completion date if present
                rest = re.sub(r"\s*✅\s*\d{4}-\d{2}-\d{2}", "", rest)

                new_checkbox = STATUS_CHECKBOX[new_status]
                new_line = new_checkbox + rest

                if new_status == TaskStatus.DONE:
                    comp = completion_date or date.today()
                    new_line += f" ✅ {comp}"

                lines[i] = new_line
                updated = True
                logger.info("Updated task status: %s → %s", query, new_status.value)
                break

        if updated:
            path.write_text("\n".join(lines), encoding="utf-8")
        return updated

    # ------------------------------------------------------------------
    def list_tasks(self, note_date: str | date) -> list:
        """List all tasks in a daily note.

        Returns parsed VaultTask objects (with raw_line, section, etc.).
        """
        note = self.read(note_date)
        if note is None:
            raise FileNotFoundError(f"Note not found: {self._path(note_date)}")
        return note.all_tasks

    # ------------------------------------------------------------------
    def delete_task(self, note_date: str | date, query: str) -> bool:
        """Delete the first task whose line matches *query* (case-insensitive).

        The entire checkbox line is removed from the file.
        Returns True if a task was found and deleted.
        """
        path = self._path(note_date)
        if not path.exists():
            raise FileNotFoundError(f"Note not found: {path}")

        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        query_lower = query.lower()
        deleted = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            m = CHECKBOX_RE.match(stripped)
            if m and query_lower in stripped.lower():
                logger.info("Deleting task line %d: %s", i + 1, stripped)
                del lines[i]
                deleted = True
                break

        if deleted:
            path.write_text("\n".join(lines), encoding="utf-8")
        return deleted

    # ── Internal helpers ─────────────────────────────────────────

    def _update_section(self, note_date: str | date, heading: str, content: str) -> None:
        path = self._path(note_date)
        if not path.exists():
            raise FileNotFoundError(f"Note not found: {path}")

        text = path.read_text(encoding="utf-8")
        fm, body = parse_raw_frontmatter(text)

        lines = body.split("\n")
        new_lines: list[str] = []
        in_target = False
        inserted = False
        target_level = heading_level(heading)

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("#"):
                level = heading_level(stripped)
                if stripped == heading:
                    in_target = True
                    new_lines.append(line)
                    new_lines.append(content)
                    inserted = True
                    continue
                elif in_target and level <= target_level:
                    in_target = False

            if not in_target:
                new_lines.append(line)

        if not inserted:
            new_lines.append(heading)
            new_lines.append(content)

        new_body = "\n".join(new_lines)
        path.write_text(serialize_frontmatter(fm) + "\n" + new_body, encoding="utf-8")

    def _append_to_section(self, note_date: str | date, heading: str, line: str) -> None:
        path = self._path(note_date)
        if not path.exists():
            raise FileNotFoundError(f"Note not found: {path}")

        text = path.read_text(encoding="utf-8")
        fm, body = parse_raw_frontmatter(text)

        body_lines = body.split("\n")
        new_lines: list[str] = []
        in_target = False
        appended = False
        target_level = heading_level(heading)

        for bline in body_lines:
            stripped = bline.strip()

            if stripped == heading:
                in_target = True
                new_lines.append(bline)
                continue

            if in_target and stripped.startswith("#"):
                level = heading_level(stripped)
                if level <= target_level:
                    new_lines.append(line)
                    appended = True
                    in_target = False

            if in_target and stripped in ("---", "___"):
                new_lines.append(line)
                appended = True
                in_target = False

            new_lines.append(bline)

        if in_target and not appended:
            new_lines.append(line)

        new_body = "\n".join(new_lines)
        path.write_text(serialize_frontmatter(fm) + "\n" + new_body, encoding="utf-8")
