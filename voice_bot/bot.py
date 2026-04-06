"""Aiogram 3.x bot handlers with FSM-based confirmation UI.

Pipeline:
  voice → STT → intent classify → LLM extract → confirmation message
  (inline keyboard edit loop, same message) → confirm → Firefly III API / Obsidian
"""
from __future__ import annotations

import logging
import os
import tempfile
from datetime import date, datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from voice_bot.integrations.firefly_iii.ui import (
    CB_BACK,
    CB_CANCEL,
    CB_CONFIRM,
    CB_EDIT,
    CB_SET,
    PendingTransaction,
    kb_account_select,
    kb_category_select,
    kb_confirm,
    kb_date_select,
    kb_text_input_prompt,
)
from voice_bot.integrations.obsidian_tasks.handlers import (
    TaskStates,
    start_agenda_show,
    start_task_create,
    start_task_show,
    start_task_update,
    task_router,
)

logger = logging.getLogger(__name__)
router = Router()

# ── Intent → handler registry ──────────────────────────────────
# Maps (integration, action) to the async callable.
# Action naming: <verb>_<object> — create_transaction, create_task, etc.
# New integrations register their (integration, action) entries here.

_INTENT_HANDLERS: dict[tuple[str, str], object] = {
    # Firefly III — all financial intents share the same flow
    ("firefly_iii", "create_transaction"): "_firefly",  # sentinel, Firefly flow is inline
    # Obsidian Tasks
    ("obsidian_tasks", "create_task"):  start_task_create,
    ("obsidian_tasks", "show_tasks"):   start_task_show,
    ("obsidian_tasks", "update_task"):  start_task_update,
    ("obsidian_tasks", "show_agenda"):  start_agenda_show,
}


def _build_intent_map(intents_cfg: dict) -> dict[str, dict]:
    """Build {intent_name: {integration, action}} from Hydra config."""
    result = {}
    for intent in intents_cfg.get("intents", []):
        result[intent["name"]] = {
            "integration": intent.get("integration", ""),
            "action": intent.get("action", ""),
        }
    return result



# ── FSM States (Firefly flow) ──────────────────────────────────


class ConfirmStates(StatesGroup):
    awaiting_confirm   = State()
    editing_amount     = State()
    editing_description = State()
    editing_date_custom = State()


_TX_KEY  = "pending_tx"
_MSG_KEY = "confirm_msg_id"


# ── Helpers ────────────────────────────────────────────────────


async def _extract_pending(
    intent: str,
    text: str,
    firefly_extractor,
    date_parser,
    account_resolver,
) -> PendingTransaction:
    if intent == "expense":
        ext = await firefly_extractor.extract_expense(text)
        parsed_date = date_parser.parse(ext.date_raw or ext.date or "")
        resolved = account_resolver.resolve(ext.source_account or None)
        return PendingTransaction(
            tx_type="expense",
            amount=ext.amount,
            currency=ext.currency,
            description=ext.description,
            date=parsed_date.isoformat(),
            source_account=resolved.name if resolved else "",
            category=ext.category,
            raw_text=text,
        )
    elif intent == "transfer":
        ext = await firefly_extractor.extract_transfer(text)
        parsed_date = date_parser.parse(ext.date_raw or ext.date or "")
        src = account_resolver.resolve(ext.source_account)
        dst = account_resolver.resolve(ext.destination_account)
        return PendingTransaction(
            tx_type="transfer",
            amount=ext.amount,
            currency=ext.currency,
            description=ext.description or "",
            date=parsed_date.isoformat(),
            source_account=src.name if src else ext.source_account,
            destination_account=dst.name if dst else ext.destination_account,
            raw_text=text,
        )
    elif intent == "deposit":
        ext = await firefly_extractor.extract_deposit(text)
        parsed_date = date_parser.parse(ext.date_raw or ext.date or "")
        dst = account_resolver.resolve(ext.destination_account or None)
        return PendingTransaction(
            tx_type="deposit",
            amount=ext.amount,
            currency=ext.currency,
            description=ext.description,
            date=parsed_date.isoformat(),
            destination_account=dst.name if dst else "",
            revenue_account=ext.revenue_account,
            raw_text=text,
        )
    raise ValueError(f"Unknown intent: {intent}")


async def _post_to_firefly(tx: PendingTransaction, firefly_client) -> str:
    if tx.tx_type == "expense":
        result = await firefly_client.create_withdrawal(
            amount=tx.amount,
            description=tx.description,
            source_name=tx.source_account,
            date=tx.date,
            category_name=tx.category,
            currency_code=tx.currency,
            notes=f"[voice] {tx.raw_text}",
        )
    elif tx.tx_type == "transfer":
        result = await firefly_client.create_transfer(
            amount=tx.amount,
            description=tx.description or f"Перевод {tx.source_account} → {tx.destination_account}",
            source_name=tx.source_account,
            destination_name=tx.destination_account,
            date=tx.date,
            currency_code=tx.currency,
            notes=f"[voice] {tx.raw_text}",
        )
    elif tx.tx_type == "deposit":
        result = await firefly_client.create_deposit(
            amount=tx.amount,
            description=tx.description,
            destination_name=tx.destination_account,
            date=tx.date,
            revenue_name=tx.revenue_account,
            currency_code=tx.currency,
            notes=f"[voice] {tx.raw_text}",
        )
    else:
        raise ValueError(f"Unknown tx_type: {tx.tx_type}")
    return str(result.get("data", {}).get("id", "?"))


def _success_text(tx: PendingTransaction, tx_id: str) -> str:
    emoji = {"expense": "💸", "transfer": "💳", "deposit": "💰"}.get(tx.tx_type, "✅")
    label = {"expense": "Трата", "transfer": "Перевод", "deposit": "Доход"}.get(tx.tx_type, tx.tx_type)
    lines = [f"✅ {emoji} *{label} записана в Firefly III* (#{tx_id})\n"]
    lines.append(f"💵 Сумма: *{tx.amount:,.2f} {tx.currency}*")
    lines.append(f"📝 {tx.description}")
    lines.append(f"📅 {tx.date}")
    if tx.tx_type == "expense":
        lines.append(f"🏦 {tx.source_account}  |  📂 {tx.category}")
    elif tx.tx_type == "transfer":
        lines.append(f"🏦 {tx.source_account} → {tx.destination_account}")
    elif tx.tx_type == "deposit":
        lines.append(f"🏦 {tx.destination_account}  |  💼 {tx.revenue_account}")
    return "\n".join(lines)


# ── Command Handlers ───────────────────────────────────────────


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "🎙 *Голосовой финансовый ассистент*\n\n"
        "Отправьте голосовое сообщение — я распознаю, покажу превью и внесу данные.\n\n"
        "*Финансы:*\n"
        "• _«Потратил 500 рублей на обед»_\n"
        "• _«Перевёл с сбера на копилку 10000»_\n"
        "• _«Получил зарплату 50000 на альфу»_\n\n"
        "*Задачи:*\n"
        "• _«Создай задачу купить продукты на завтра»_\n"
        "• _«Покажи мои задачи на сегодня»_\n\n"
        "*/accounts* — счета  |  */categories* — категории\n"
        "*/tasks* — задачи на сегодня  |  */help* — справка",
        parse_mode="Markdown",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 *Справка*\n\n"
        "*Финансы (Firefly III):*\n"
        "• 💸 Трата: «потратил 500 на обед»\n"
        "• 💳 Перевод: «перевёл 10000 с сбера на копилку»\n"
        "• 💰 Доход: «получил зарплату 50000»\n\n"
        "*Задачи (Obsidian):*\n"
        "• 📌 Создать: «создай задачу купить продукты завтра»\n"
        "• 📋 Показать: «покажи задачи на сегодня»\n\n"
        "*Даты:*\n"
        "• сегодня, вчера, позавчера, завтра\n"
        "• в четверг, на прошлой неделе в среду\n"
        "• 3 дня назад, неделю назад\n\n"
        "*Счета:* сбер / альфа / тинькофф / наличка / копилка",
        parse_mode="Markdown",
    )


@router.message(Command("accounts"))
async def cmd_accounts(message: Message, firefly_client) -> None:
    try:
        accounts = await firefly_client.get_accounts(account_type="asset")
        if not accounts:
            await message.answer("📭 Нет счетов.")
            return
        lines = ["🏦 *Ваши счета:*\n"]
        for acc in accounts:
            lines.append(f"• *{acc.name}* — {acc.current_balance or '?'} {acc.currency_code}")
        await message.answer("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")


@router.message(Command("categories"))
async def cmd_categories(message: Message, firefly_client) -> None:
    try:
        categories = await firefly_client.get_categories()
        if not categories:
            await message.answer("📭 Нет категорий.")
            return
        lines = ["📋 *Категории расходов:*\n"]
        for i, cat in enumerate(categories, 1):
            lines.append(f"{i}. {cat['name']}")
        await message.answer("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")


@router.message(Command("tasks"))
async def cmd_tasks(
    message: Message,
    state: FSMContext,
    task_extractor,
    date_parser,
    vault,
) -> None:
    """Show today's tasks."""
    await start_task_show(
        message=message,
        state=state,
        text="покажи задачи на сегодня",
        task_extractor=task_extractor,
        date_parser=date_parser,
        vault=vault,
    )


# ── Voice Handler ─────────────────────────────────────────────


@router.message(F.voice)
async def handle_voice(
    message: Message,
    bot: Bot,
    state: FSMContext,
    transcriber,
    intent_classifier,
    firefly_extractor,
    date_parser,
    account_resolver,
    firefly_client,
    task_extractor,
    vault,
) -> None:
    """Process voice → classify → route to Firefly or Obsidian handler."""
    await state.clear()

    status_msg = await message.answer("🎧 Распознаю речь...")

    # 1. Download + transcribe
    voice = message.voice
    file = await bot.get_file(voice.file_id)
    with tempfile.TemporaryDirectory() as tmp_dir:
        ogg_path = os.path.join(tmp_dir, f"voice_{voice.file_id}.ogg")
        await bot.download_file(file.file_path, ogg_path)
        try:
            text = transcriber.transcribe(ogg_path)
        except Exception as e:
            logger.error("STT failed: %s", e)
            await status_msg.edit_text(f"❌ Ошибка распознавания: {e}")
            return

    if not text.strip():
        await status_msg.edit_text("🤷 Не удалось распознать речь. Попробуйте ещё раз.")
        return

    await status_msg.edit_text(
        f"📝 *Распознано:*\n_{text}_\n\n⏳ Анализирую...",
        parse_mode="Markdown",
    )

    # 2. Classify intent
    result = intent_classifier.classify(text)
    logger.info("Intent: %s (%.2f)", result.intent, result.confidence)

    if result.intent == "unknown":
        await status_msg.edit_text(
            "🤔 Не удалось определить тип записи.\n\n"
            "Финансы: «потратил 500 на обед», «перевёл с сбера», «получил зарплату»\n"
            "Задачи: «создай задачу», «покажи задачи на сегодня»"
        )
        return

    # 3. Route by intent → integration (config-driven)
    #    Intent map is built lazily from dp["intents_cfg"] injected at startup.
    intents_cfg = kwargs.get("intents_cfg", {})
    intent_map = _build_intent_map(intents_cfg)
    intent_meta = intent_map.get(result.intent)

    if not intent_meta:
        await status_msg.edit_text(
            f"⚙️ Интент «{result.intent}» распознан, но обработчик не настроен."
        )
        return

    integration = intent_meta["integration"]
    action = intent_meta["action"]
    handler_key = (integration, action)
    handler_fn = _INTENT_HANDLERS.get(handler_key)

    if handler_fn == "_firefly":
        # Firefly III integration: expense / transfer / deposit
        try:
            tx = await _extract_pending(
                result.intent, text, firefly_extractor, date_parser, account_resolver
            )
        except Exception as e:
            logger.error("Firefly extraction failed: %s", e, exc_info=True)
            await status_msg.edit_text(f"⚠️ Ошибка извлечения данных: {e}")
            return

        await state.set_state(ConfirmStates.awaiting_confirm)
        await state.update_data({_TX_KEY: tx.to_json(), _MSG_KEY: status_msg.message_id})
        await status_msg.edit_text(
            tx.format_preview(), reply_markup=kb_confirm(tx), parse_mode="Markdown",
        )

    elif callable(handler_fn):
        # Generic async handler (obsidian_tasks, future integrations)
        handler_kwargs = dict(
            message=message, state=state, text=text,
            status_msg=status_msg,
        )
        if "task_extractor" in kwargs:
            handler_kwargs["task_extractor"] = task_extractor
        if "date_parser" in kwargs:
            handler_kwargs["date_parser"] = date_parser
        if "vault" in kwargs:
            handler_kwargs["vault"] = vault
        await handler_fn(**handler_kwargs)

    else:
        await status_msg.edit_text(
            f"⚙️ Интент «{result.intent}» ({integration}/{action}) распознан, "
            f"но обработчик не зарегистрирован в _INTENT_HANDLERS."
        )



# ── Firefly Confirmation Callbacks ────────────────────────────


@router.callback_query(F.data == CB_CONFIRM, ConfirmStates.awaiting_confirm)
async def on_confirm(query: CallbackQuery, state: FSMContext, firefly_client) -> None:
    await query.answer("Отправляю в Firefly III...")
    data = await state.get_data()
    tx = PendingTransaction.from_json(data[_TX_KEY])
    try:
        tx_id = await _post_to_firefly(tx, firefly_client)
        await query.message.edit_text(
            _success_text(tx, tx_id), reply_markup=None, parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("Firefly post failed: %s", e, exc_info=True)
        await query.message.edit_text(
            f"⚠️ Ошибка при сохранении:\n`{e}`",
            reply_markup=kb_confirm(tx),
            parse_mode="Markdown",
        )
        return
    await state.clear()


@router.callback_query(F.data == CB_CANCEL, ConfirmStates.awaiting_confirm)
async def on_cancel(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await query.answer("Отменено")
    await query.message.edit_text("❌ Запись отменена.", reply_markup=None)


@router.callback_query(F.data == CB_BACK)
async def on_back(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(ConfirmStates.awaiting_confirm)
    data = await state.get_data()
    tx_json = data.get(_TX_KEY)
    if not tx_json:
        await query.message.edit_text("⚠️ Сессия устарела.", reply_markup=None)
        return
    tx = PendingTransaction.from_json(tx_json)
    await query.message.edit_text(
        tx.format_preview(), reply_markup=kb_confirm(tx), parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith(CB_EDIT), ConfirmStates.awaiting_confirm)
async def on_edit_field(query: CallbackQuery, state: FSMContext, account_resolver, firefly_client) -> None:
    await query.answer()
    field_key = query.data[len(CB_EDIT):]

    data = await state.get_data()
    tx = PendingTransaction.from_json(data[_TX_KEY])

    if field_key in ("source_account", "destination_account"):
        label = "счёт списания" if field_key == "source_account" else "счёт зачисления"
        await query.message.edit_text(
            f"🏦 Выберите *{label}*:",
            reply_markup=kb_account_select(account_resolver.account_names, field_key),
            parse_mode="Markdown",
        )
        return

    if field_key == "revenue_account":
        try:
            rev = await firefly_client.get_accounts(account_type="revenue")
            names = [a.name for a in rev] if rev else []
        except Exception:
            names = []
        if not names:
            names = ["Зарплата", "Проценты", "Фриланс", "Другое"]
        await query.message.edit_text(
            "💼 Выберите *источник дохода*:",
            reply_markup=kb_account_select(names, "revenue_account"),
            parse_mode="Markdown",
        )
        return

    if field_key == "category":
        cats = ["Внешний вид", "Еда", "Медицина", "Обустройство",
                "Поездки", "Транспорт", "Хобби", "Другое"]
        await query.message.edit_text(
            "📂 Выберите *категорию*:",
            reply_markup=kb_category_select(cats),
            parse_mode="Markdown",
        )
        return

    if field_key == "date":
        await query.message.edit_text(
            "📅 Выберите *дату*:", reply_markup=kb_date_select(), parse_mode="Markdown",
        )
        return

    if field_key == "date_custom":
        from aiogram.fsm.state import State
        await state.set_state(ConfirmStates.editing_date_custom)
        await query.message.edit_text(
            "📅 Введите дату *ГГГГ-ММ-ДД*:",
            reply_markup=kb_text_input_prompt("date", "Дата"),
            parse_mode="Markdown",
        )
        return

    if field_key == "amount":
        await state.set_state(ConfirmStates.editing_amount)
    elif field_key == "description":
        await state.set_state(ConfirmStates.editing_description)

    labels = {"amount": "сумму", "description": "описание"}
    await query.message.edit_text(
        f"✏️ Введите *{labels.get(field_key, field_key)}*:",
        reply_markup=kb_text_input_prompt(field_key, field_key),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith(CB_SET))
async def on_set_value(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    payload = query.data[len(CB_SET):]
    sep = payload.index(":")
    field_key, value = payload[:sep], payload[sep + 1:]
    data = await state.get_data()
    tx_json = data.get(_TX_KEY)
    if not tx_json:
        await query.message.edit_text("⚠️ Сессия устарела.", reply_markup=None)
        return
    tx = PendingTransaction.from_json(tx_json)
    if field_key == "amount":
        try:
            value = float(value)
        except ValueError:
            await query.answer("⚠️ Неверный формат числа", show_alert=True)
            return
    setattr(tx, field_key, value)
    await state.update_data({_TX_KEY: tx.to_json()})
    await state.set_state(ConfirmStates.awaiting_confirm)
    await query.message.edit_text(
        tx.format_preview(), reply_markup=kb_confirm(tx), parse_mode="Markdown",
    )


# ── Free-text input for Firefly fields ────────────────────────


async def _apply_tx_field(message: Message, state: FSMContext, bot: Bot, field: str, value) -> None:
    data = await state.get_data()
    tx = PendingTransaction.from_json(data[_TX_KEY])
    setattr(tx, field, value)
    await state.update_data({_TX_KEY: tx.to_json()})
    await state.set_state(ConfirmStates.awaiting_confirm)
    await message.delete()
    msg_id = data.get(_MSG_KEY)
    if msg_id:
        await bot.edit_message_text(
            chat_id=message.chat.id, message_id=msg_id,
            text=tx.format_preview(), reply_markup=kb_confirm(tx), parse_mode="Markdown",
        )


@router.message(ConfirmStates.editing_amount)
async def on_edit_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    try:
        amount = float((message.text or "").replace(",", ".").replace(" ", ""))
    except ValueError:
        await message.answer("⚠️ Введите число, например: `1500`", parse_mode="Markdown")
        return
    await _apply_tx_field(message, state, bot, "amount", amount)


@router.message(ConfirmStates.editing_description)
async def on_edit_description(message: Message, state: FSMContext, bot: Bot) -> None:
    desc = (message.text or "").strip()
    if not desc:
        await message.answer("⚠️ Описание не может быть пустым.")
        return
    await _apply_tx_field(message, state, bot, "description", desc)


@router.message(ConfirmStates.editing_date_custom)
async def on_edit_date(message: Message, state: FSMContext, bot: Bot) -> None:
    try:
        d = date.fromisoformat((message.text or "").strip())
    except ValueError:
        await message.answer("⚠️ Формат: `2026-03-20`", parse_mode="Markdown")
        return
    await _apply_tx_field(message, state, bot, "date", d.isoformat())
