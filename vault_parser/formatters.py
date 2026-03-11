"""Pretty formatting for CLI output of vault parser results."""
from __future__ import annotations

import json
from datetime import date
from typing import Any, Sequence

from vault_parser.models import (
    DayNote,
    EnergyData,
    MonthlyNote,
    SleepData,
    VaultTask,
    WeeklyNote,
)


# ── ANSI colors ──────────────────────────────────────────────────────
class _C:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    RESET = "\033[0m"


_STATUS_ICONS = {
    "open": f"{_C.YELLOW}○{_C.RESET}",
    "done": f"{_C.GREEN}✓{_C.RESET}",
    "cancelled": f"{_C.RED}✗{_C.RESET}",
    "in_progress": f"{_C.BLUE}◐{_C.RESET}",
}

_PRIORITY_LABELS = {
    "critical": f"{_C.RED}{_C.BOLD}⏫ CRIT{_C.RESET}",
    "high": f"{_C.RED}🔺 HIGH{_C.RESET}",
    "medium": f"{_C.YELLOW}🔼 MED{_C.RESET}",
    "low": f"{_C.DIM}🔽 LOW{_C.RESET}",
    "normal": f"{_C.DIM}   —  {_C.RESET}",
}


def _trunc(text: str, max_len: int = 60) -> str:
    return text[:max_len - 1] + "…" if len(text) > max_len else text


# ── Table formatter ──────────────────────────────────────────────────

def format_tasks_table(
    tasks: Sequence[VaultTask],
    *,
    max_items: int = 50,
    show_raw: bool = False,
) -> str:
    """Render tasks as a coloured CLI table."""
    if not tasks:
        return f"{_C.DIM}No tasks found.{_C.RESET}"

    lines: list[str] = []
    header = (
        f"{_C.BOLD}{'#':>3}  {'St':4}  {'Priority':8}  "
        f"{'Date':12}  {'Section':22}  {'Task':60}"
        f"{_C.RESET}"
    )
    lines.append(header)
    lines.append("─" * 120)

    for i, t in enumerate(tasks[:max_items], 1):
        st = _STATUS_ICONS.get(t.status.value, "?")
        prio = _PRIORITY_LABELS.get(t.priority.value, "")
        src_date = str(t.source_date) if t.source_date else "—"
        sect = _trunc(t.section, 22) if t.section else "—"
        text = _trunc(t.text, 60)

        # Suffix: people, wiki-links (non-person), time, scheduled
        suffix_parts: list[str] = []
        if t.people:
            suffix_parts.append(f"{_C.CYAN}@{','.join(t.people)}{_C.RESET}")
        # Show non-person wiki-links by target (filename) for cross-referencing
        non_person_links = [
            wl.target for wl in t.wiki_links
            if wl.target not in t.people
        ]
        if non_person_links:
            suffix_parts.append(f"{_C.DIM}🔗{','.join(non_person_links)}{_C.RESET}")
        if t.time_slot:
            suffix_parts.append(f"{_C.MAGENTA}{t.time_slot}{_C.RESET}")
        if t.scheduled_date:
            suffix_parts.append(f"{_C.YELLOW}⏳{t.scheduled_date}{_C.RESET}")
        if t.completion_date:
            suffix_parts.append(f"{_C.GREEN}✅{t.completion_date}{_C.RESET}")

        suffix = "  " + " ".join(suffix_parts) if suffix_parts else ""

        line = f"{i:>3}  {st:4}  {prio:8}  {src_date:12}  {sect:22}  {text}{suffix}"
        lines.append(line)

        if show_raw:
            lines.append(f"     {_C.DIM}{t.raw_line}{_C.RESET}")

    if len(tasks) > max_items:
        lines.append(f"{_C.DIM}... and {len(tasks) - max_items} more{_C.RESET}")

    lines.append(f"\n{_C.BOLD}Total: {len(tasks)} tasks{_C.RESET}")
    return "\n".join(lines)


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


# ── Stats formatter ──────────────────────────────────────────────────

def format_stats(
    daily: Sequence[DayNote],
    weekly: Sequence[WeeklyNote],
    monthly: Sequence[MonthlyNote],
) -> str:
    """Overview statistics about the vault."""
    all_tasks = []
    for d in daily:
        all_tasks.extend(d.all_tasks)
    for w in weekly:
        all_tasks.extend(w.tasks)

    open_count = sum(1 for t in all_tasks if t.is_open)
    done_count = sum(1 for t in all_tasks if t.is_done)
    cancelled = sum(1 for t in all_tasks if t.status.value == "cancelled")
    in_prog = sum(1 for t in all_tasks if t.status.value == "in_progress")

    # People mentioned
    people: dict[str, int] = {}
    for t in all_tasks:
        for p in t.people:
            people[p] = people.get(p, 0) + 1

    # Sleep stats
    sleep_durations = [
        d.sleep.duration_minutes()
        for d in daily
        if d.sleep.duration_minutes() is not None
    ]
    avg_sleep = sum(sleep_durations) / len(sleep_durations) if sleep_durations else 0

    # Energy stats
    energies = [d.energy.average() for d in daily if d.energy.average() is not None]
    avg_energy = sum(energies) / len(energies) if energies else 0

    # Week marks
    week_marks = [w.week_mark for w in weekly if w.week_mark is not None]
    avg_week = sum(week_marks) / len(week_marks) if week_marks else 0

    lines = [
        f"{_C.BOLD}📊 Vault Statistics{_C.RESET}",
        "═" * 50,
        f"  Daily notes:   {len(daily)}",
        f"  Weekly notes:  {len(weekly)}",
        f"  Monthly notes: {len(monthly)}",
        "",
        f"{_C.BOLD}📋 Tasks{_C.RESET}",
        f"  Total:        {len(all_tasks)}",
        f"  {_C.GREEN}Done:         {done_count}{_C.RESET}",
        f"  {_C.YELLOW}Open:         {open_count}{_C.RESET}",
        f"  {_C.BLUE}In progress:  {in_prog}{_C.RESET}",
        f"  {_C.RED}Cancelled:    {cancelled}{_C.RESET}",
        "",
        f"{_C.BOLD}😴 Sleep{_C.RESET}",
        f"  Avg duration: {avg_sleep / 60:.1f}h ({avg_sleep:.0f} min)",
        f"  Notes w/sleep: {len(sleep_durations)}",
        "",
        f"{_C.BOLD}⚡ Energy{_C.RESET}",
        f"  Avg energy:   {avg_energy:.1f} / 10",
        "",
        f"{_C.BOLD}📅 Weekly marks{_C.RESET}",
        f"  Avg week mark: {avg_week:.1f} / 10",
    ]

    if people:
        lines.append("")
        lines.append(f"{_C.BOLD}👥 People mentioned{_C.RESET}")
        for name, count in sorted(people.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  {name}: {count} tasks")

    return "\n".join(lines)


def format_wellness_table(daily: Sequence[DayNote], max_items: int = 50) -> str:
    """Render sleep & energy data as a standalone table with summary."""
    if not daily:
        return f"{_C.DIM}No daily notes found.{_C.RESET}"

    lines = [
        f"{_C.BOLD}😴⚡ Sleep & Energy Tracker{_C.RESET}",
        "",
        f"{_C.BOLD}{'Date':12}  {'Sleep':8}  {'Quality':9}  "
        f"{'Morning':9}  {'Day':6}  {'Evening':9}  "
        f"{'Mood':6}  {'Exercise':10}  {'Late meal':10}{_C.RESET}",
        "─" * 100,
    ]

    total_dur = 0
    dur_count = 0
    total_quality = 0
    qual_count = 0
    total_me = 0
    total_de = 0
    total_ee = 0
    energy_count = 0

    for d in daily[-max_items:]:
        dur = d.sleep.sleep_duration or "none"
        qual = str(d.sleep.sleep_quality) if d.sleep.sleep_quality is not None else "none"
        me = str(d.energy.morning_energy) if d.energy.morning_energy is not None else "none"
        de = str(d.energy.day_energy) if d.energy.day_energy is not None else "none"
        ee = str(d.energy.evening_energy) if d.energy.evening_energy is not None else "none"
        mood = str(d.sleep.morning_mood) if d.sleep.morning_mood is not None else "none"
        exercise = f"{_C.GREEN}true{_C.RESET}" if d.sleep.physical_exercise else f"{_C.DIM}false{_C.RESET}"
        late = f"{_C.RED}true{_C.RESET}" if d.sleep.late_dinner else f"{_C.DIM}false{_C.RESET}"

        lines.append(
            f"{str(d.date):12}  {dur:8}  {qual:9}  "
            f"{me:9}  {de:6}  {ee:9}  "
            f"{mood:6}  {exercise:>14}  {late:>14}"
        )

        # Accumulate for averages
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
    lines.append("─" * 100)
    avg_dur = f"{total_dur / dur_count / 60:.1f}h" if dur_count else "—"
    avg_qual = f"{total_quality / qual_count:.1f}" if qual_count else "—"
    avg_me = f"{total_me / energy_count:.1f}" if energy_count else "—"
    avg_de = f"{total_de / energy_count:.1f}" if energy_count else "—"
    avg_ee = f"{total_ee / energy_count:.1f}" if energy_count else "—"
    lines.append(
        f"{_C.BOLD}{'AVG':12}  {avg_dur:8}  {avg_qual:9}  "
        f"{avg_me:9}  {avg_de:6}  {avg_ee:9}{_C.RESET}"
    )
    lines.append(f"\n{_C.BOLD}Total days: {len(daily)}{_C.RESET}")

    return "\n".join(lines)


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


def format_people_table(registry) -> str:
    """Render people registry as a coloured CLI table."""
    lines = [
        f"{_C.BOLD}\U0001f465 People Registry{_C.RESET}",
        "",
        f"{_C.BOLD}{'Name':25}  {'Roles':30}  {'Interests':30}  {'Telegram':30}{_C.RESET}",
        "\u2500" * 120,
    ]

    for p in registry.all_persons():
        roles = ", ".join(p.roles[:4]) if p.roles else "\u2014"
        interests = ", ".join(p.interests[:4]) if p.interests else "\u2014"
        tg = p.telegram or "\u2014"
        lines.append(f"{p.name:25}  {roles:30}  {interests:30}  {tg:30}")

    if registry.all_groups():
        lines.append("")
        lines.append(f"{_C.BOLD}\U0001f465 Groups{_C.RESET}")
        lines.append("\u2500" * 80)
        for g in registry.all_groups():
            lines.append(f"  {_C.BOLD}{g.name}{_C.RESET}")
            if g.members:
                for member_name, role in g.members.items():
                    lines.append(f"    {_C.CYAN}{member_name:25}{_C.RESET}  {role}")
            else:
                lines.append("    \u2014")

    lines.append(f"\n{_C.BOLD}Total: {len(registry.all_persons())} people, {len(registry.all_groups())} groups{_C.RESET}")
    return "\n".join(lines)
