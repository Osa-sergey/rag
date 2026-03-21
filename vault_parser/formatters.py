"""Pretty formatting for CLI output of vault parser results.

Uses Rich for colorful tables and panels in the terminal.
JSON and CSV formats remain plain-text for piping.
"""
from __future__ import annotations

import json
from typing import Sequence

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from vault_parser.models import (
    DayNote,
    MonthlyNote,
    SleepData,
    VaultTask,
    WeeklyNote,
)

_console = Console()


# ── Status / Priority styles ────────────────────────────────────

_STATUS_STYLE = {
    "open": ("○", "yellow"),
    "done": ("✓", "green"),
    "cancelled": ("✗", "red"),
    "in_progress": ("◐", "blue"),
}

_PRIORITY_STYLE = {
    "critical": ("⏫ CRIT", "bold red"),
    "high": ("🔺 HIGH", "red"),
    "medium": ("🔼 MED", "yellow"),
    "low": ("🔽 LOW", "dim"),
    "normal": ("—", "dim"),
}


def _trunc(text: str, max_len: int = 60) -> str:
    return text[: max_len - 1] + "…" if len(text) > max_len else text


# ── Table formatter ──────────────────────────────────────────────

def format_tasks_table(
    tasks: Sequence[VaultTask],
    *,
    max_items: int = 50,
    show_raw: bool = False,
) -> None:
    """Render tasks as a Rich table to the console."""
    if not tasks:
        _console.print("[dim]No tasks found.[/dim]")
        return

    table = Table(title=f"Tasks ({len(tasks)})", show_lines=False, expand=True)
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("St", width=3, justify="center")
    table.add_column("Priority", width=10)
    table.add_column("Date", style="cyan", width=12)
    table.add_column("Section", style="dim", width=22, overflow="ellipsis")
    table.add_column("Task", min_width=30, ratio=1)
    table.add_column("Meta", style="dim", width=20, overflow="ellipsis")

    for i, t in enumerate(tasks[:max_items], 1):
        icon, st_style = _STATUS_STYLE.get(t.status.value, ("?", ""))
        prio_label, prio_style = _PRIORITY_STYLE.get(t.priority.value, ("", ""))
        src_date = str(t.source_date) if t.source_date else "—"
        sect = _trunc(t.section, 22) if t.section else "—"
        text = _trunc(t.text, 60)

        # Meta column: people, links, time, scheduled
        meta_parts: list[str] = []
        if t.people:
            meta_parts.append(f"@{','.join(t.people)}")
        non_person_links = [wl.target for wl in t.wiki_links if wl.target not in t.people]
        if non_person_links:
            meta_parts.append(f"🔗{','.join(non_person_links)}")
        if t.time_slot:
            meta_parts.append(t.time_slot)
        if t.scheduled_date:
            meta_parts.append(f"⏳{t.scheduled_date}")
        meta = " ".join(meta_parts)

        table.add_row(
            str(i),
            Text(icon, style=st_style),
            Text(prio_label, style=prio_style),
            src_date,
            sect,
            text,
            meta,
        )

    if len(tasks) > max_items:
        table.caption = f"… and {len(tasks) - max_items} more"

    _console.print(table)


def format_tasks_json(tasks: Sequence[VaultTask]) -> str:
    """Render tasks as JSON."""
    return json.dumps([t.as_dict() for t in tasks], ensure_ascii=False, indent=2)


def format_tasks_csv(tasks: Sequence[VaultTask]) -> str:
    """Render tasks as CSV."""
    header = "status,priority,date,section,text,people,scheduled,completed"
    rows = [header]
    for t in tasks:
        people = ";".join(t.people)
        rows.append(
            f"{t.status.value},{t.priority.value},{t.source_date},"
            f'"{t.section}","{t.text}","{people}",{t.scheduled_date},{t.completion_date}'
        )
    return "\n".join(rows)


# ── Stats formatter ──────────────────────────────────────────────

def format_stats(
    daily: Sequence[DayNote],
    weekly: Sequence[WeeklyNote],
    monthly: Sequence[MonthlyNote],
) -> None:
    """Overview statistics about the vault (rendered via Rich)."""
    all_tasks = []
    for d in daily:
        all_tasks.extend(d.all_tasks)
    for w in weekly:
        all_tasks.extend(w.tasks)

    open_count = sum(1 for t in all_tasks if t.is_open)
    done_count = sum(1 for t in all_tasks if t.is_done)
    cancelled = sum(1 for t in all_tasks if t.status.value == "cancelled")
    in_prog = sum(1 for t in all_tasks if t.status.value == "in_progress")

    # People
    people: dict[str, int] = {}
    for t in all_tasks:
        for p in t.people:
            people[p] = people.get(p, 0) + 1

    # Sleep stats
    sleep_durations = [
        d.sleep.duration_minutes() for d in daily if d.sleep.duration_minutes() is not None
    ]
    avg_sleep = sum(sleep_durations) / len(sleep_durations) if sleep_durations else 0

    # Energy stats
    energies = [d.energy.average() for d in daily if d.energy.average() is not None]
    avg_energy = sum(energies) / len(energies) if energies else 0

    # Week marks
    week_marks = [w.week_mark for w in weekly if w.week_mark is not None]
    avg_week = sum(week_marks) / len(week_marks) if week_marks else 0

    # Notes table
    notes_table = Table(show_header=False, show_edge=False, padding=(0, 2))
    notes_table.add_column(style="bold")
    notes_table.add_column(justify="right")
    notes_table.add_row("Daily notes", str(len(daily)))
    notes_table.add_row("Weekly notes", str(len(weekly)))
    notes_table.add_row("Monthly notes", str(len(monthly)))

    # Tasks table
    tasks_table = Table(show_header=False, show_edge=False, padding=(0, 2))
    tasks_table.add_column(style="bold")
    tasks_table.add_column(justify="right")
    tasks_table.add_row("Total", str(len(all_tasks)))
    tasks_table.add_row("[green]Done[/green]", str(done_count))
    tasks_table.add_row("[yellow]Open[/yellow]", str(open_count))
    tasks_table.add_row("[blue]In progress[/blue]", str(in_prog))
    tasks_table.add_row("[red]Cancelled[/red]", str(cancelled))

    # Wellness
    wellness_table = Table(show_header=False, show_edge=False, padding=(0, 2))
    wellness_table.add_column(style="bold")
    wellness_table.add_column(justify="right")
    wellness_table.add_row("Avg sleep", f"{avg_sleep / 60:.1f}h ({avg_sleep:.0f} min)")
    wellness_table.add_row("Avg energy", f"{avg_energy:.1f} / 10")
    wellness_table.add_row("Avg week mark", f"{avg_week:.1f} / 10")

    _console.print(Panel(notes_table, title="📊 Vault", border_style="blue"))
    _console.print(Panel(tasks_table, title="📋 Tasks", border_style="green"))
    _console.print(Panel(wellness_table, title="😴⚡ Wellness", border_style="magenta"))

    if people:
        people_table = Table(title="👥 People Mentioned (top 10)", show_lines=False)
        people_table.add_column("Name", style="cyan")
        people_table.add_column("Tasks", justify="right")
        for name, count in sorted(people.items(), key=lambda x: -x[1])[:10]:
            people_table.add_row(name, str(count))
        _console.print(people_table)


def format_wellness_table(daily: Sequence[DayNote], max_items: int = 50) -> None:
    """Render sleep & energy data as a Rich table with summary."""
    if not daily:
        _console.print("[dim]No daily notes found.[/dim]")
        return

    table = Table(title="😴⚡ Sleep & Energy Tracker", show_lines=False)
    table.add_column("Date", style="cyan", width=12)
    table.add_column("Sleep", width=8)
    table.add_column("Quality", width=7, justify="center")
    table.add_column("🌅 Morn", width=7, justify="center")
    table.add_column("☀️ Day", width=7, justify="center")
    table.add_column("🌙 Eve", width=7, justify="center")
    table.add_column("Mood", width=6, justify="center")
    table.add_column("🏋️", width=4, justify="center")
    table.add_column("🍽️", width=4, justify="center")

    total_dur = dur_count = total_quality = qual_count = 0
    total_me = total_de = total_ee = energy_count = 0

    for d in daily[-max_items:]:
        dur = d.sleep.sleep_duration or "—"
        qual = str(d.sleep.sleep_quality) if d.sleep.sleep_quality is not None else "—"
        me = str(d.energy.morning_energy) if d.energy.morning_energy is not None else "—"
        de = str(d.energy.day_energy) if d.energy.day_energy is not None else "—"
        ee = str(d.energy.evening_energy) if d.energy.evening_energy is not None else "—"
        mood = str(d.sleep.morning_mood) if d.sleep.morning_mood is not None else "—"
        exercise = "[green]✓[/green]" if d.sleep.physical_exercise else "[dim]—[/dim]"
        late = "[red]✓[/red]" if d.sleep.late_dinner else "[dim]—[/dim]"

        table.add_row(str(d.date), dur, qual, me, de, ee, mood, exercise, late)

        dur_mins = d.sleep.duration_minutes()
        if dur_mins is not None:
            total_dur += dur_mins
            dur_count += 1
        if d.sleep.sleep_quality is not None:
            total_quality += d.sleep.sleep_quality
            qual_count += 1
        if d.energy.morning_energy is not None:
            total_me += d.energy.morning_energy
        if d.energy.day_energy is not None:
            total_de += d.energy.day_energy
        if d.energy.evening_energy is not None:
            total_ee += d.energy.evening_energy
        if d.energy.average() is not None:
            energy_count += 1

    # Summary row
    avg_dur = f"{total_dur / dur_count / 60:.1f}h" if dur_count else "—"
    avg_qual = f"{total_quality / qual_count:.1f}" if qual_count else "—"
    avg_me = f"{total_me / energy_count:.1f}" if energy_count else "—"
    avg_de = f"{total_de / energy_count:.1f}" if energy_count else "—"
    avg_ee = f"{total_ee / energy_count:.1f}" if energy_count else "—"

    table.add_section()
    table.add_row(
        Text("AVG", style="bold"), avg_dur, avg_qual, avg_me, avg_de, avg_ee, "", "", "",
    )
    table.caption = f"Total days: {len(daily)}"

    _console.print(table)


def format_wellness_json(daily: Sequence[DayNote]) -> str:
    """Render sleep & energy data as JSON."""
    records = []
    for d in daily:
        records.append({
            "date": str(d.date),
            "sleep": {
                "bed_time_start": d.sleep.bed_time_start,
                "sleep_start": d.sleep.sleep_start,
                "sleep_end": d.sleep.sleep_end,
                "duration": d.sleep.sleep_duration,
                "duration_minutes": d.sleep.duration_minutes(),
                "quality": d.sleep.sleep_quality,
                "quick_fall_asleep": d.sleep.quick_fall_asleep,
                "night_awakenings": d.sleep.night_awakenings,
                "deep_sleep": d.sleep.deep_sleep,
                "remembered_dreams": d.sleep.remembered_dreams,
                "no_nightmare": d.sleep.no_nightmare,
                "no_phone": d.sleep.no_phone,
                "physical_exercise": d.sleep.physical_exercise,
                "late_dinner": d.sleep.late_dinner,
            },
            "energy": {
                "morning_mood": d.sleep.morning_mood,
                "morning_energy": d.energy.morning_energy,
                "day_energy": d.energy.day_energy,
                "evening_energy": d.energy.evening_energy,
                "average": d.energy.average(),
            },
        })
    return json.dumps(records, ensure_ascii=False, indent=2)


def format_wellness_csv(daily: Sequence[DayNote]) -> str:
    """Render sleep & energy data as CSV."""
    header = (
        "date,bed_time,sleep_start,sleep_end,duration,duration_min,"
        "quality,mood,morning_energy,day_energy,evening_energy,"
        "quick_asleep,night_wake,deep_sleep,dreams,nightmare,phone,exercise,late_dinner"
    )
    rows = [header]
    for d in daily:
        s = d.sleep
        e = d.energy
        rows.append(
            f"{d.date},{s.bed_time_start},{s.sleep_start},{s.sleep_end},"
            f"{s.sleep_duration},{s.duration_minutes()},"
            f"{s.sleep_quality},{s.morning_mood},"
            f"{e.morning_energy},{e.day_energy},{e.evening_energy},"
            f"{s.quick_fall_asleep},{s.night_awakenings},{s.deep_sleep},"
            f"{s.remembered_dreams},{s.no_nightmare},{s.no_phone},"
            f"{s.physical_exercise},{s.late_dinner}"
        )
    return "\n".join(rows)


def format_people_table(registry) -> None:
    """Render people registry as a Rich table."""
    table = Table(title="👥 People Registry", show_lines=False)
    table.add_column("Name", style="bold cyan", min_width=20)
    table.add_column("Roles", min_width=25)
    table.add_column("Interests", min_width=25)
    table.add_column("Telegram", style="dim")

    for p in registry.all_persons():
        roles = ", ".join(p.roles[:4]) if p.roles else "—"
        interests = ", ".join(p.interests[:4]) if p.interests else "—"
        tg = p.telegram or "—"
        table.add_row(p.name, roles, interests, tg)

    _console.print(table)

    if registry.all_groups():
        groups_table = Table(title="👥 Groups", show_lines=False)
        groups_table.add_column("Group", style="bold")
        groups_table.add_column("Member", style="cyan", min_width=25)
        groups_table.add_column("Role")

        for g in registry.all_groups():
            if g.members:
                first = True
                for member_name, role in g.members.items():
                    groups_table.add_row(
                        g.name if first else "",
                        member_name,
                        role,
                    )
                    first = False
            else:
                groups_table.add_row(g.name, "—", "—")

        _console.print(groups_table)

    _console.print(
        f"\n[bold]Total: {len(registry.all_persons())} people, "
        f"{len(registry.all_groups())} groups[/bold]"
    )
