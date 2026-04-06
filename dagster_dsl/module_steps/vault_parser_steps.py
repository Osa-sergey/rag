"""Step definitions for vault_parser module.

Registered steps:
    vault_parser.parse  — Full JSON dump of parsed vault
"""
from __future__ import annotations

import logging
from pathlib import Path

from dagster_dsl.steps import register_step
from vault_parser.schemas import VaultParserConfig

log = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "vault_parser" / "conf"


@register_step(
    "vault_parser.parse",
    description="Полный парсинг Obsidian-вольта в JSON",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=VaultParserConfig,
    tags={"module": "vault_parser", "type": "parsing"},
)
def vault_parse_step(cfg):
    """Execute vault_parser parse logic.

    Replicates the CLI ``parse`` command:
      1. Init DI container
      2. Call parser methods
      3. Return parsed data
    """
    from vault_parser.containers import VaultParserContainer

    container = VaultParserContainer(config=cfg)
    parser = container.parser()

    data = parser.parse_all()
    return {
        "daily_count": len(data.get("daily", [])),
        "weekly_count": len(data.get("weekly", [])),
        "monthly_count": len(data.get("monthly", [])),
    }

@register_step(
    "vault_parser.list_tasks",
    description="Get a list of tasks from the vault",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=VaultParserConfig,
    tags={"module": "vault_parser", "type": "query"},
)
def vault_list_tasks_step(cfg):
    from vault_parser.containers import VaultParserContainer
    from vault_parser.schemas import Mode
    
    cfg.mode = Mode.list_tasks
    container = VaultParserContainer(config=cfg)
    parser = container.parser()
    
    tasks = parser.list_tasks(
        status=cfg.status, 
        priority=cfg.priority, 
        date_range=cfg.date_range, 
        person=cfg.person, 
        section=cfg.section
    )
    return {"tasks": [t.model_dump() for t in tasks], "count": len(tasks)}

@register_step(
    "vault_parser.search",
    description="Search tasks in the vault by text query",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=VaultParserConfig,
    tags={"module": "vault_parser", "type": "query"},
)
def vault_search_step(cfg):
    from vault_parser.containers import VaultParserContainer
    from vault_parser.schemas import Mode
    
    cfg.mode = Mode.search
    container = VaultParserContainer(config=cfg)
    parser = container.parser()
    
    tasks = parser.search_tasks(cfg.query)
    return {"tasks": [t.model_dump() for t in tasks], "count": len(tasks)}

@register_step(
    "vault_parser.stats",
    description="Get aggregated task statistics",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=VaultParserConfig,
    tags={"module": "vault_parser", "type": "query"},
)
def vault_stats_step(cfg):
    from vault_parser.containers import VaultParserContainer
    from vault_parser.schemas import Mode
    
    cfg.mode = Mode.stats
    container = VaultParserContainer(config=cfg)
    parser = container.parser()
    
    stats = parser.get_stats()
    return stats

@register_step(
    "vault_parser.wellness",
    description="Get wellness entries (sleep, energy)",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=VaultParserConfig,
    tags={"module": "vault_parser", "type": "query"},
)
def vault_wellness_step(cfg):
    from vault_parser.containers import VaultParserContainer
    from vault_parser.schemas import Mode
    
    cfg.mode = Mode.wellness
    container = VaultParserContainer(config=cfg)
    parser = container.parser()
    
    entries = parser.get_wellness(date_range=cfg.date_range)
    return {"entries": [e.model_dump() for e in entries], "count": len(entries)}

@register_step(
    "vault_parser.add_task",
    description="Add a task to a daily note",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=VaultParserConfig,
    tags={"module": "vault_parser", "type": "edit"},
)
def vault_add_task_step(cfg):
    from vault_parser.containers import VaultParserContainer
    from vault_parser.schemas import Mode, EditAction, TaskStatus
    
    cfg.mode = Mode.edit
    cfg.action = EditAction.add_task
    container = VaultParserContainer(config=cfg)
    editor = container.editor()
    
    people_list = [p.strip() for p in cfg.people_param.split(",")] if cfg.people_param else None
    
    ok = editor.add_task(
        note_date=cfg.date,
        text=cfg.text,
        section=cfg.section or "main",
        status=cfg.status or TaskStatus.open,
        scheduled_date=cfg.scheduled_date,
        due_date=cfg.due_date,
        people=people_list
    )
    return {"success": ok}

@register_step(
    "vault_parser.update_task",
    description="Update a task status",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=VaultParserConfig,
    tags={"module": "vault_parser", "type": "edit"},
)
def vault_update_task_step(cfg):
    from vault_parser.containers import VaultParserContainer
    from vault_parser.schemas import Mode
    
    cfg.mode = Mode.edit
    container = VaultParserContainer(config=cfg)
    editor = container.editor()
    
    ok = editor.update_task_status(cfg.date, cfg.query, cfg.status)
    return {"success": ok, "found": ok}

@register_step(
    "vault_parser.delete_task",
    description="Delete a task from a daily note",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=VaultParserConfig,
    tags={"module": "vault_parser", "type": "edit"},
)
def vault_delete_task_step(cfg):
    from vault_parser.containers import VaultParserContainer
    from vault_parser.schemas import Mode, EditAction
    
    cfg.mode = Mode.edit
    cfg.action = EditAction.delete
    container = VaultParserContainer(config=cfg)
    editor = container.editor()
    
    ok = editor.delete_task(cfg.date, cfg.query)
    return {"success": ok, "found": ok}

@register_step(
    "vault_parser.create_note",
    description="Create a daily note from template",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=VaultParserConfig,
    tags={"module": "vault_parser", "type": "edit"},
)
def vault_create_note_step(cfg):
    from vault_parser.containers import VaultParserContainer
    from vault_parser.schemas import Mode, EditAction
    
    cfg.mode = Mode.edit
    cfg.action = EditAction.create
    container = VaultParserContainer(config=cfg)
    editor = container.editor()
    
    template_path = cfg.vault.template_path
    path = editor.create_from_template(cfg.date, template_path)
    return {"path": str(path)}

