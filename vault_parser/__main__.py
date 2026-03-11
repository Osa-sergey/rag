"""CLI entry point for Vault Parser.

Usage examples:
    python -m vault_parser                                  # list all tasks (default)
    python -m vault_parser mode=list-tasks status=open      # open tasks only
    python -m vault_parser mode=list-tasks priority=high    # high-priority tasks
    python -m vault_parser mode=search query=tts            # search in task text
    python -m vault_parser mode=stats                       # vault statistics
    python -m vault_parser mode=wellness                    # sleep & energy table
    python -m vault_parser mode=wellness date_range=this_month  # filtered by date
    python -m vault_parser mode=parse                       # full vault parse (JSON dump)
    python -m vault_parser output.format=json               # JSON output
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

import hydra
from omegaconf import DictConfig

logger = logging.getLogger(__name__)


def _parse_date_range(spec: str) -> tuple[date | None, date | None]:
    """Parse date range spec into (from, to) pair.

    Supported formats:
        today, this_week, this_month, YYYY-MM-DD, YYYY-MM-DD..YYYY-MM-DD
    """
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
        # Single date
        try:
            d = date.fromisoformat(spec)
            return d, d
        except ValueError:
            logger.error("Invalid date_range: %s", spec)
            return None, None


@hydra.main(
    config_path="conf",
    config_name="config",
    version_base=None,
)
def main(cfg: DictConfig) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s][%(name)s][%(levelname)s] - %(message)s",
    )

    from vault_parser.filters import filter_tasks
    from vault_parser.formatters import (
        format_people_table,
        format_stats,
        format_tasks_csv,
        format_tasks_json,
        format_tasks_table,
        format_wellness_table,
        format_wellness_json,
        format_wellness_csv,
    )
    from vault_parser.parser import VaultParser

    vault_cfg = cfg.get("vault", {})
    vault_dir = vault_cfg.get("path", ".")
    people_dir = vault_cfg.get("people_dir")
    parser = VaultParser(
        vault_dir,
        daily_subdir=vault_cfg.get("daily_dir", "daily"),
        weekly_subdir=vault_cfg.get("weekly_dir", "weekly"),
        monthly_subdir=vault_cfg.get("monthly_dir", "monthly"),
        people_dir=people_dir,
    )

    mode = cfg.get("mode", "list-tasks")

    # ── People mode ──────────────────────────────────────────────
    if mode == "people":
        registry = parser.people_registry
        if not registry:
            print("People registry not loaded. Set vault.people_dir in config.")
            return
        out = cfg.get("output", {})
        fmt = out.get("format", "table")
        if fmt == "json":
            import json
            data = []
            for p in registry.all_persons():
                data.append({
                    "name": p.name,
                    "roles": p.roles,
                    "interests": p.interests,
                    "telegram": p.telegram,
                })
            for g in registry.all_groups():
                data.append({
                    "name": g.name,
                    "is_group": True,
                    "members": g.members,
                })
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(format_people_table(registry))
        return

    # ── Edit mode ────────────────────────────────────────────────
    if mode == "edit":
        from vault_parser.writer import DailyNoteEditor
        from vault_parser.models import TaskStatus
        from datetime import date as date_type

        note_date = cfg.get("date")
        if not note_date:
            print("Error: date= is required for edit mode")
            return

        daily_dir = Path(vault_dir) / vault_cfg.get("daily_dir", "daily")
        editor = DailyNoteEditor(daily_dir)
        action = cfg.get("action", "read")

        if action == "create":
            try:
                tpl = vault_cfg.get("template_path")
                path = editor.create_from_template(note_date, template_path=tpl)
                print(f"Created: {path}")
            except FileExistsError as e:
                print(f"Error: {e}")

        elif action == "set-sleep":
            sleep_fields = {}
            for key in ["bed_time_start", "sleep_start", "sleep_end", "sleep_duration",
                         "sleep_quality", "quick_fall_asleep", "night_awakenings",
                         "deep_sleep", "remembered_dreams", "no_nightmare",
                         "morning_mood", "no_phone", "physical_exercise", "late_dinner"]:
                val = cfg.get(key)
                if val is not None:
                    sleep_fields[key] = val
            if not sleep_fields:
                print("Error: provide at least one sleep field (e.g. sleep_quality=8)")
                return
            editor.set_sleep(note_date, **sleep_fields)
            print(f"Updated sleep for {note_date}: {list(sleep_fields.keys())}")

        elif action == "set-energy":
            editor.set_energy(
                note_date,
                morning=cfg.get("morning"),
                day=cfg.get("day_energy"),
                evening=cfg.get("evening"),
            )
            print(f"Updated energy for {note_date}")

        elif action == "set-focus":
            items = cfg.get("items", "")
            if isinstance(items, str):
                items = [i.strip() for i in items.split(";") if i.strip()]
            editor.set_focus(note_date, items)
            print(f"Set focus for {note_date}: {items}")

        elif action == "add-task":
            text = cfg.get("text")
            if not text:
                print("Error: text= is required")
                return
            section = cfg.get("section") or "main"
            people_str = cfg.get("people", "")
            people = [p.strip() for p in people_str.split(",") if p.strip()] if people_str else None

            sched = cfg.get("scheduled_date")
            start = cfg.get("start_date")
            due = cfg.get("due_date")
            scheduled_date = date_type.fromisoformat(sched) if sched else None
            start_date = date_type.fromisoformat(start) if start else None
            due_date = date_type.fromisoformat(due) if due else None

            editor.add_task(
                note_date, text,
                section=section,
                time_slot=cfg.get("time_slot"),
                people=people,
                scheduled_date=scheduled_date,
                start_date=start_date,
                due_date=due_date,
                recurrence=cfg.get("recurrence"),
            )
            print(f"Added task to {note_date}: {text}")

        elif action in ("done", "cancel", "progress"):
            query = cfg.get("query")
            if not query:
                print("Error: query= is required to match a task")
                return
            status_map = {"done": TaskStatus.DONE, "cancel": TaskStatus.CANCELLED, "progress": TaskStatus.IN_PROGRESS}
            result = editor.update_task_status(note_date, query, status_map[action])
            if result:
                print(f"Marked '{query}' as {action} in {note_date}")
            else:
                print(f"No task matching '{query}' found in {note_date}")

        elif action == "set-gratitude":
            editor.set_gratitude(note_date, cfg.get("text", ""))
            print(f"Updated gratitude for {note_date}")

        elif action == "set-notes":
            editor.set_notes(note_date, cfg.get("text", ""))
            print(f"Updated notes for {note_date}")

        elif action == "set-problem":
            editor.set_problem(note_date, cfg.get("what", ""), cfg.get("cause", ""), cfg.get("consequences", ""))
            print(f"Updated problem for {note_date}")

        elif action == "think-about":
            editor.add_think_about(note_date, cfg.get("text", ""))
            print(f"Added think-about for {note_date}")

        elif action == "read":
            note = editor.read(note_date)
            if note:
                import json
                from vault_parser.formatters import format_tasks_json
                print(json.dumps({
                    "date": str(note.date),
                    "focus": note.focus,
                    "tasks": [t.as_dict() for t in note.all_tasks],
                    "gratitude": note.gratitude,
                    "notes_text": note.notes_text,
                }, ensure_ascii=False, indent=2))
            else:
                print(f"Note not found: {note_date}")

        else:
            print(f"Unknown action: {action}. Use: create, set-sleep, set-energy, "
                  f"set-focus, add-task, done, cancel, progress, "
                  f"set-gratitude, set-notes, set-problem, think-about, read")
        return

    # ── Stats mode ───────────────────────────────────────────────
    if mode == "stats":
        all_notes = parser.parse_all()
        print(format_stats(all_notes["daily"], all_notes["weekly"], all_notes["monthly"]))
        return

    # ── Wellness mode (sleep & energy) ───────────────────────────
    if mode == "wellness":
        daily_notes = parser.parse_daily_notes()

        # Apply date filter
        date_range = cfg.get("date_range")
        if date_range:
            d_from, d_to = _parse_date_range(str(date_range))
            if d_from:
                daily_notes = [d for d in daily_notes if d.date >= d_from]
            if d_to:
                daily_notes = [d for d in daily_notes if d.date <= d_to]

        out = cfg.get("output", {})
        fmt = out.get("format", "table")
        max_items = out.get("max_items", 50)

        if fmt == "json":
            print(format_wellness_json(daily_notes))
        elif fmt == "csv":
            print(format_wellness_csv(daily_notes))
        else:
            print(format_wellness_table(daily_notes, max_items=max_items))
        return

    # ── Parse mode (full JSON dump) ──────────────────────────────
    if mode == "parse":
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
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # ── List-tasks / Search mode ─────────────────────────────────
    tasks = parser.all_tasks()

    # Apply filters from config
    filter_kwargs: dict = {}

    status = cfg.get("status")
    if status:
        filter_kwargs["status"] = status

    priority = cfg.get("priority")
    if priority:
        filter_kwargs["priority"] = priority

    date_range = cfg.get("date_range")
    if date_range:
        d_from, d_to = _parse_date_range(str(date_range))
        if d_from:
            filter_kwargs["date_from"] = d_from
        if d_to:
            filter_kwargs["date_to"] = d_to

    person = cfg.get("person")
    if person:
        filter_kwargs["person"] = person

    section = cfg.get("section")
    if section:
        filter_kwargs["section"] = section

    query = cfg.get("query")
    if query:
        filter_kwargs["query"] = query

    if mode == "search" and query:
        filter_kwargs["query"] = query

    if filter_kwargs:
        tasks = filter_tasks(tasks, **filter_kwargs)

    # Output
    out = cfg.get("output", {})
    fmt = out.get("format", "table")
    max_items = out.get("max_items", 50)
    show_raw = out.get("show_raw", False)

    if fmt == "json":
        print(format_tasks_json(tasks))
    elif fmt == "csv":
        print(format_tasks_csv(tasks))
    else:
        print(format_tasks_table(tasks, max_items=max_items, show_raw=show_raw))


if __name__ == "__main__":
    main()
