"""Telegram FSM handlers for Obsidian task management.

Supports full task creation with all enriched fields:
  people, start_date, scheduled_date, time_slot, recurrence, priority, tags.

All UI runs in-place via edit_text on a single message.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from voice_bot.integrations.obsidian_tasks.schemas import ObsidianTask
from voice_bot.integrations.obsidian_tasks.ui import (
    CB_AGENDA_NAV,
    CB_EDIT_CANCEL,
    CB_EDIT_CONFIRM,
    CB_EDIT_FIELD,
    CB_EDIT_SET,
    CB_LIST_DELETE,
    CB_LIST_DONE,
    CB_LIST_EDIT,
    CB_LIST_NAV,
    CB_TASK_BACK,
    CB_TASK_CANCEL,
    CB_TASK_CONFIRM,
    CB_TASK_EDIT,
    CB_TASK_SET,
    format_agenda,
    format_task_list,
    format_task_preview,
    kb_agenda_nav,
    kb_date_select,
    kb_delete_confirm,
    kb_people_select,
    kb_priority_select,
    kb_recurrence_select,
    kb_task_confirm,
    kb_task_edit,
    kb_task_list,
    kb_text_prompt,
)

logger = logging.getLogger(__name__)
task_router = Router()

# ── FSM state keys ─────────────────────────────────────────────
_TASK_KEY     = "pending_task"
_TASKS_KEY    = "task_list"
_DAY_KEY      = "view_day"
_PAGE_KEY     = "view_page"
_MSG_KEY      = "task_msg_id"
_EDIT_IDX_KEY = "edit_task_idx"


# ── FSM States ─────────────────────────────────────────────────


class TaskStates(StatesGroup):
    # Creation flow
    creating              = State()
    editing_title         = State()
    editing_tags          = State()
    editing_date_custom   = State()   # due date
    editing_start_custom  = State()   # start_date custom text
    editing_sched_custom  = State()   # scheduled_date custom text
    editing_time_slot     = State()
    editing_recurrence_custom = State()
    editing_people_custom = State()   # free-text people input

    # Update flow
    updating_task         = State()   # showing matched task + changes for confirmation
    updating_select       = State()   # multiple matches — user picks one

    # List view
    viewing_list          = State()
    deleting_confirm      = State()

    # Agenda view
    viewing_agenda        = State()

    # Edit from list
    editing_task          = State()
    editing_task_title    = State()
    editing_task_tags     = State()


# ── Helpers ────────────────────────────────────────────────────


def _load_task(data: dict) -> ObsidianTask:
    return ObsidianTask.from_json(data[_TASK_KEY])


def _save_task(task: ObsidianTask) -> dict:
    return {_TASK_KEY: task.to_json()}


def _load_tasks(data: dict) -> list[ObsidianTask]:
    return [ObsidianTask.from_json(s) for s in json.loads(data.get(_TASKS_KEY, "[]"))]


def _save_tasks(tasks: list[ObsidianTask]) -> dict:
    return {_TASKS_KEY: json.dumps([t.to_json() for t in tasks])}


async def _back_to_preview(query: CallbackQuery, state: FSMContext) -> None:
    """Return to task creation preview."""
    await state.set_state(TaskStates.creating)
    data = await state.get_data()
    task = _load_task(data)
    await query.message.edit_text(
        format_task_preview(task),
        reply_markup=kb_task_confirm(task),
        parse_mode="Markdown",
    )


async def _update_preview_from_text(
    message: Message, state: FSMContext, bot: Bot,
    field: str, value,
) -> None:
    """Delete user's text message, update original preview in-place."""
    data = await state.get_data()
    task = _load_task(data)
    setattr(task, field, value)
    await state.update_data(_save_task(task))
    await state.set_state(TaskStates.creating)
    await message.delete()
    msg_id = data.get(_MSG_KEY)
    if msg_id:
        await bot.edit_message_text(
            chat_id=message.chat.id, message_id=msg_id,
            text=format_task_preview(task),
            reply_markup=kb_task_confirm(task), parse_mode="Markdown",
        )


async def _refresh_list_message(query: CallbackQuery, state: FSMContext, vault) -> None:
    data = await state.get_data()
    day_str = data.get(_DAY_KEY, date.today().isoformat())
    page = data.get(_PAGE_KEY, 0)
    day = date.fromisoformat(day_str)
    tasks = vault.read_tasks(day, include_done=True)
    await state.update_data({**_save_tasks(tasks), _DAY_KEY: day_str, _PAGE_KEY: page})
    await query.message.edit_text(
        format_task_list(tasks, day, page=page),
        reply_markup=kb_task_list(tasks, day, page=page),
        parse_mode="Markdown",
    )


# ── Entry points ───────────────────────────────────────────────


async def start_task_create(
    message: Message,
    state: FSMContext,
    text: str,
    task_extractor,
    date_parser,
    status_msg: Message | None = None,
) -> None:
    """Extract all task fields from voice text and show confirmation preview."""
    if status_msg is None:
        status_msg = await message.answer("⏳ Извлекаю задачу...")
    else:
        await status_msg.edit_text("⏳ Извлекаю задачу...")

    try:
        extracted = await task_extractor.extract_create(text)
    except Exception as e:
        logger.error("Task extraction failed: %s", e)
        await status_msg.edit_text(f"⚠️ Ошибка извлечения задачи: {e}")
        return

    # Resolve all date fields through DateParser
    due_date        = date_parser.parse(extracted.date_raw or extracted.date or "")
    start_date      = date_parser.parse(extracted.start_date_raw) if extracted.start_date_raw else None
    scheduled_date  = date_parser.parse(extracted.scheduled_date_raw) if extracted.scheduled_date_raw else None

    task = ObsidianTask(
        title=extracted.title,
        date=due_date.isoformat(),
        priority=extracted.priority,
        tags=extracted.tags,
        notes=extracted.notes,
        start_date=start_date.isoformat() if start_date else "",
        scheduled_date=scheduled_date.isoformat() if scheduled_date else "",
        time_slot=extracted.time_slot,
        recurrence=extracted.recurrence,
        people=extracted.people,
    )

    await state.set_state(TaskStates.creating)
    await state.update_data({**_save_task(task), _MSG_KEY: status_msg.message_id})
    await status_msg.edit_text(
        format_task_preview(task),
        reply_markup=kb_task_confirm(task),
        parse_mode="Markdown",
    )


async def start_task_update(
    message: Message,
    state: FSMContext,
    text: str,
    task_extractor,
    date_parser,
    vault,
    status_msg: Message | None = None,
) -> None:
    """Extract update request from voice, find matching tasks, apply changes.

    Flow:
      1. LLM extracts search_query + changes.
      2. Vault searches matching tasks (by title substring).
      3a. Exactly one match: apply changes, show confirmation.
      3b. Multiple matches: show numbered list, user picks one.
      3c. No matches: show error message.
    """
    if status_msg is None:
        status_msg = await message.answer("🔄 Ищу задачу для обновления...")
    else:
        await status_msg.edit_text("🔄 Ищу задачу для обновления...")

    try:
        update_req = await task_extractor.extract_update(text)
    except Exception as e:
        logger.error("Task update extraction failed: %s", e)
        await status_msg.edit_text(f"⚠️ Ошибка извлечения запроса обновления: {e}")
        return

    # Resolve search date
    search_day = date_parser.parse(update_req.search_date) if update_req.search_date else date.today()

    # Search matching tasks (by substring in title, case-insensitive)
    query_lower = update_req.search_query.lower()
    all_tasks = vault.read_tasks(search_day, include_done=False)
    matches = [t for t in all_tasks if query_lower and query_lower in t.title.lower()]

    if not matches:
        await status_msg.edit_text(
            f"❌ Задача *«{update_req.search_query}»* не найдена на {search_day.isoformat()}.\n"
            "Попробуйте уточнить название или дату.",
            parse_mode="Markdown",
        )
        return

    # Apply changes to best match
    original = matches[0]
    updated = _apply_update(original, update_req, date_parser, vault)

    # Format diff for confirmation
    diff_lines = ["*✏️ Обновление задачи — подтвердите:*\n"]
    diff_lines.append(f"Найдена: {original.format_preview()}\n")
    diff_lines.append("*Изменения:*")
    if updated.title != original.title:
        diff_lines.append(f"📌 {original.title} → *{updated.title}*")
    if updated.date != original.date:
        diff_lines.append(f"📅 {original.date or '—'} → *{updated.date or '—'}*")
    if updated.priority != original.priority:
        diff_lines.append(f"🏷 {original.priority} → *{updated.priority}*")
    if updated.recurrence != original.recurrence:
        diff_lines.append(f"🔁 {original.recurrence or '—'} → *{updated.recurrence or '—'}*")
    if updated.time_slot != original.time_slot:
        diff_lines.append(f"🕐 {original.time_slot or '—'} → *{updated.time_slot or '—'}*")
    if updated.people != original.people:
        diff_lines.append(f"👤 {', '.join(original.people) or '—'} → *{', '.join(updated.people) or '—'}*")

    await state.set_state(TaskStates.updating_task)
    await state.update_data({
        **_save_task(updated),
        "_original_task": original.to_json(),
        _MSG_KEY: status_msg.message_id,
    })

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Применить",   callback_data="tu:confirm"),
        InlineKeyboardButton(text="✏️ Изменить ещё", callback_data=f"{CB_TASK_EDIT}priority"),
        InlineKeyboardButton(text="❌ Отмена",       callback_data=CB_TASK_CANCEL),
    ]])
    await status_msg.edit_text(
        "\n".join(diff_lines) if len(diff_lines) > 2 else
        f"🔄 Задача без изменений?\n{original.format_preview()}",
        reply_markup=kb, parse_mode="Markdown",
    )


def _apply_update(original: ObsidianTask, req, date_parser, vault) -> ObsidianTask:
    """Apply ExtractedTaskUpdate fields to an existing ObsidianTask copy."""
    from dataclasses import replace as dc_replace
    updated = ObsidianTask.from_json(original.to_json())  # deep copy

    if req.new_title:
        updated.title = req.new_title
    if req.new_date:
        d = date_parser.parse(req.new_date)
        updated.date = d.isoformat()
    if req.new_priority:
        updated.priority = req.new_priority
    if req.new_recurrence is not None and req.new_recurrence != "":
        updated.recurrence = req.new_recurrence
    if req.new_time_slot is not None and req.new_time_slot != "":
        updated.time_slot = req.new_time_slot
    if req.people_add:
        resolved = vault.resolve_people(req.people_add)
        for p in resolved:
            if p not in updated.people:
                updated.people.append(p)
    if req.people_remove:
        resolved = vault.resolve_people(req.people_remove)
        updated.people = [p for p in updated.people if p not in resolved]

    return updated


@task_router.callback_query(F.data == "tu:confirm", TaskStates.updating_task)
async def on_update_confirm(query: CallbackQuery, state: FSMContext, vault) -> None:
    """Apply the update: delete old task, write new one."""
    await query.answer("💾 Обновляю...")
    data = await state.get_data()
    original = ObsidianTask.from_json(data["_original_task"])
    updated = _load_task(data)
    try:
        vault.update_task(original, updated)
        await query.message.edit_text(
            f"✅ *Задача обновлена!*\n\n{updated.format_preview()}",
            reply_markup=None, parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("Vault update failed: %s", e)
        await query.message.edit_text(f"⚠️ Ошибка обновления: `{e}`", parse_mode="Markdown")
        return
    await state.clear()


# ── Agenda ─────────────────────────────────────────────────────


async def start_agenda_show(
    message: Message,
    state: FSMContext,
    text: str,
    task_extractor,
    date_parser,
    vault,
    status_msg: Message | None = None,
) -> None:
    """Build and display a day agenda with LLM summary."""
    if status_msg is None:
        status_msg = await message.answer("📅 Собираю агенду...")
    else:
        await status_msg.edit_text("📅 Собираю агенду...")

    # 1. Determine date from voice text
    try:
        query_obj = await task_extractor.extract_show_query(text)
        day = date_parser.parse(query_obj.date_raw or query_obj.date or "")
    except Exception:
        day = date.today()

    await _render_agenda(status_msg, state, day, task_extractor, vault)


async def _render_agenda(
    msg: Message,
    state: FSMContext,
    day: date,
    task_extractor,
    vault,
) -> None:
    """Build agenda, run LLM summary, render + send."""
    agenda = vault.build_agenda(day)

    # 2. Build plain text for LLM summarization
    plain_parts: list[str] = []
    if agenda.focus:
        plain_parts.append("Фокус дня: " + "; ".join(agenda.focus))
    for priority, tasks in agenda.tasks_by_priority.items():
        for t in tasks:
            time_str = f"{t.time_slot} " if t.time_slot else ""
            people_str = f" ({', '.join(t.people)})" if t.people else ""
            status_str = "[готово] " if t.status == "done" else ""
            plain_parts.append(f"{status_str}{time_str}{t.title}{people_str}")

    # 3. LLM summary (only if there's something to summarize)
    if plain_parts:
        try:
            agenda.summary = await task_extractor.summarize_agenda("\n".join(plain_parts))
        except Exception as e:
            logger.warning("Agenda summarization failed: %s", e)

    # 4. Render
    await state.set_state(TaskStates.viewing_agenda)
    await state.update_data({_DAY_KEY: day.isoformat(), _MSG_KEY: msg.message_id})
    await msg.edit_text(
        format_agenda(agenda),
        reply_markup=kb_agenda_nav(day),
        parse_mode="Markdown",
    )


@task_router.callback_query(F.data.startswith(CB_AGENDA_NAV), TaskStates.viewing_agenda)
async def on_agenda_nav(
    query: CallbackQuery, state: FSMContext, vault, task_extractor,
) -> None:
    """Navigate to another day's agenda."""
    date_str = query.data[len(CB_AGENDA_NAV):]
    try:
        day = date.fromisoformat(date_str)
    except ValueError:
        day = date.today()
    await query.answer(f"📅 {day.isoformat()}")
    await _render_agenda(query.message, state, day, task_extractor, vault)


async def start_task_show(
    message: Message,
    state: FSMContext,
    text: str,
    task_extractor,
    date_parser,
    vault,
    status_msg: Message | None = None,
) -> None:
    """Show task list for the date extracted from text."""
    if status_msg is None:
        status_msg = await message.answer("📋 Загружаю задачи...")
    else:
        await status_msg.edit_text("📋 Загружаю задачи...")

    try:
        query_obj = await task_extractor.extract_show_query(text)
        day = date_parser.parse(query_obj.date_raw or query_obj.date or "")
    except Exception:
        day = date.today()

    tasks = vault.read_tasks(day, include_done=True)
    await state.set_state(TaskStates.viewing_list)
    await state.update_data({
        **_save_tasks(tasks),
        _DAY_KEY: day.isoformat(),
        _PAGE_KEY: 0,
        _MSG_KEY: status_msg.message_id,
    })
    await status_msg.edit_text(
        format_task_list(tasks, day),
        reply_markup=kb_task_list(tasks, day),
        parse_mode="Markdown",
    )


# ── Confirm / Cancel ───────────────────────────────────────────


@task_router.callback_query(F.data == CB_TASK_CONFIRM, TaskStates.creating)
async def on_task_confirm(query: CallbackQuery, state: FSMContext, vault) -> None:
    await query.answer("Сохраняю в Obsidian...")
    data = await state.get_data()
    task = _load_task(data)
    try:
        vault.add_task(task)
        fname = task.file_path.replace("\\", "/").split("/")[-1] if task.file_path else "?"
        await query.message.edit_text(
            f"✅ *Задача создана!*\n\n{task.format_preview()}\n\n📁 `{fname}`",
            reply_markup=None, parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("Vault write failed: %s", e)
        await query.message.edit_text(
            f"⚠️ Ошибка записи в Obsidian:\n`{e}`",
            reply_markup=kb_task_confirm(task), parse_mode="Markdown",
        )
        return
    await state.clear()


@task_router.callback_query(F.data == CB_TASK_CANCEL, TaskStates.creating)
async def on_task_cancel(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await query.answer("Отменено")
    await query.message.edit_text("❌ Создание задачи отменено.", reply_markup=None)


@task_router.callback_query(F.data == CB_TASK_BACK)
async def on_task_back(query: CallbackQuery, state: FSMContext, vault=None) -> None:
    await query.answer()
    current = await state.get_state()

    creating_states = {
        TaskStates.editing_title, TaskStates.editing_tags,
        TaskStates.editing_date_custom, TaskStates.editing_start_custom,
        TaskStates.editing_sched_custom, TaskStates.editing_time_slot,
        TaskStates.editing_recurrence_custom, TaskStates.editing_people_custom,
        # also from sub-menus while in creating state (no state change needed)
    }
    if current in creating_states or current == TaskStates.creating:
        await _back_to_preview(query, state)
    elif current in (TaskStates.editing_task, TaskStates.editing_task_title,
                     TaskStates.editing_task_tags) and vault is not None:
        await state.set_state(TaskStates.viewing_list)
        await _refresh_list_message(query, state, vault)
    else:
        # Generic fallback: try to return to preview
        data = await state.get_data()
        if _TASK_KEY in data:
            await _back_to_preview(query, state)


# ── Edit field (creating flow) ─────────────────────────────────


@task_router.callback_query(F.data.startswith(CB_TASK_EDIT), TaskStates.creating)
async def on_task_edit_field(query: CallbackQuery, state: FSMContext, vault=None) -> None:
    await query.answer()
    field_key = query.data[len(CB_TASK_EDIT):]
    data = await state.get_data()
    task = _load_task(data)

    # ── Inline enum pickers ───────────────────────────────────
    if field_key == "priority":
        await query.message.edit_text(
            "🏷 Выберите *приоритет*:", reply_markup=kb_priority_select(), parse_mode="Markdown",
        )
    elif field_key == "recurrence":
        await query.message.edit_text(
            "🔁 Выберите *правило повтора*:", reply_markup=kb_recurrence_select(), parse_mode="Markdown",
        )
    elif field_key == "date":
        await query.message.edit_text(
            "📅 Выберите *срок выполнения* (due):",
            reply_markup=kb_date_select(field="date"), parse_mode="Markdown",
        )
    elif field_key == "start_date":
        await query.message.edit_text(
            "🛫 Выберите *дату начала*:",
            reply_markup=kb_date_select(field="start_date"), parse_mode="Markdown",
        )
    elif field_key == "scheduled_date":
        await query.message.edit_text(
            "⏳ Выберите *дату планирования*:",
            reply_markup=kb_date_select(field="scheduled_date"), parse_mode="Markdown",
        )
    elif field_key == "people":
        all_names = vault.all_people_names() if vault else []
        await query.message.edit_text(
            "👤 Выберите *людей* (нажмите для toggle):",
            reply_markup=kb_people_select(all_names, task.people),
            parse_mode="Markdown",
        )
    # ── Custom date inputs ────────────────────────────────────
    elif field_key == "date_custom":
        await state.set_state(TaskStates.editing_date_custom)
        await query.message.edit_text(
            "📅 Введите *срок* (ГГГГ-ММ-ДД):", reply_markup=kb_text_prompt(), parse_mode="Markdown",
        )
    elif field_key == "start_date_custom":
        await state.set_state(TaskStates.editing_start_custom)
        await query.message.edit_text(
            "🛫 Введите *дату начала* (ГГГГ-ММ-ДД):", reply_markup=kb_text_prompt(), parse_mode="Markdown",
        )
    elif field_key == "scheduled_date_custom":
        await state.set_state(TaskStates.editing_sched_custom)
        await query.message.edit_text(
            "⏳ Введите *дату планирования* (ГГГГ-ММ-ДД):", reply_markup=kb_text_prompt(), parse_mode="Markdown",
        )
    # ── Free-text inputs ──────────────────────────────────────
    elif field_key == "title":
        await state.set_state(TaskStates.editing_title)
        await query.message.edit_text(
            "📌 Введите *название задачи*:", reply_markup=kb_text_prompt(), parse_mode="Markdown",
        )
    elif field_key == "tags":
        await state.set_state(TaskStates.editing_tags)
        await query.message.edit_text(
            "🔖 Введите *теги* через запятую _(без #, например: дом работа встреча)_:",
            reply_markup=kb_text_prompt(), parse_mode="Markdown",
        )
    elif field_key == "time_slot":
        await state.set_state(TaskStates.editing_time_slot)
        await query.message.edit_text(
            "🕐 Введите *временной слот* (ЧЧ:ММ-ЧЧ:ММ)\n_Например: 10:00-11:30_\n\n"
            "Или отправьте `-` чтобы убрать:",
            reply_markup=kb_text_prompt(), parse_mode="Markdown",
        )
    elif field_key == "recurrence_custom":
        await state.set_state(TaskStates.editing_recurrence_custom)
        await query.message.edit_text(
            "🔁 Введите *правило повтора* по-английски:\n"
            "_Например: every day / every monday / every mon,wed,fri_",
            reply_markup=kb_text_prompt(), parse_mode="Markdown",
        )
    elif field_key == "people_custom":
        await state.set_state(TaskStates.editing_people_custom)
        await query.message.edit_text(
            "👤 Введите *имена через запятую*:",
            reply_markup=kb_text_prompt(), parse_mode="Markdown",
        )


# ── Set value from inline button (creating flow) ───────────────


@task_router.callback_query(F.data.startswith(CB_TASK_SET), TaskStates.creating)
async def on_task_set_value(query: CallbackQuery, state: FSMContext, vault=None) -> None:
    await query.answer()
    payload = query.data[len(CB_TASK_SET):]
    sep = payload.index(":")
    field_key, value = payload[:sep], payload[sep + 1:]

    data = await state.get_data()
    task = _load_task(data)

    # Special: people toggle (add/remove)
    if field_key == "people_toggle":
        people = list(task.people)
        if value in people:
            people.remove(value)
        else:
            people.append(value)
        task.people = people
        # Stay on people picker, update keyboard
        await state.update_data(_save_task(task))
        all_names = vault.all_people_names() if vault else []
        await query.message.edit_text(
            "👤 Выберите *людей* (нажмите для toggle):",
            reply_markup=kb_people_select(all_names, task.people),
            parse_mode="Markdown",
        )
        return

    # Special: people_clear
    if field_key == "people_clear":
        task.people = []
        await state.update_data(_save_task(task))
        all_names = vault.all_people_names() if vault else []
        await query.message.edit_text(
            "👤 Выберите *людей*:",
            reply_markup=kb_people_select(all_names, task.people),
            parse_mode="Markdown",
        )
        return

    # Generic: set field value
    setattr(task, field_key, value)
    await state.update_data(_save_task(task))
    await state.set_state(TaskStates.creating)
    await query.message.edit_text(
        format_task_preview(task),
        reply_markup=kb_task_confirm(task),
        parse_mode="Markdown",
    )


# ── Free-text inputs (creating flow) ──────────────────────────


@task_router.message(TaskStates.editing_title)
async def on_title_input(message: Message, state: FSMContext, bot: Bot) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("⚠️ Название не может быть пустым.")
        return
    await _update_preview_from_text(message, state, bot, "title", title)


@task_router.message(TaskStates.editing_tags)
async def on_tags_input(message: Message, state: FSMContext, bot: Bot) -> None:
    raw = (message.text or "").strip()
    tags = [t.lstrip("#").strip() for t in raw.replace(",", " ").split() if t.strip()]
    await _update_preview_from_text(message, state, bot, "tags", tags)


@task_router.message(TaskStates.editing_date_custom)
async def on_date_input(message: Message, state: FSMContext, bot: Bot) -> None:
    await _parse_date_input(message, state, bot, "date")


@task_router.message(TaskStates.editing_start_custom)
async def on_start_date_input(message: Message, state: FSMContext, bot: Bot) -> None:
    await _parse_date_input(message, state, bot, "start_date")


@task_router.message(TaskStates.editing_sched_custom)
async def on_sched_date_input(message: Message, state: FSMContext, bot: Bot) -> None:
    await _parse_date_input(message, state, bot, "scheduled_date")


async def _parse_date_input(
    message: Message, state: FSMContext, bot: Bot, field: str
) -> None:
    text = (message.text or "").strip()
    try:
        d = date.fromisoformat(text)
    except ValueError:
        await message.answer("⚠️ Формат даты: `2026-03-25` (ГГГГ-ММ-ДД)", parse_mode="Markdown")
        return
    await _update_preview_from_text(message, state, bot, field, d.isoformat())


@task_router.message(TaskStates.editing_time_slot)
async def on_time_slot_input(message: Message, state: FSMContext, bot: Bot) -> None:
    text = (message.text or "").strip()
    value = "" if text == "-" else text
    await _update_preview_from_text(message, state, bot, "time_slot", value)


@task_router.message(TaskStates.editing_recurrence_custom)
async def on_recurrence_input(message: Message, state: FSMContext, bot: Bot) -> None:
    value = (message.text or "").strip()
    await _update_preview_from_text(message, state, bot, "recurrence", value)


@task_router.message(TaskStates.editing_people_custom)
async def on_people_input(message: Message, state: FSMContext, bot: Bot, vault=None) -> None:
    raw = (message.text or "").strip()
    names = [n.strip() for n in raw.replace(",", " ").split() if n.strip()]
    # Resolve canonical names via registry
    resolved = vault.resolve_people(names) if vault else names
    await _update_preview_from_text(message, state, bot, "people", resolved)


# ── Task List callbacks ────────────────────────────────────────


@task_router.callback_query(F.data.startswith(CB_LIST_NAV), TaskStates.viewing_list)
async def on_list_nav(query: CallbackQuery, state: FSMContext, vault) -> None:
    await query.answer()
    payload = query.data[len(CB_LIST_NAV):]
    data = await state.get_data()
    day_str = data.get(_DAY_KEY, date.today().isoformat())
    page = data.get(_PAGE_KEY, 0)

    if payload.startswith("date:"):
        day_str = payload[5:]
        page = 0
    elif payload.startswith("page:"):
        page = int(payload[5:])

    day = date.fromisoformat(day_str)
    tasks = vault.read_tasks(day, include_done=True)
    await state.update_data({**_save_tasks(tasks), _DAY_KEY: day_str, _PAGE_KEY: page})
    await query.message.edit_text(
        format_task_list(tasks, day, page=page),
        reply_markup=kb_task_list(tasks, day, page=page),
        parse_mode="Markdown",
    )


@task_router.callback_query(F.data.startswith(CB_LIST_DONE), TaskStates.viewing_list)
async def on_list_done(query: CallbackQuery, state: FSMContext, vault) -> None:
    await query.answer("✅ Отмечено как выполнено")
    idx = int(query.data[len(CB_LIST_DONE):])
    data = await state.get_data()
    tasks = _load_tasks(data)
    if 0 <= idx < len(tasks):
        vault.mark_done(tasks[idx])
    await _refresh_list_message(query, state, vault)


@task_router.callback_query(F.data.startswith(CB_LIST_DELETE), TaskStates.viewing_list)
async def on_list_delete(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    idx = int(query.data[len(CB_LIST_DELETE):])
    data = await state.get_data()
    tasks = _load_tasks(data)
    if 0 <= idx < len(tasks):
        task = tasks[idx]
        await state.set_state(TaskStates.deleting_confirm)
        await state.update_data({_EDIT_IDX_KEY: idx})
        await query.message.edit_text(
            f"🗑 *Удалить задачу?*\n\n{task.format_preview()}",
            reply_markup=kb_delete_confirm(idx), parse_mode="Markdown",
        )


@task_router.callback_query(
    F.data.startswith("tl:del_confirm:"), TaskStates.deleting_confirm
)
async def on_delete_confirmed(query: CallbackQuery, state: FSMContext, vault) -> None:
    await query.answer("🗑 Удалено")
    idx = int(query.data[len("tl:del_confirm:"):])
    data = await state.get_data()
    tasks = _load_tasks(data)
    if 0 <= idx < len(tasks):
        vault.delete_task(tasks[idx])
    await state.set_state(TaskStates.viewing_list)
    await _refresh_list_message(query, state, vault)


@task_router.callback_query(F.data.startswith(CB_LIST_EDIT), TaskStates.viewing_list)
async def on_list_edit(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    idx = int(query.data[len(CB_LIST_EDIT):])
    data = await state.get_data()
    tasks = _load_tasks(data)
    if 0 <= idx < len(tasks):
        task = tasks[idx]
        await state.set_state(TaskStates.editing_task)
        await state.update_data({_EDIT_IDX_KEY: idx, **_save_task(task)})
        await query.message.edit_text(
            f"✏️ *Редактирование задачи:*\n\n{task.format_preview()}",
            reply_markup=kb_task_edit(task, idx), parse_mode="Markdown",
        )


# ── Task edit from list ────────────────────────────────────────


@task_router.callback_query(F.data.startswith(CB_EDIT_FIELD), TaskStates.editing_task)
async def on_edit_task_field(query: CallbackQuery, state: FSMContext, vault=None) -> None:
    await query.answer()
    payload = query.data[len(CB_EDIT_FIELD):]
    sep = payload.index(":")
    field_key, idx = payload[:sep], int(payload[sep + 1:])
    data = await state.get_data()
    task = _load_task(data)

    if field_key == "priority":
        await query.message.edit_text(
            "🏷 Выберите *приоритет*:", reply_markup=kb_priority_select(cb_prefix=CB_EDIT_SET),
            parse_mode="Markdown",
        )
    elif field_key == "date":
        await query.message.edit_text(
            "📅 Выберите *срок*:", reply_markup=kb_date_select(field="date", cb_prefix=CB_EDIT_SET),
            parse_mode="Markdown",
        )
    elif field_key == "recurrence":
        await query.message.edit_text(
            "🔁 Выберите *повтор*:", reply_markup=kb_recurrence_select(cb_prefix=CB_EDIT_SET),
            parse_mode="Markdown",
        )
    elif field_key == "people":
        all_names = vault.all_people_names() if vault else []
        await query.message.edit_text(
            "👤 Выберите *людей*:",
            reply_markup=kb_people_select(all_names, task.people, cb_prefix=CB_EDIT_SET),
            parse_mode="Markdown",
        )
    elif field_key == "title":
        await state.set_state(TaskStates.editing_task_title)
        await query.message.edit_text(
            "📌 Введите *новое название*:", reply_markup=kb_text_prompt(CB_TASK_BACK), parse_mode="Markdown",
        )
    elif field_key == "tags":
        await state.set_state(TaskStates.editing_task_tags)
        await query.message.edit_text(
            "🔖 Введите *теги* через запятую:", reply_markup=kb_text_prompt(CB_TASK_BACK), parse_mode="Markdown",
        )


@task_router.callback_query(F.data.startswith(CB_EDIT_SET), TaskStates.editing_task)
async def on_edit_task_set(query: CallbackQuery, state: FSMContext, vault=None) -> None:
    await query.answer()
    payload = query.data[len(CB_EDIT_SET):]
    sep = payload.index(":")
    field_key, value = payload[:sep], payload[sep + 1:]
    data = await state.get_data()
    task = _load_task(data)
    idx = data.get(_EDIT_IDX_KEY, 0)

    if field_key == "people_toggle":
        people = list(task.people)
        if value in people:
            people.remove(value)
        else:
            people.append(value)
        task.people = people
        await state.update_data(_save_task(task))
        all_names = vault.all_people_names() if vault else []
        await query.message.edit_text(
            "👤 Выберите *людей*:",
            reply_markup=kb_people_select(all_names, task.people, cb_prefix=CB_EDIT_SET),
            parse_mode="Markdown",
        )
        return

    setattr(task, field_key, value)
    await state.update_data(_save_task(task))
    await state.set_state(TaskStates.editing_task)
    await query.message.edit_text(
        f"✏️ *Редактирование задачи:*\n\n{task.format_preview()}",
        reply_markup=kb_task_edit(task, idx), parse_mode="Markdown",
    )


@task_router.callback_query(F.data.startswith(CB_EDIT_CONFIRM), TaskStates.editing_task)
async def on_edit_task_confirm(query: CallbackQuery, state: FSMContext, vault) -> None:
    await query.answer("💾 Сохраняю...")
    idx = int(query.data[len(CB_EDIT_CONFIRM) + 1:])
    data = await state.get_data()
    tasks = _load_tasks(data)
    new_task = _load_task(data)
    if 0 <= idx < len(tasks):
        vault.update_task(tasks[idx], new_task)
    await state.set_state(TaskStates.viewing_list)
    await _refresh_list_message(query, state, vault)


@task_router.callback_query(F.data == CB_EDIT_CANCEL, TaskStates.editing_task)
async def on_edit_task_cancel(query: CallbackQuery, state: FSMContext, vault) -> None:
    await query.answer("Отменено")
    await state.set_state(TaskStates.viewing_list)
    await _refresh_list_message(query, state, vault)


@task_router.message(TaskStates.editing_task_title)
async def on_edit_task_title(message: Message, state: FSMContext, bot: Bot) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("⚠️ Название не может быть пустым.")
        return
    data = await state.get_data()
    task = _load_task(data)
    idx = data.get(_EDIT_IDX_KEY, 0)
    task.title = title
    await state.update_data(_save_task(task))
    await state.set_state(TaskStates.editing_task)
    await message.delete()
    msg_id = data.get(_MSG_KEY)
    if msg_id:
        await bot.edit_message_text(
            chat_id=message.chat.id, message_id=msg_id,
            text=f"✏️ *Редактирование задачи:*\n\n{task.format_preview()}",
            reply_markup=kb_task_edit(task, idx), parse_mode="Markdown",
        )


@task_router.message(TaskStates.editing_task_tags)
async def on_edit_task_tags(message: Message, state: FSMContext, bot: Bot) -> None:
    raw = (message.text or "").strip()
    tags = [t.lstrip("#").strip() for t in raw.replace(",", " ").split() if t.strip()]
    data = await state.get_data()
    task = _load_task(data)
    idx = data.get(_EDIT_IDX_KEY, 0)
    task.tags = tags
    await state.update_data(_save_task(task))
    await state.set_state(TaskStates.editing_task)
    await message.delete()
    msg_id = data.get(_MSG_KEY)
    if msg_id:
        await bot.edit_message_text(
            chat_id=message.chat.id, message_id=msg_id,
            text=f"✏️ *Редактирование задачи:*\n\n{task.format_preview()}",
            reply_markup=kb_task_edit(task, idx), parse_mode="Markdown",
        )
