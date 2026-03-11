"""Core parser for Obsidian vault markdown files.

Handles daily, weekly, and monthly notes with full extraction of:
- YAML frontmatter (sleep / energy metrics)
- Tasks with all metadata (status, priority, dates, wiki-links, time slots)
- Section-based content (gratitude, problems, reflections, etc.)
"""
from __future__ import annotations

import logging
import re
from datetime import date, time
from pathlib import Path
from typing import Any

import yaml

from vault_parser.models import (
    DayNote,
    EnergyData,
    MonthlyNote,
    NoteType,
    Priority,
    ReflectionBlock,
    SleepData,
    TaskStatus,
    TimeSlot,
    VaultTask,
    WeeklyNote,
    WikiLink,
)

logger = logging.getLogger(__name__)

# ── Regex patterns ───────────────────────────────────────────────────

# Checkbox line:  - [x] text ✅ 2025-11-28
_CHECKBOX_RE = re.compile(
    r"^(?P<indent>\s*)-\s+"             # leading indent + bullet
    r"\[(?P<status>[xX /\-])\]\s+"      # checkbox status
    r"(?P<body>.+)$",                   # rest of the line
)

# Completion date:  ✅ 2025-11-28  (at the end of line or before parenthetical)
_COMPLETION_DATE_RE = re.compile(r"✅\s*(\d{4}-\d{2}-\d{2})")

# Scheduled date:  ⏳ 2025-08-29
_SCHEDULED_DATE_RE = re.compile(r"⏳\s*(\d{4}-\d{2}-\d{2})")

# Priority emoji markers
_PRIORITY_EMOJI: dict[str, Priority] = {
    "⏫": Priority.CRITICAL,
    "🔺": Priority.HIGH,
    "🔼": Priority.MEDIUM,
    "🔽": Priority.LOW,
}
_PRIORITY_RE = re.compile(r"[⏫🔺🔼🔽]")

# Wiki-link:  [[Target|Alias]]  or  [[Target]]
_WIKI_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")

# Time slot:  HH:MM-HH:MM  (e.g. 11:30-12:00)
_TIME_SLOT_RE = re.compile(r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})")

# Inline comment in parentheses at end of line
_INLINE_COMMENT_RE = re.compile(r"\(([^)]+)\)\s*$")

# Tags:  #tag
_TAG_RE = re.compile(r"(?<!\w)#([\w\-/]+)")

# Week filename:  2025-W34
_WEEK_FILE_RE = re.compile(r"^(\d{4})-W(\d{1,2})$")

# Monthly filename:  2025-08
_MONTH_FILE_RE = re.compile(r"^(\d{4})-(\d{2})$")

# Daily filename:  2025-08-25
_DAILY_FILE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

# Heading detector
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")

# Week mark:  week-mark:: 6
_WEEK_MARK_RE = re.compile(r"week-mark::\s*(\d+)")

# Score in text:  4 из 10  or  **5/10**  or  5 из 10
_MONTH_SCORE_RE = re.compile(r"\*?\*?(\d{1,2})\s*(?:из|/)\s*10\*?\*?")

# Dataview code block boundaries
_CODE_BLOCK_RE = re.compile(r"^```")


# ── Helpers ──────────────────────────────────────────────────────────

def _parse_date(s: str) -> date | None:
    """Try to parse YYYY-MM-DD string into a date."""
    try:
        return date.fromisoformat(s.strip())
    except (ValueError, AttributeError):
        return None


def _parse_time(s: str) -> time | None:
    """Parse H:MM or HH:MM into a time object."""
    parts = s.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        return time(int(parts[0]), int(parts[1]))
    except ValueError:
        return None


def parse_wiki_links(text: str) -> list[WikiLink]:
    """Extract all ``[[Target|Alias]]`` links from text."""
    return [
        WikiLink(target=m.group(1).strip(), alias=m.group(2).strip() if m.group(2) else None)
        for m in _WIKI_LINK_RE.finditer(text)
    ]


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from body.

    Returns (frontmatter_dict, body_text).
    If no frontmatter, returns ({}, full_text).
    """
    if not text.startswith("---"):
        return {}, text

    # Find the closing ---
    end_idx = text.find("\n---", 3)
    if end_idx == -1:
        return {}, text

    fm_raw = text[3:end_idx].strip()
    body = text[end_idx + 4:].strip()

    try:
        fm = yaml.safe_load(fm_raw)
        if not isinstance(fm, dict):
            fm = {}
    except yaml.YAMLError:
        fm = {}

    return fm, body


def _extract_sleep_data(fm: dict[str, Any]) -> SleepData:
    """Build SleepData from frontmatter dict."""
    def _bool(v: Any) -> bool:
        """Parse boolean — returns False for None/empty (no 'unset' state)."""
        if v is None or v == "":
            return False
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "yes", "1", "да")
        return bool(v)

    def _int(v: Any) -> int | None:
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    def _str(v: Any) -> str | None:
        if v is None or v == "":
            return None
        return str(v)

    def _time_str(v: Any) -> str | None:
        """Handle YAML sexagesimal: `6:30` becomes int 390 (=6*60+30).

        Convert back to 'H:MM' string.  Also handles string values as-is.
        """
        if v is None or v == "":
            return None
        if isinstance(v, int):
            # YAML parsed H:MM as minutes (sexagesimal base-60)
            hours = v // 60
            mins = v % 60
            return f"{hours}:{mins:02d}"
        return str(v)

    # physical-exercise has a trailing colon in some notes: "physical-exercise:"
    exercise = _bool(fm.get("physical-exercise:")) or _bool(fm.get("physical-exercise"))

    return SleepData(
        bed_time_start=_time_str(fm.get("bed-time-start")),
        sleep_start=_time_str(fm.get("sleep-start")),
        sleep_end=_time_str(fm.get("sleep-end")),
        sleep_duration=_time_str(fm.get("sleep-duration")),
        sleep_quality=_int(fm.get("sleep-quality")),
        quick_fall_asleep=_bool(fm.get("quick-fall-asleep")),
        night_awakenings=_bool(fm.get("night-awakenings")),
        deep_sleep=_bool(fm.get("deep-sleep")),
        remembered_dreams=_bool(fm.get("remembered-dreams")),
        no_nightmare=_bool(fm.get("no-nightmare")),
        morning_mood=_int(fm.get("morning-mood")),
        no_phone=_bool(fm.get("no-phone")),
        physical_exercise=exercise,
        late_dinner=_bool(fm.get("late-dinner")),
    )


def _extract_energy_data(fm: dict[str, Any]) -> EnergyData:
    """Build EnergyData from frontmatter dict."""
    def _int(v: Any) -> int | None:
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    return EnergyData(
        morning_energy=_int(fm.get("morning-energy")),
        day_energy=_int(fm.get("day-energy")),
        evening_energy=_int(fm.get("evening-energy")),
    )


# ── Task parsing ─────────────────────────────────────────────────────

def _detect_priority_from_emoji(text: str) -> Priority | None:
    """Check for priority emoji in text."""
    for emoji, prio in _PRIORITY_EMOJI.items():
        if emoji in text:
            return prio
    return None


def _section_to_priority(section: str) -> Priority:
    """Infer priority from the section heading."""
    s = section.lower()
    if "фокус" in s:
        return Priority.HIGH
    if "основные" in s:
        return Priority.MEDIUM
    if "второстепенные" in s:
        return Priority.LOW
    if "подумать" in s:
        return Priority.LOW
    return Priority.NORMAL


def parse_task_line(
    line: str,
    *,
    section: str = "",
    source_file: Path | None = None,
    source_date: date | None = None,
) -> VaultTask | None:
    """Parse a single checkbox line into a VaultTask.

    Returns None if the line is not a valid checkbox task.
    """
    m = _CHECKBOX_RE.match(line)
    if not m:
        return None

    raw_status = m.group("status")
    body = m.group("body").strip()

    # ─ Status ────────────────────────────────────────────────────
    status_map = {
        "x": TaskStatus.DONE,
        "X": TaskStatus.DONE,
        " ": TaskStatus.OPEN,
        "/": TaskStatus.IN_PROGRESS,
        "-": TaskStatus.CANCELLED,
    }
    status = status_map.get(raw_status, TaskStatus.OPEN)

    # ─ Completion date ───────────────────────────────────────────
    completion_date: date | None = None
    cm = _COMPLETION_DATE_RE.search(body)
    if cm:
        completion_date = _parse_date(cm.group(1))

    # ─ Scheduled date ────────────────────────────────────────────
    scheduled_date: date | None = None
    sm = _SCHEDULED_DATE_RE.search(body)
    if sm:
        scheduled_date = _parse_date(sm.group(1))

    # ─ Priority ──────────────────────────────────────────────────
    priority = _detect_priority_from_emoji(body) or _section_to_priority(section)

    # ─ Time slot ─────────────────────────────────────────────────
    time_slot: TimeSlot | None = None
    tm = _TIME_SLOT_RE.search(body)
    if tm:
        t_start = _parse_time(tm.group(1))
        t_end = _parse_time(tm.group(2))
        if t_start and t_end:
            time_slot = TimeSlot(start=t_start, end=t_end)

    # ─ Wiki-links ────────────────────────────────────────────────
    wiki_links = parse_wiki_links(body)
    people = [wl.display_name() for wl in wiki_links]

    # ─ Tags ──────────────────────────────────────────────────────
    tags = _TAG_RE.findall(body)

    # ─ Inline comment ────────────────────────────────────────────
    inline_comment: str | None = None
    ic_match = _INLINE_COMMENT_RE.search(body)
    if ic_match:
        inline_comment = ic_match.group(1).strip()

    # ─ Clean text ────────────────────────────────────────────────
    clean = body
    # Remove completion / scheduled markers
    clean = _COMPLETION_DATE_RE.sub("", clean)
    clean = _SCHEDULED_DATE_RE.sub("", clean)
    # Remove priority emojis
    clean = _PRIORITY_RE.sub("", clean)
    # Remove wiki-link syntax but keep display text
    clean = _WIKI_LINK_RE.sub(lambda m: m.group(2) or m.group(1), clean)
    # Remove time-slot
    clean = _TIME_SLOT_RE.sub("", clean)
    # Collapse whitespace
    clean = re.sub(r"\s{2,}", " ", clean).strip()

    return VaultTask(
        text=clean,
        status=status,
        priority=priority,
        completion_date=completion_date,
        scheduled_date=scheduled_date,
        time_slot=time_slot,
        source_file=source_file,
        source_date=source_date,
        section=section,
        wiki_links=wiki_links,
        people=people,
        tags=tags,
        inline_comment=inline_comment,
        raw_line=line.rstrip(),
    )


# ── Section splitter ─────────────────────────────────────────────────

def _split_into_sections(body: str) -> list[tuple[str, int, str]]:
    """Split markdown body into (heading, level, content) tuples.

    Returns a list where each element is (heading_text, heading_level, everything_until_next_heading).
    Lines before the first heading get heading="" and level=0.
    """
    sections: list[tuple[str, int, str]] = []
    current_heading = ""
    current_level = 0
    current_lines: list[str] = []
    in_code_block = False

    for line in body.split("\n"):
        # Track code blocks to avoid treating ``` as headings
        if _CODE_BLOCK_RE.match(line.strip()):
            in_code_block = not in_code_block
            current_lines.append(line)
            continue

        if in_code_block:
            current_lines.append(line)
            continue

        hm = _HEADING_RE.match(line)
        if hm:
            # Save previous section
            sections.append((current_heading, current_level, "\n".join(current_lines)))
            current_heading = hm.group(2).strip()
            current_level = len(hm.group(1))
            current_lines = []
        else:
            current_lines.append(line)

    # Last section
    sections.append((current_heading, current_level, "\n".join(current_lines)))
    return sections


def _extract_bullet_items(text: str) -> list[str]:
    """Extract top-level bullet items from text (lines starting with ``-``)."""
    items = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- ") and not stripped.startswith("- ["):
            items.append(stripped[2:].strip())
    return items


def _extract_tasks_from_text(
    text: str,
    *,
    section: str = "",
    source_file: Path | None = None,
    source_date: date | None = None,
) -> list[VaultTask]:
    """Extract all checkbox tasks from a block of text."""
    tasks = []
    for line in text.split("\n"):
        task = parse_task_line(
            line.strip(),
            section=section,
            source_file=source_file,
            source_date=source_date,
        )
        if task:
            tasks.append(task)
    return tasks


def _strip_dataview_blocks(text: str) -> str:
    """Remove ```dataviewjs ... ``` code blocks."""
    result: list[str] = []
    in_code = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```") and not in_code:
            in_code = True
            continue
        if stripped.startswith("```") and in_code:
            in_code = False
            continue
        if not in_code:
            result.append(line)
    return "\n".join(result)


# ── Daily note parser ────────────────────────────────────────────────

def parse_daily_note(file_path: Path) -> DayNote | None:
    """Parse a daily note file into a DayNote object.

    Expected filename: ``YYYY-MM-DD.md``
    """
    stem = file_path.stem
    m = _DAILY_FILE_RE.match(stem)
    if not m:
        logger.warning("Skipping non-daily file: %s", file_path.name)
        return None

    note_date = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    text = file_path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)

    sleep = _extract_sleep_data(fm)
    energy = _extract_energy_data(fm)

    sections = _split_into_sections(body)

    day = DayNote(
        date=note_date,
        source_file=file_path,
        sleep=sleep,
        energy=energy,
        raw_frontmatter=fm,
    )

    # Walk through sections and populate the note
    current_h1 = ""
    for heading, level, content in sections:
        # Track top-level h1 for context
        if level == 1:
            current_h1 = heading

        heading_lower = heading.lower()

        # ── Фокус дня ───────────────────────────────────────
        if "фокус" in heading_lower:
            day.focus = _extract_bullet_items(content)

        # ── Основные дела ────────────────────────────────────
        elif "основные" in heading_lower and "дела" in heading_lower:
            day.tasks.extend(
                _extract_tasks_from_text(
                    content, section="Основные дела",
                    source_file=file_path, source_date=note_date,
                )
            )

        # ── Второстепенные задачи ────────────────────────────
        elif "второстепенные" in heading_lower:
            day.tasks.extend(
                _extract_tasks_from_text(
                    content, section="Второстепенные задачи",
                    source_file=file_path, source_date=note_date,
                )
            )

        # ── Чему я рад ──────────────────────────────────────
        elif "рад" in heading_lower or "получилось" in heading_lower:
            day.gratitude = content.strip()

        # ── Что пошло не так ─────────────────────────────────
        elif "не так" in heading_lower:
            # Sub-headings under this become individual problems
            sub_sections = _split_into_sections(content)
            for sub_h, sub_l, sub_c in sub_sections:
                if sub_h:
                    day.problems.append(ReflectionBlock(heading=sub_h, content=sub_c.strip()))

        # ── Заметки ──────────────────────────────────────────
        elif heading_lower == "заметки":
            day.notes_text = content.strip()

        # ── Надо подумать о ──────────────────────────────────
        elif "подумать" in heading_lower:
            tasks = _extract_tasks_from_text(
                content, section="Надо подумать о",
                source_file=file_path, source_date=note_date,
            )
            if tasks:
                day.think_about.extend(tasks)
            else:
                # Sometimes "think about" items are plain bullets
                for item in _extract_bullet_items(content):
                    day.think_about.append(
                        VaultTask(
                            text=item,
                            status=TaskStatus.OPEN,
                            priority=Priority.LOW,
                            section="Надо подумать о",
                            source_file=file_path,
                            source_date=note_date,
                            raw_line=f"- {item}",
                        )
                    )

    # Collect all wiki-links from the full body
    day.wiki_links = parse_wiki_links(body)

    return day


# ── Weekly note parser ───────────────────────────────────────────────

def parse_weekly_note(file_path: Path) -> WeeklyNote | None:
    """Parse a weekly note file into a WeeklyNote object.

    Expected filename: ``YYYY-Wnn.md``
    """
    stem = file_path.stem
    m = _WEEK_FILE_RE.match(stem)
    if not m:
        logger.warning("Skipping non-weekly file: %s", file_path.name)
        return None

    year, week = int(m.group(1)), int(m.group(2))
    text = file_path.read_text(encoding="utf-8")
    _, body = parse_frontmatter(text)

    # Strip dataview blocks so we only parse the review content
    clean_body = _strip_dataview_blocks(body)

    weekly = WeeklyNote(year=year, week=week, source_file=file_path)

    sections = _split_into_sections(clean_body)

    for heading, level, content in sections:
        hl = heading.lower()

        # ── Tasks section ────────────────────────────────────
        if "задач" in hl and ("список" in hl or level == 2):
            weekly.tasks = _extract_tasks_from_text(
                content, section="Список задач",
                source_file=file_path, source_date=None,
            )

        # ── Основной фокус ───────────────────────────────────
        elif "фокус" in hl:
            weekly.focus = _extract_bullet_items(content)

        # ── Ключевые достижения ──────────────────────────────
        elif "достижени" in hl:
            weekly.achievements = _extract_bullet_items(content)

        # ── Инсайты ──────────────────────────────────────────
        elif "инсайт" in hl:
            weekly.insights = _extract_bullet_items(content)

        # ── Причины отклонений ───────────────────────────────
        elif "отклонени" in hl or ("причин" in hl and "план" in hl):
            weekly.plan_deviations = _extract_bullet_items(content)

        # ── Что тормозило ────────────────────────────────────
        elif "тормози" in hl or ("проблем" in hl and "блок" in hl):
            weekly.problems = _extract_bullet_items(content)

        # ── Возможные решения ────────────────────────────────
        elif "решени" in hl:
            weekly.solutions = _extract_bullet_items(content)

        # ── Week mark ────────────────────────────────────────
        elif "мотивац" in hl or "самооценк" in hl:
            wm = _WEEK_MARK_RE.search(content)
            if wm:
                weekly.week_mark = int(wm.group(1))
            # Also search for checklist improvements
            if "порадовал" not in hl:
                weekly.reflections.append(ReflectionBlock(heading=heading, content=content.strip()))

        # ── Порадовало ───────────────────────────────────────
        elif "порадовал" in hl:
            weekly.reflections.append(ReflectionBlock(heading=heading, content=content.strip()))

        # ── Находки / ресурсы ────────────────────────────────
        elif "находк" in hl or "ресурс" in hl:
            weekly.resources = _extract_bullet_items(content)

        # ── Рефлексия (general) ──────────────────────────────
        elif "рефлекси" in hl:
            weekly.reflections.append(ReflectionBlock(heading=heading, content=content.strip()))

    # Week mark might also appear outside heading context
    wm_global = _WEEK_MARK_RE.search(clean_body)
    if wm_global and weekly.week_mark is None:
        weekly.week_mark = int(wm_global.group(1))

    weekly.wiki_links = parse_wiki_links(clean_body)

    return weekly


# ── Monthly note parser ──────────────────────────────────────────────

def parse_monthly_note(file_path: Path) -> MonthlyNote | None:
    """Parse a monthly note file into a MonthlyNote object.

    Expected filename: ``YYYY-MM.md``
    """
    stem = file_path.stem
    m = _MONTH_FILE_RE.match(stem)
    if not m:
        logger.warning("Skipping non-monthly file: %s", file_path.name)
        return None

    year, month = int(m.group(1)), int(m.group(2))
    text = file_path.read_text(encoding="utf-8")
    _, body = parse_frontmatter(text)

    monthly = MonthlyNote(year=year, month=month, source_file=file_path)

    sections = _split_into_sections(body)

    for heading, level, content in sections:
        hl = heading.lower()
        # Normalize: remove emoji number prefixes like "1️⃣"
        clean_heading = re.sub(r"[0-9️⃣🌱💡⚖🛠🧱🔋📚]+\s*", "", hl).strip()

        # ── Общая динамика ───────────────────────────────────
        if "динамик" in clean_heading:
            monthly.dynamics = content.strip()

        # ── Достижения ───────────────────────────────────────
        elif "достижени" in clean_heading:
            monthly.achievements = _extract_bullet_items(content)

        # ── Инсайты ──────────────────────────────────────────
        elif "инсайт" in clean_heading:
            monthly.insights = _extract_bullet_items(content)

        # ── Сравнение планов ─────────────────────────────────
        elif "план" in clean_heading and "факт" in clean_heading:
            monthly.plan_vs_fact = content.strip()

        # ── Навыки ───────────────────────────────────────────
        elif "навык" in clean_heading or "привычк" in clean_heading:
            monthly.skills = _extract_bullet_items(content)

        # ── Проблемы ─────────────────────────────────────────
        elif "проблем" in clean_heading or "блок" in clean_heading:
            monthly.problems = _extract_bullet_items(content)

        # ── Решения ──────────────────────────────────────────
        elif "решени" in clean_heading:
            monthly.solutions = _extract_bullet_items(content)

        # ── Самооценка ───────────────────────────────────────
        elif "самооценк" in clean_heading or "мотивац" in clean_heading:
            monthly.self_assessment = content.strip()
            score_m = _MONTH_SCORE_RE.search(content)
            if score_m:
                monthly.month_score = int(score_m.group(1))

        # ── Находки ──────────────────────────────────────────
        elif "находк" in clean_heading or "ресурс" in clean_heading:
            monthly.resources = _extract_bullet_items(content)

        # ── Рефлексия ────────────────────────────────────────
        elif "рефлекси" in clean_heading:
            monthly.reflection = content.strip()

    monthly.wiki_links = parse_wiki_links(body)

    return monthly


# ── Vault-level aggregation ──────────────────────────────────────────

class VaultParser:
    """High-level facade for parsing an entire vault notes directory.

    Args:
        vault_dir: Root directory containing ``daily/``, ``weekly/``, ``monthly/`` sub-dirs.
        daily_subdir: Name of daily notes sub-directory.
        weekly_subdir: Name of weekly notes sub-directory.
        monthly_subdir: Name of monthly notes sub-directory.
        people_dir: Optional path to the ``people/`` directory for person registry.
    """

    def __init__(
        self,
        vault_dir: str | Path,
        *,
        daily_subdir: str = "daily",
        weekly_subdir: str = "weekly",
        monthly_subdir: str = "monthly",
        people_dir: str | Path | None = None,
    ) -> None:
        self.vault_dir = Path(vault_dir)
        self.daily_dir = self.vault_dir / daily_subdir
        self.weekly_dir = self.vault_dir / weekly_subdir
        self.monthly_dir = self.vault_dir / monthly_subdir

        # People registry
        self._registry = None
        if people_dir:
            from vault_parser.people import load_people_registry, enrich_registry_from_notes
            self._registry = load_people_registry(people_dir)
            # Discover aliases from notes
            enrich_registry_from_notes(self._registry, self.vault_dir)

    @property
    def people_registry(self):
        """Access the people registry (may be None if no people_dir was set)."""
        return self._registry

    def _enrich_tasks_with_people(self, tasks: list[VaultTask]) -> None:
        """Post-process tasks: filter people list to only real persons from registry."""
        if not self._registry:
            return
        for task in tasks:
            real_people = []
            for wl in task.wiki_links:
                person = self._registry.lookup(wl.target) or (
                    self._registry.lookup(wl.alias) if wl.alias else None
                )
                if person and not person.is_group:
                    # Use canonical name (= filename) for cross-referencing
                    real_people.append(person.name)
            task.people = real_people

    # ── Parse all ────────────────────────────────────────────────
    def parse_daily_notes(self) -> list[DayNote]:
        """Parse all daily notes, sorted by date ascending."""
        if not self.daily_dir.exists():
            logger.warning("Daily notes directory not found: %s", self.daily_dir)
            return []
        notes = []
        for f in sorted(self.daily_dir.glob("*.md")):
            note = parse_daily_note(f)
            if note:
                self._enrich_tasks_with_people(note.tasks)
                self._enrich_tasks_with_people(note.think_about)
                notes.append(note)
        logger.info("Parsed %d daily notes from %s", len(notes), self.daily_dir)
        return notes

    def parse_weekly_notes(self) -> list[WeeklyNote]:
        """Parse all weekly notes, sorted by date ascending."""
        if not self.weekly_dir.exists():
            logger.warning("Weekly notes directory not found: %s", self.weekly_dir)
            return []
        notes = []
        for f in sorted(self.weekly_dir.glob("*.md")):
            note = parse_weekly_note(f)
            if note:
                self._enrich_tasks_with_people(note.tasks)
                notes.append(note)
        logger.info("Parsed %d weekly notes from %s", len(notes), self.weekly_dir)
        return notes

    def parse_monthly_notes(self) -> list[MonthlyNote]:
        """Parse all monthly notes, sorted by date ascending."""
        if not self.monthly_dir.exists():
            logger.warning("Monthly notes directory not found: %s", self.monthly_dir)
            return []
        notes = []
        for f in sorted(self.monthly_dir.glob("*.md")):
            note = parse_monthly_note(f)
            if note:
                notes.append(note)
        logger.info("Parsed %d monthly notes from %s", len(notes), self.monthly_dir)
        return notes

    def parse_all(
        self,
    ) -> dict[str, list[DayNote] | list[WeeklyNote] | list[MonthlyNote]]:
        """Parse all note types and return a dict keyed by type."""
        return {
            "daily": self.parse_daily_notes(),
            "weekly": self.parse_weekly_notes(),
            "monthly": self.parse_monthly_notes(),
        }

    # ── Convenience ──────────────────────────────────────────────
    def all_tasks(self) -> list[VaultTask]:
        """Gather all tasks from daily and weekly notes."""
        tasks: list[VaultTask] = []
        for day in self.parse_daily_notes():
            tasks.extend(day.all_tasks)
        for week in self.parse_weekly_notes():
            tasks.extend(week.tasks)
        return tasks

    def open_tasks(self) -> list[VaultTask]:
        """Return only open (uncompleted, non-cancelled) tasks."""
        return [t for t in self.all_tasks() if t.is_open]

    def tasks_for_date(self, target_date: date) -> list[VaultTask]:
        """Return tasks whose source date matches the given date."""
        return [t for t in self.all_tasks() if t.source_date == target_date]

    def tasks_mentioning(self, person: str) -> list[VaultTask]:
        """Return tasks mentioning a specific person.

        If a people registry is loaded, tries to resolve the person name first.
        """
        # Try to resolve via registry
        if self._registry:
            resolved = self._registry.lookup(person)
            if resolved:
                person = resolved.name

        person_lower = person.lower()
        return [
            t for t in self.all_tasks()
            if any(p.lower() == person_lower for p in t.people)
            or any(
                wl.target.lower() == person_lower or
                (wl.alias and wl.alias.lower() == person_lower)
                for wl in t.wiki_links
            )
        ]

    def search_tasks(self, query: str) -> list[VaultTask]:
        """Full-text search across task texts."""
        q = query.lower()
        return [t for t in self.all_tasks() if q in t.text.lower()]

