"""Markdown section manipulation for daily note editing."""
from __future__ import annotations

import re

# Section markers in the daily note template
SECTION_MARKERS = {
    "plans": "# Планы на день",
    "focus": "## Фокус дня",
    "main": "## Основные дела",
    "secondary": "## Второстепенные задачи",
    "gratitude": "# Чему я рад и что получилось",
    "problems": "# Что пошло не так",
    "notes": "# Заметки",
    "think_about": "# Надо подумать о",
}

# Template section order with separators
_SECTION_ORDER = [
    ("# Планы на день", None),
    ("## Фокус дня", None),
    ("## Основные дела", None),
    ("## Второстепенные задачи", None),
    ("# Чему я рад и что получилось", "---"),
    ("# Что пошло не так", "___"),
    ("# Заметки", "---"),
    ("# Надо подумать о", "---"),
]

_HEADING_RE = re.compile(r"^(#{1,6})\s+")


def split_sections(body: str) -> dict[str, str]:
    """Split markdown body into named sections.

    Returns dict mapping section heading → content (without the heading).
    """
    sections: dict[str, str] = {}
    all_markers = set(SECTION_MARKERS.values())

    lines = body.split("\n")
    current_heading = "__preamble__"
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        matched = False
        for marker in all_markers:
            if stripped == marker or stripped.startswith(marker + " "):
                sections[current_heading] = "\n".join(current_lines)
                current_heading = stripped
                current_lines = []
                matched = True
                break
        if not matched:
            current_lines.append(line)

    sections[current_heading] = "\n".join(current_lines)
    return sections


def heading_level(heading: str) -> int:
    """Return the heading level (number of # characters)."""
    m = _HEADING_RE.match(heading)
    return len(m.group(1)) if m else 0
