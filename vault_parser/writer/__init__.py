"""Writer submodule — create, read, and update Obsidian daily notes."""
from vault_parser.writer.editor import DailyNoteEditor
from vault_parser.writer.task_lines import format_task_line

__all__ = ["DailyNoteEditor", "format_task_line"]
