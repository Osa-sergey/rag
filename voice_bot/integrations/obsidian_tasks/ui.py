"""Telegram inline UI for Obsidian task management.

Keyboards for confirmation, field editing, task list actions.
Supports all enriched task fields: people, start/scheduled dates,
time slot, recurrence, priority, tags.
"""
from __future__ import annotations

from datetime import date, timedelta

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from voice_bot.integrations.obsidian_tasks.schemas import AgendaData, ObsidianTask

# ── Callback prefixes (≤ 64 bytes total per callback_data) ────

CB_TASK_CONFIRM    = "t:confirm"
CB_TASK_CANCEL     = "t:cancel"
CB_TASK_EDIT       = "t:edit:"      # t:edit:<field>
CB_TASK_SET        = "t:set:"       # t:set:<field>:<value>
CB_TASK_BACK       = "t:back"

# Task list actions
CB_LIST_DONE       = "tl:done:"
CB_LIST_DELETE     = "tl:del:"
CB_LIST_EDIT       = "tl:edit:"
CB_LIST_NAV        = "tl:nav:"

# Task edit (from list)
CB_EDIT_CONFIRM    = "te:confirm"
CB_EDIT_CANCEL     = "te:cancel"
CB_EDIT_FIELD      = "te:field:"
CB_EDIT_SET        = "te:set:"

PRIORITIES = [
    ("⏫ Высокий",  "high"),
    ("🔼 Средний",  "medium"),
    ("🔽 Низкий",   "low"),
    ("📋 Обычный",  "normal"),
]

RECURRENCE_PRESETS = [
    ("Каждый день",  "every day"),
    ("Каждую неделю","every week"),
    ("Каждый пн",   "every monday"),
    ("Пн/Ср/Пт",    "every mon,wed,fri"),
    ("Пн-Пт",       "every mon,tue,wed,thu,fri"),
    ("Каждый месяц","every month"),
]


# ── Formatters ────────────────────────────────────────────────


def format_task_preview(task: ObsidianTask) -> str:
    """Full confirmation card (calls model's own formatter)."""
    return task.format_full_preview()


def format_task_list(
    tasks: list[ObsidianTask],
    day: date,
    page: int = 0,
    page_size: int = 5,
) -> str:
    if not tasks:
        return f"📭 *Нет задач на {day.isoformat()}*"

    total = len(tasks)
    start = page * page_size
    end = min(start + page_size, total)
    lines = [f"📋 *Задачи на {day.isoformat()}* ({total} шт.)\n"]
    for i, task in enumerate(tasks[start:end], start=start + 1):
        lines.append(task.format_preview(index=i))
    if total > page_size:
        lines.append(f"\n_Стр. {page + 1}/{(total + page_size - 1) // page_size}_")
    return "\n".join(lines)


# ── Task confirmation keyboard ─────────────────────────────────


def kb_task_confirm(task: ObsidianTask) -> InlineKeyboardMarkup:
    """Main confirmation keyboard — edit any field, confirm, or cancel."""
    rows = [
        [
            InlineKeyboardButton(text="📌 Название",  callback_data=f"{CB_TASK_EDIT}title"),
            InlineKeyboardButton(text="📅 Срок",       callback_data=f"{CB_TASK_EDIT}date"),
        ],
        [
            InlineKeyboardButton(text="🏷 Приоритет", callback_data=f"{CB_TASK_EDIT}priority"),
            InlineKeyboardButton(text="🔖 Теги",       callback_data=f"{CB_TASK_EDIT}tags"),
        ],
        [
            InlineKeyboardButton(text="👤 Люди",       callback_data=f"{CB_TASK_EDIT}people"),
            InlineKeyboardButton(text="🕐 Время",      callback_data=f"{CB_TASK_EDIT}time_slot"),
        ],
        [
            InlineKeyboardButton(text="🛫 Начало",     callback_data=f"{CB_TASK_EDIT}start_date"),
            InlineKeyboardButton(text="🔁 Повтор",     callback_data=f"{CB_TASK_EDIT}recurrence"),
        ],
        [
            InlineKeyboardButton(text="✅ Создать задачу", callback_data=CB_TASK_CONFIRM),
            InlineKeyboardButton(text="❌ Отмена",         callback_data=CB_TASK_CANCEL),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Priority keyboard ─────────────────────────────────────────


def kb_priority_select(cb_prefix: str = CB_TASK_SET) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"{cb_prefix}priority:{val}")]
        for label, val in PRIORITIES
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=CB_TASK_BACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Date keyboards ────────────────────────────────────────────

def _date_shortcuts(cb_prefix: str, field: str) -> list[list[InlineKeyboardButton]]:
    """Quick-pick date buttons (today, tomorrow, …)."""
    today = date.today()
    shortcuts = [
        ("Сегодня",    0),
        ("Завтра",     1),
        ("Послезавтра",2),
        ("Через 3 дня",3),
        ("Через неделю",7),
    ]
    rows = []
    for label, delta in shortcuts:
        d = today + timedelta(days=delta)
        rows.append([InlineKeyboardButton(
            text=f"{label} ({d.isoformat()})",
            callback_data=f"{cb_prefix}{field}:{d.isoformat()}",
        )])
    return rows


def kb_date_select(
    field: str = "date",
    cb_prefix: str = CB_TASK_SET,
) -> InlineKeyboardMarkup:
    rows = _date_shortcuts(cb_prefix, field)
    rows.append([InlineKeyboardButton(
        text="✏️ Ввести вручную",
        callback_data=f"{CB_TASK_EDIT}{field}_custom",
    )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=CB_TASK_BACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Recurrence keyboard ───────────────────────────────────────


def kb_recurrence_select(cb_prefix: str = CB_TASK_SET) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"{cb_prefix}recurrence:{val}")]
        for label, val in RECURRENCE_PRESETS
    ]
    rows.append([InlineKeyboardButton(
        text="✏️ Своё правило",
        callback_data=f"{CB_TASK_EDIT}recurrence_custom",
    )])
    rows.append([InlineKeyboardButton(
        text="🚫 Без повтора",
        callback_data=f"{cb_prefix}recurrence:",
    )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=CB_TASK_BACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── People keyboard ───────────────────────────────────────────


def kb_people_select(
    all_names: list[str],
    selected: list[str],
    cb_prefix: str = CB_TASK_SET,
) -> InlineKeyboardMarkup:
    """Show all vault people. Selected ones get a ✅ prefix.

    Clicking a name toggles it (add/remove from selection).
    """
    rows: list[list[InlineKeyboardButton]] = []
    # Show max 20 people (Telegram limit)
    for name in all_names[:20]:
        tick = "✅ " if name in selected else ""
        rows.append([InlineKeyboardButton(
            text=f"{tick}{name}",
            callback_data=f"{cb_prefix}people_toggle:{name}",
        )])
    rows.append([InlineKeyboardButton(
        text="✏️ Ввести вручную",
        callback_data=f"{CB_TASK_EDIT}people_custom",
    )])
    rows.append([
        InlineKeyboardButton(text="🗑 Очистить", callback_data=f"{cb_prefix}people_clear:"),
        InlineKeyboardButton(text="✔ Готово",    callback_data=CB_TASK_BACK),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Text prompt keyboard (while waiting for free-text input) ──


def kb_text_prompt(back_cb: str = CB_TASK_BACK) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад (без изменений)", callback_data=back_cb),
    ]])


# ── Task list keyboard ────────────────────────────────────────


def kb_task_list(
    tasks: list[ObsidianTask],
    day: date,
    page: int = 0,
    page_size: int = 5,
) -> InlineKeyboardMarkup:
    total = len(tasks)
    start = page * page_size
    end = min(start + page_size, total)
    total_pages = max(1, (total + page_size - 1) // page_size)

    rows: list[list[InlineKeyboardButton]] = []
    for i in range(start, end):
        rows.append([
            InlineKeyboardButton(text=f"✅ #{i+1}", callback_data=f"{CB_LIST_DONE}{i}"),
            InlineKeyboardButton(text=f"✏️ #{i+1}", callback_data=f"{CB_LIST_EDIT}{i}"),
            InlineKeyboardButton(text=f"🗑 #{i+1}", callback_data=f"{CB_LIST_DELETE}{i}"),
        ])

    # Date navigation
    prev_day = day - timedelta(days=1)
    next_day = day + timedelta(days=1)
    rows.append([
        InlineKeyboardButton(
            text=f"◀ {prev_day.strftime('%d.%m')}",
            callback_data=f"{CB_LIST_NAV}date:{prev_day.isoformat()}",
        ),
        InlineKeyboardButton(text="📅 Дата", callback_data=f"{CB_TASK_EDIT}list_date"),
        InlineKeyboardButton(
            text=f"{next_day.strftime('%d.%m')} ▶",
            callback_data=f"{CB_LIST_NAV}date:{next_day.isoformat()}",
        ),
    ])

    # Page nav
    if total_pages > 1:
        page_row = []
        if page > 0:
            page_row.append(InlineKeyboardButton(
                text="⬅️", callback_data=f"{CB_LIST_NAV}page:{page-1}",
            ))
        if page < total_pages - 1:
            page_row.append(InlineKeyboardButton(
                text="➡️", callback_data=f"{CB_LIST_NAV}page:{page+1}",
            ))
        if page_row:
            rows.append(page_row)

    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Task edit keyboard (from list) ────────────────────────────


def kb_task_edit(task: ObsidianTask, task_idx: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="📌 Название",  callback_data=f"{CB_EDIT_FIELD}title:{task_idx}"),
            InlineKeyboardButton(text="📅 Срок",       callback_data=f"{CB_EDIT_FIELD}date:{task_idx}"),
        ],
        [
            InlineKeyboardButton(text="🏷 Приоритет", callback_data=f"{CB_EDIT_FIELD}priority:{task_idx}"),
            InlineKeyboardButton(text="🔖 Теги",       callback_data=f"{CB_EDIT_FIELD}tags:{task_idx}"),
        ],
        [
            InlineKeyboardButton(text="👤 Люди",       callback_data=f"{CB_EDIT_FIELD}people:{task_idx}"),
            InlineKeyboardButton(text="🔁 Повтор",     callback_data=f"{CB_EDIT_FIELD}recurrence:{task_idx}"),
        ],
        [
            InlineKeyboardButton(text="✅ Сохранить", callback_data=f"{CB_EDIT_CONFIRM}:{task_idx}"),
            InlineKeyboardButton(text="❌ Отмена",     callback_data=CB_EDIT_CANCEL),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Delete confirmation keyboard ──────────────────────────────


def kb_delete_confirm(task_idx: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🗑 Да, удалить",
            callback_data=f"tl:del_confirm:{task_idx}",
        ),
        InlineKeyboardButton(text="⬅️ Нет, назад", callback_data=CB_TASK_BACK),
    ]])


# ── Agenda ────────────────────────────────────────────────────

CB_AGENDA_NAV = "ag:nav:"   # ag:nav:YYYY-MM-DD

_MONTH_RU = [
    "января", "февраля", "марта", "апреля",
    "мая", "июня", "июля", "августа",
    "сентября", "октября", "ноября", "декабря",
]

_PRIORITY_LABEL = {
    "high":   "⏫ Высокий приоритет",
    "medium": "🔼 Средний приоритет",
    "normal": "📋 Обычный приоритет",
    "low":    "🔽 Низкий приоритет",
}


def format_agenda(agenda: AgendaData) -> str:
    """Render AgendaData as a Markdown string for Telegram."""
    day = agenda.day
    date_str = f"{day.day} {_MONTH_RU[day.month - 1]} {day.year}"
    lines = [f"📅 *Агенда — {date_str}, {agenda.weekday}*\n"]

    # LLM summary
    if agenda.summary:
        lines.append(f"💡 *Главное за день:*\n_{agenda.summary}_\n")

    # Focus
    if agenda.focus:
        lines.append("🎯 *Фокус дня:*")
        for item in agenda.focus:
            lines.append(f"  • {item}")
        lines.append("")

    # Tasks by priority
    if agenda.total > 0:
        lines.append(f"📋 *Задачи* ({agenda.open} открыто / {agenda.done} закрыто):\n")
        for priority, tasks in agenda.tasks_by_priority.items():
            open_tasks = [t for t in tasks if t.status != "done"]
            done_tasks = [t for t in tasks if t.status == "done"]
            if open_tasks:
                lines.append(f"*{_PRIORITY_LABEL.get(priority, priority)}:*")
                for t in open_tasks:
                    time_prefix = f"🕐 {t.time_slot}  " if t.time_slot else "  "
                    people_str = " " + " ".join(f"[[{p}]]" for p in t.people) if t.people else ""
                    lines.append(f"{time_prefix}☐ {t.title}{people_str}")
                lines.append("")
            if done_tasks:
                if "✅" not in "".join(lines):
                    lines.append(f"✅ *Выполнено ({agenda.done}):*")
                for t in done_tasks:
                    lines.append(f"  ✅ {t.title}")
                lines.append("")
    else:
        lines.append("📭 *Нет задач на этот день*\n")

    # People
    if agenda.people_involved:
        lines.append(f"👤 *Люди:* {', '.join(agenda.people_involved)}")

    # Stats
    if agenda.total > 0:
        lines.append(f"📊 Всего: {agenda.total} задач ({agenda.open} открыто, {agenda.done} закрыто)")

    return "\n".join(lines)


def kb_agenda_nav(day: date) -> InlineKeyboardMarkup:
    """Day navigation: ← yesterday / today / tomorrow →."""
    prev_day = day - timedelta(days=1)
    next_day = day + timedelta(days=1)
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=f"◀ {prev_day.strftime('%d.%m')}",
            callback_data=f"{CB_AGENDA_NAV}{prev_day.isoformat()}",
        ),
        InlineKeyboardButton(
            text="📅 Сегодня",
            callback_data=f"{CB_AGENDA_NAV}{date.today().isoformat()}",
        ),
        InlineKeyboardButton(
            text=f"{next_day.strftime('%d.%m')} ▶",
            callback_data=f"{CB_AGENDA_NAV}{next_day.isoformat()}",
        ),
    ]])

