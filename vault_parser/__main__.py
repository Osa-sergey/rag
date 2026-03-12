"""CLI entry point for Vault Parser (Click + Hydra + Pydantic + DI wiring).

Architecture:
  Click handler (thin)  -> parse CLI args, load config, init container
  Business function     -> @inject receives ready objects via Provide[]

Usage:
    python -m vault_parser --help
    python -m vault_parser list-tasks --status open --priority high
    python -m vault_parser search "tts"
    python -m vault_parser stats
    python -m vault_parser wellness --date-range this_week
    python -m vault_parser people --format json
    python -m vault_parser edit --date 2025-12-01 --action create
    python -m vault_parser validate
    python -m vault_parser show-config
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

import click
from dependency_injector.wiring import Provide, inject

from cli_base import add_common_commands, load_config
from vault_parser.schemas import VaultParserConfig

CONFIG_DIR = Path(__file__).parent / "conf"
CONFIG_NAME = "config"

# Container — initialized once per CLI invocation
_container = None


def _parse_date_range(spec: str) -> tuple[date | None, date | None]:
    """Parse date_range into (from, to) pair."""
    spec = spec.strip().lower()
    today = date.today()
    if spec == "today":
        return today, today
    elif spec == "this_week":
        monday = today - timedelta(days=today.weekday())
        return monday, monday + timedelta(days=6)
    elif spec == "this_month":
        first = today.replace(day=1)
        if today.month == 12:
            last = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        return first, last
    elif ".." in spec:
        parts = spec.split("..")
        return date.fromisoformat(parts[0].strip()), date.fromisoformat(parts[1].strip())
    else:
        d = date.fromisoformat(spec)
        return d, d


def _init_container(cfg: VaultParserConfig):
    """Create, wire, and return the DI container."""
    global _container
    from vault_parser.containers import VaultParserContainer
    _container = VaultParserContainer(config=cfg)
    _container.wire(modules=[__name__])
    return _container


# ══════════════════════════════════════════════════════════════
# Business logic — @inject + Provide[]
# Эти функции НЕ знают про Click, конфиги, CLI-аргументы.
# Они получают готовые объекты через DI wiring.
# ══════════════════════════════════════════════════════════════

@inject
def _do_list_tasks(cfg: VaultParserConfig, parser=Provide["parser"]):
    """Фильтрация и вывод задач."""
    from vault_parser.filters import filter_tasks
    from vault_parser.formatters import format_tasks_table, format_tasks_json, format_tasks_csv

    tasks = parser.all_tasks()

    filter_kwargs: dict = {}
    if cfg.status:
        filter_kwargs["status"] = cfg.status.value
    if cfg.priority:
        filter_kwargs["priority"] = cfg.priority.value
    if cfg.date_range:
        d_from, d_to = _parse_date_range(cfg.date_range)
        if d_from:
            filter_kwargs["date_from"] = d_from
        if d_to:
            filter_kwargs["date_to"] = d_to
    if cfg.person:
        filter_kwargs["person"] = cfg.person
    if cfg.section:
        filter_kwargs["section"] = cfg.section
    if cfg.query:
        filter_kwargs["query"] = cfg.query

    if filter_kwargs:
        tasks = filter_tasks(tasks, **filter_kwargs)

    out = cfg.output
    if out.format == "json":
        click.echo(format_tasks_json(tasks))
    elif out.format == "csv":
        click.echo(format_tasks_csv(tasks))
    else:
        click.echo(format_tasks_table(tasks, max_items=out.max_items, show_raw=out.show_raw))


@inject
def _do_stats(parser=Provide["parser"]):
    """Агрегированная статистика."""
    from vault_parser.formatters import format_stats
    all_notes = parser.parse_all()
    click.echo(format_stats(all_notes["daily"], all_notes["weekly"], all_notes["monthly"]))


@inject
def _do_wellness(cfg: VaultParserConfig, parser=Provide["parser"]):
    """Таблица сна и энергии."""
    from vault_parser.formatters import format_wellness_table, format_wellness_json, format_wellness_csv

    daily_notes = parser.parse_daily_notes()

    if cfg.date_range:
        d_from, d_to = _parse_date_range(cfg.date_range)
        if d_from:
            daily_notes = [d for d in daily_notes if d.date >= d_from]
        if d_to:
            daily_notes = [d for d in daily_notes if d.date <= d_to]

    out = cfg.output
    if out.format == "json":
        click.echo(format_wellness_json(daily_notes))
    elif out.format == "csv":
        click.echo(format_wellness_csv(daily_notes))
    else:
        click.echo(format_wellness_table(daily_notes, max_items=out.max_items))


@inject
def _do_people(cfg: VaultParserConfig, parser=Provide["parser"]):
    """Реестр людей."""
    from vault_parser.formatters import format_people_table

    registry = parser.people_registry
    if not registry:
        click.echo("Реестр людей не загружен. Укажите vault.people_dir в конфиге.")
        return

    if cfg.output.format == "json":
        data = []
        for p in registry.all_persons():
            data.append({"name": p.name, "roles": p.roles,
                         "interests": p.interests, "telegram": p.telegram})
        for g in registry.all_groups():
            data.append({"name": g.name, "is_group": True, "members": g.members})
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        click.echo(format_people_table(registry))


@inject
def _do_edit(cfg: VaultParserConfig, note_date, action, section,
             editor=Provide["editor"]):
    """Редактирование дневных заметок."""
    from vault_parser.models import TaskStatus as VaultTaskStatus
    from datetime import date as date_type

    if action == "create":
        try:
            tpl = cfg.vault.template_path
            path = editor.create_from_template(note_date, template_path=tpl)
            click.echo(f"Created: {path}")
        except FileExistsError as e:
            click.echo(f"Error: {e}")

    elif action == "set-sleep":
        from vault_parser.writer.frontmatter import SLEEP_KWARGS_MAP
        sleep_fields = {}
        for key in SLEEP_KWARGS_MAP:
            val = getattr(cfg, key, None)
            if val is not None:
                sleep_fields[key] = val
        if not sleep_fields:
            click.echo("Укажите хотя бы одно sleep-поле (e.g. -o sleep_quality=8)")
            return
        editor.set_sleep(note_date, **sleep_fields)
        click.echo(f"Сон обновлён для {note_date}: {list(sleep_fields.keys())}")

    elif action == "set-energy":
        editor.set_energy(note_date, morning=cfg.morning, day=cfg.day_energy, evening=cfg.evening)
        click.echo(f"Энергия обновлена для {note_date}")

    elif action == "set-focus":
        items = cfg.items or ""
        if isinstance(items, str):
            items = [i.strip() for i in items.split(";") if i.strip()]
        editor.set_focus(note_date, items)
        click.echo(f"Фокус дня для {note_date}: {items}")

    elif action == "add-task":
        people_str = cfg.people_param or ""
        ppl = [p.strip() for p in people_str.split(",") if p.strip()] if people_str else None
        sched = date_type.fromisoformat(cfg.scheduled_date) if cfg.scheduled_date else None
        start = date_type.fromisoformat(cfg.start_date) if cfg.start_date else None
        due = date_type.fromisoformat(cfg.due_date) if cfg.due_date else None
        editor.add_task(
            note_date, cfg.text,
            section=section or "main",
            time_slot=cfg.time_slot,
            people=ppl,
            scheduled_date=sched,
            start_date=start,
            due_date=due,
            recurrence=cfg.recurrence,
        )
        click.echo(f"Задача добавлена в {note_date}: {cfg.text}")

    elif action in ("done", "cancel", "progress"):
        status_map = {"done": VaultTaskStatus.DONE, "cancel": VaultTaskStatus.CANCELLED,
                      "progress": VaultTaskStatus.IN_PROGRESS}
        result = editor.update_task_status(note_date, cfg.query, status_map[action])
        if result:
            click.echo(f"'{cfg.query}' -> {action} в {note_date}")
        else:
            click.echo(f"Задача '{cfg.query}' не найдена в {note_date}")

    elif action == "set-gratitude":
        editor.set_gratitude(note_date, cfg.text or "")
        click.echo(f"Благодарность обновлена для {note_date}")

    elif action == "set-notes":
        editor.set_notes(note_date, cfg.text or "")
        click.echo(f"Заметки обновлены для {note_date}")

    elif action == "set-problem":
        editor.set_problem(note_date, cfg.what or "", cfg.cause or "", cfg.consequences or "")
        click.echo(f"Проблема обновлена для {note_date}")

    elif action == "think-about":
        editor.add_think_about(note_date, cfg.text or "")
        click.echo(f"Добавлено в 'Надо подумать' для {note_date}")

    elif action == "read":
        note = editor.read(note_date)
        if note:
            click.echo(json.dumps({
                "date": str(note.date),
                "focus": note.focus,
                "tasks": [t.as_dict() for t in note.all_tasks],
                "gratitude": note.gratitude,
                "notes_text": note.notes_text,
            }, ensure_ascii=False, indent=2))
        else:
            click.echo(f"Заметка не найдена: {note_date}")

    elif action == "list":
        try:
            tasks = editor.list_tasks(note_date)
        except FileNotFoundError:
            click.echo(f"Заметка не найдена: {note_date}")
            return
        if not tasks:
            click.echo(f"Задачи не найдены в {note_date}")
            return
        click.echo(f"Задачи в {note_date} ({len(tasks)} шт.):")
        click.echo()
        for i, t in enumerate(tasks, 1):
            status_icon = {"open": "☐", "done": "✅", "in_progress": "🔄",
                           "cancelled": "❌"}.get(t.status.value, "?")
            prio = f" [{t.priority.value}]" if t.priority.value != "normal" else ""
            section = f" ({t.section})" if t.section else ""
            click.echo(f"  {i:3d}. {status_icon}{prio} {t.text}{section}")

    elif action == "delete":
        if not cfg.query:
            click.echo("Укажите --query / -q для поиска задачи для удаления")
            return
        # Сначала показать, что будет удалено
        try:
            tasks = editor.list_tasks(note_date)
        except FileNotFoundError:
            click.echo(f"Заметка не найдена: {note_date}")
            return
        query_lower = cfg.query.lower()
        matches = [t for t in tasks if query_lower in t.text.lower() or query_lower in t.raw_line.lower()]
        if not matches:
            click.echo(f"Задача '{cfg.query}' не найдена в {note_date}")
            return
        click.echo(f"Найдено совпадений: {len(matches)}")
        for t in matches:
            click.echo(f"  → {t.raw_line.strip()}")
        # Удаляем первое совпадение
        result = editor.delete_task(note_date, cfg.query)
        if result:
            click.echo(f"✅ Задача удалена из {note_date}")
        else:
            click.echo(f"Ошибка при удалении задачи '{cfg.query}'")


@inject
def _do_parse(parser=Provide["parser"]):
    """Полный JSON-дамп."""
    all_notes = parser.parse_all()
    result = {
        "daily_count": len(all_notes["daily"]),
        "weekly_count": len(all_notes["weekly"]),
        "monthly_count": len(all_notes["monthly"]),
        "daily": [
            {
                "date": str(d.date),
                "sleep_duration": d.sleep.sleep_duration,
                "sleep_quality": d.sleep.sleep_quality,
                "energy": {
                    "morning": d.energy.morning_energy,
                    "day": d.energy.day_energy,
                    "evening": d.energy.evening_energy,
                },
                "focus": d.focus,
                "tasks": [t.as_dict() for t in d.all_tasks],
                "gratitude": d.gratitude,
                "notes": d.notes_text,
                "wiki_links": [str(wl) for wl in d.wiki_links],
            }
            for d in all_notes["daily"]
        ],
        "weekly": [
            {
                "label": w.date_label,
                "week_mark": w.week_mark,
                "tasks": [t.as_dict() for t in w.tasks],
                "focus": w.focus,
                "achievements": w.achievements,
                "insights": w.insights,
                "problems": w.problems,
                "wiki_links": [str(wl) for wl in w.wiki_links],
            }
            for w in all_notes["weekly"]
        ],
        "monthly": [
            {
                "label": m.date_label,
                "month_score": m.month_score,
                "dynamics": m.dynamics[:200] if m.dynamics else "",
                "achievements": m.achievements,
                "insights": m.insights,
                "reflection": m.reflection[:200] if m.reflection else "",
            }
            for m in all_notes["monthly"]
        ],
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ══════════════════════════════════════════════════════════════
# Click handlers (thin) — parse CLI → config → container → call
# ══════════════════════════════════════════════════════════════

@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Подробный вывод (DEBUG)")
def cli(verbose: bool) -> None:
    """Vault Parser -- извлечение задач и метрик из Obsidian-заметок.

    Парсинг дневных, недельных и месячных заметок из Obsidian-вольта
    с фильтрацией, поиском и автоматическим реестром людей.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
        stream=sys.stdout,
    )


# ── list-tasks ────────────────────────────────────────────────

@cli.command("list-tasks")
@click.option("--status", type=click.Choice(["open", "done", "cancelled", "in_progress"]),
              default=None, help="Фильтр по статусу задачи")
@click.option("--priority", type=click.Choice(["critical", "high", "medium", "low", "normal"]),
              default=None, help="Фильтр по приоритету")
@click.option("--date-range", default=None,
              help="Фильтр по дате: today, this_week, YYYY-MM-DD, YYYY-MM-DD..YYYY-MM-DD")
@click.option("--person", default=None, help="Задачи конкретного человека")
@click.option("--section", default=None, help="Фильтр по секции заметки")
@click.option("--query", "-q", default=None, help="Поиск по тексту задачи")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv"]),
              default=None, help="Формат вывода  [default: table]")
@click.option("--max-items", type=int, default=None, help="Лимит строк  [default: 50]")
@click.option("--show-raw", is_flag=True, default=False, help="Показать исходный markdown")
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def list_tasks_cmd(status, priority, date_range, person, section, query,
                   fmt, max_items, show_raw, override):
    """Вывод задач с фильтрацией.

    \b
    Примеры:
      python -m vault_parser list-tasks
      python -m vault_parser list-tasks --status open --priority high
      python -m vault_parser list-tasks --date-range this_week --person "Федя"
      python -m vault_parser list-tasks --format json
    """
    overrides = {}
    if status:
        overrides["status"] = status
    if priority:
        overrides["priority"] = priority
    if date_range:
        overrides["date_range"] = date_range
    if person:
        overrides["person"] = person
    if section:
        overrides["section"] = section
    if query:
        overrides["query"] = query
    if fmt:
        overrides["output.format"] = fmt
    if max_items:
        overrides["output.max_items"] = max_items
    if show_raw:
        overrides["output.show_raw"] = True

    cfg = load_config(CONFIG_DIR, CONFIG_NAME, VaultParserConfig,
                      overrides=override, mode="list-tasks", **overrides)
    _init_container(cfg)
    _do_list_tasks(cfg)


# ── search ────────────────────────────────────────────────────

@cli.command()
@click.argument("query")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv"]),
              default=None, help="Формат вывода")
@click.option("--max-items", type=int, default=None, help="Лимит строк")
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def search(query, fmt, max_items, override):
    """Полнотекстовый поиск по тексту задач.

    \b
    Примеры:
      python -m vault_parser search "tts"
      python -m vault_parser search "python" --format json
    """
    overrides = {"query": query, "mode": "list-tasks"}
    if fmt:
        overrides["output.format"] = fmt
    if max_items:
        overrides["output.max_items"] = max_items

    cfg = load_config(CONFIG_DIR, CONFIG_NAME, VaultParserConfig,
                      overrides=override, **overrides)
    _init_container(cfg)
    _do_list_tasks(cfg)


# ── stats ─────────────────────────────────────────────────────

@cli.command()
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def stats(override):
    """Агрегированная статистика по вольту."""
    cfg = load_config(CONFIG_DIR, CONFIG_NAME, VaultParserConfig,
                      overrides=override, mode="stats")
    _init_container(cfg)
    _do_stats()


# ── wellness ──────────────────────────────────────────────────

@cli.command()
@click.option("--date-range", default=None,
              help="Фильтр по дате: today, this_week, YYYY-MM-DD..YYYY-MM-DD")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv"]),
              default=None, help="Формат вывода")
@click.option("--max-items", type=int, default=None, help="Лимит строк")
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def wellness(date_range, fmt, max_items, override):
    """Таблица сна и энергии.

    \b
    Примеры:
      python -m vault_parser wellness
      python -m vault_parser wellness --date-range this_week
      python -m vault_parser wellness --format csv > sleep.csv
    """
    overrides = {}
    if date_range:
        overrides["date_range"] = date_range
    if fmt:
        overrides["output.format"] = fmt
    if max_items:
        overrides["output.max_items"] = max_items

    cfg = load_config(CONFIG_DIR, CONFIG_NAME, VaultParserConfig,
                      overrides=override, mode="wellness", **overrides)
    _init_container(cfg)
    _do_wellness(cfg)


# ── people ────────────────────────────────────────────────────

@cli.command()
@click.option("--format", "fmt", type=click.Choice(["table", "json"]),
              default=None, help="Формат вывода")
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def people(fmt, override):
    """Реестр людей и групп из people/ директории.

    \b
    Примеры:
      python -m vault_parser people
      python -m vault_parser people --format json
    """
    overrides = {}
    if fmt:
        overrides["output.format"] = fmt
    cfg = load_config(CONFIG_DIR, CONFIG_NAME, VaultParserConfig,
                      overrides=override, mode="people", **overrides)
    _init_container(cfg)
    _do_people(cfg)


# ── edit ──────────────────────────────────────────────────────

@cli.command()
@click.option("--date", "note_date", required=True, help="Дата заметки (YYYY-MM-DD)")
@click.option("--action", type=click.Choice([
    "create", "set-sleep", "set-energy", "set-focus",
    "add-task", "done", "cancel", "progress",
    "set-gratitude", "set-notes", "set-problem", "think-about",
    "read", "list", "delete",
]), default="read", help="Действие")
@click.option("--text", default=None, help="Текст задачи / секции")
@click.option("--section", default=None, help="Секция: main / secondary")
@click.option("--query", "-q", default=None, help="Поиск задачи (для done/cancel/progress)")
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def edit(note_date, action, text, section, query, override):
    """Редактор дневных заметок (создание, обновление, удаление).

    \b
    Примеры:
      python -m vault_parser edit --date 2025-12-01 --action create
      python -m vault_parser edit --date 2025-12-01 --action add-task --text "стендап"
      python -m vault_parser edit --date 2025-12-01 --action done --query "стендап"
      python -m vault_parser edit --date 2025-12-01 --action list
      python -m vault_parser edit --date 2025-12-01 --action delete --query "стендап"
      python -m vault_parser edit --date 2025-12-01 --action read
    """
    overrides = {"mode": "edit", "date": note_date, "action": action}
    if text:
        overrides["text"] = text
    if query:
        overrides["query"] = query

    cfg = load_config(CONFIG_DIR, CONFIG_NAME, VaultParserConfig,
                      overrides=override, **overrides)
    _init_container(cfg)
    _do_edit(cfg, note_date, action, section)


# ── parse ─────────────────────────────────────────────────────

@cli.command()
@click.option("--override", "-o", multiple=True, help="Hydra override (key=value)")
def parse(override):
    """Полный JSON-дамп всех заметок."""
    cfg = load_config(CONFIG_DIR, CONFIG_NAME, VaultParserConfig,
                      overrides=override, mode="parse")
    _init_container(cfg)
    _do_parse()


# ── Common commands ───────────────────────────────────────────

add_common_commands(cli, CONFIG_DIR, CONFIG_NAME, VaultParserConfig)


if __name__ == "__main__":
    cli()
