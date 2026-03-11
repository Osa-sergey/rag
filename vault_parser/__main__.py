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
