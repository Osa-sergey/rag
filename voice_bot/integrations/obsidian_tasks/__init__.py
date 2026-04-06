"""Obsidian Tasks integration — create, view, edit, delete tasks in Obsidian vault."""

from voice_bot.integrations.obsidian_tasks.schemas import ObsidianTask, ObsidianConfig
from voice_bot.integrations.obsidian_tasks.vault import ObsidianVault

__all__ = ["ObsidianTask", "ObsidianConfig", "ObsidianVault"]
