"""YAML frontmatter helpers for daily note editing."""
from __future__ import annotations

import re
from typing import Any

import yaml

# Keys in strict template order
FM_KEY_ORDER = [
    "bed-time-start",
    "sleep-start",
    "sleep-end",
    "quick-fall-asleep",
    "night-awakenings",
    "deep-sleep",
    "remembered-dreams",
    "no-nightmare",
    "morning-mood",
    "sleep-quality",
    "no-phone",
    "physical-exercise:",  # note the trailing colon in template
    "late-dinner",
    "sleep-duration",
    "morning-energy",
    "day-energy",
    "evening-energy",
]

# Friendly Python kwargs → YAML keys (sleep)
SLEEP_KWARGS_MAP = {
    "bed_time_start": "bed-time-start",
    "sleep_start": "sleep-start",
    "sleep_end": "sleep-end",
    "quick_fall_asleep": "quick-fall-asleep",
    "night_awakenings": "night-awakenings",
    "deep_sleep": "deep-sleep",
    "remembered_dreams": "remembered-dreams",
    "no_nightmare": "no-nightmare",
    "morning_mood": "morning-mood",
    "sleep_quality": "sleep-quality",
    "no_phone": "no-phone",
    "physical_exercise": "physical-exercise:",
    "late_dinner": "late-dinner",
    "sleep_duration": "sleep-duration",
}

# Friendly Python kwargs → YAML keys (energy)
ENERGY_KWARGS_MAP = {
    "morning": "morning-energy",
    "day": "day-energy",
    "evening": "evening-energy",
}


def parse_raw_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter dict and body from raw note text."""
    if not text.strip().startswith("---"):
        return {}, text

    end = text.find("\n---", 3)
    if end == -1:
        return {}, text

    fm_raw = text[3:end].strip()
    body = text[end + 4:]

    try:
        fm = yaml.safe_load(fm_raw)
        if not isinstance(fm, dict):
            fm = {}
    except yaml.YAMLError:
        fm = {}

    return fm, body


def serialize_frontmatter(fm: dict[str, Any]) -> str:
    """Serialize frontmatter dict to YAML string in template key order."""
    lines = ["---"]

    seen: set[str] = set()
    for key in FM_KEY_ORDER:
        if key in fm:
            seen.add(key)
            lines.append(_format_fm_line(key, fm[key]))

    for key, val in fm.items():
        if key not in seen:
            lines.append(_format_fm_line(key, val))

    lines.append("---")
    return "\n".join(lines)


def _format_fm_line(key: str, val: Any) -> str:
    """Format a single YAML frontmatter line."""
    if key == "physical-exercise:":
        if val is None or val == "":
            return '"physical-exercise:":'
        return f'"physical-exercise:": {_yaml_val(val)}'

    if val is None or val == "":
        return f"{key}:"
    return f"{key}: {_yaml_val(val)}"


def _yaml_val(val: Any) -> str:
    """Format a YAML value inline."""
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val)
    if re.match(r"^\d{1,2}:\d{2}$", s):
        return f'"{s}"'
    return s
