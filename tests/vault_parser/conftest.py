"""Shared fixtures for vault_parser tests.

All tests use tmp_path and in-memory markdown stubs instead of a real Obsidian vault.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from vault_parser.models import Priority, TaskStatus, VaultTask, TimeSlot, Recurrence
from vault_parser.writer.editor import DailyNoteEditor


# ── Markdown stubs ───────────────────────────────────────────────────

SAMPLE_DAILY_MD = """\
---
bed-time-start: "23:00"
sleep-start: "23:30"
sleep-end: "6:00"
sleep-duration: 6:30
sleep-quality: 7
quick-fall-asleep: true
night-awakenings: false
deep-sleep: true
remembered-dreams: false
no-nightmare: true
morning-mood: 6
no-phone: true
physical-exercise: false
late-dinner: true
morning-energy: 6
day-energy: 7
evening-energy: 5
---

## Фокус дня
- Модуль тестирования
- Ревью кода

## Основные дела
- [ ] 🔺 стендап 10:00-10:15 [[Иванов Иван]]
- [x] код ревью ⏳ 2025-12-01 ✅ 2025-12-01

## Второстепенные задачи
- [/] написать тесты #testing
- [-] отменённая задача

## Надо подумать о
- [ ] архитектура модулей

## Чему я рад и что получилось
Сделал много дел

## Заметки
Интересный день

## Что пошло не так
### Что случилось
Баг в продакшене
### Почему
Не хватило тестов
### Последствия
Откат
"""

SAMPLE_WEEKLY_MD = """\
---
week-mark: 7
---
## Рефлексия
Хорошая неделя

## Достижения
- Закончил модуль парсера
- Провёл 5 ревью
"""

SAMPLE_MONTHLY_MD = """\
---
tags: [monthly]
---
## Итоги месяца
Продуктивный месяц, закончил 3 проекта.

### Оценка
**7 из 10**

## Планы
- Запустить CI
"""

SAMPLE_PERSON_MD = """\
---
roles:
  - Backend разработчик
  - Тимлид
interests:
  - Python
  - Архитектура
tg: "@ivanov"
---
"""

SAMPLE_GROUP_MD = """\
---
---
## Участники
| Участник | Роль |
|----------|------|
| [[Иванов Иван]] | Тимлид |
| [[Петров Петр]] | Разработчик |
"""


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def sample_daily_md():
    """Raw markdown for a full daily note."""
    return SAMPLE_DAILY_MD


@pytest.fixture
def daily_note_file(tmp_path, sample_daily_md):
    """Create a daily note file at tmp_path/daily/2025-12-01.md."""
    daily_dir = tmp_path / "daily"
    daily_dir.mkdir()
    note = daily_dir / "2025-12-01.md"
    note.write_text(sample_daily_md, encoding="utf-8")
    return note


@pytest.fixture
def daily_dir(tmp_path):
    """Empty daily directory."""
    d = tmp_path / "daily"
    d.mkdir(exist_ok=True)
    return d


@pytest.fixture
def editor(daily_dir):
    """DailyNoteEditor pointing to tmp_path/daily."""
    return DailyNoteEditor(daily_dir)


@pytest.fixture
def editor_with_note(daily_dir, sample_daily_md):
    """DailyNoteEditor with a pre-existing note for 2025-12-01."""
    note = daily_dir / "2025-12-01.md"
    note.write_text(sample_daily_md, encoding="utf-8")
    return DailyNoteEditor(daily_dir)


@pytest.fixture
def people_dir(tmp_path):
    """Create a people directory with stub person/group files."""
    d = tmp_path / "people"
    d.mkdir()
    # Group file must start with "Группа" for _parse_person_file to detect is_group
    (d / "Иванов Иван.md").write_text(SAMPLE_PERSON_MD, encoding="utf-8")
    (d / "Группа Backend.md").write_text(SAMPLE_GROUP_MD, encoding="utf-8")
    return d


def make_task(
    text="тест",
    status=TaskStatus.OPEN,
    priority=Priority.NORMAL,
    section="",
    source_date=None,
    scheduled_date=None,
    people=None,
    time_slot=None,
    raw_line="",
) -> VaultTask:
    """Helper to create VaultTask with minimal boilerplate."""
    return VaultTask(
        text=text,
        status=status,
        priority=priority,
        section=section,
        source_date=source_date,
        scheduled_date=scheduled_date,
        people=people or [],
        time_slot=time_slot,
        raw_line=raw_line,
    )
