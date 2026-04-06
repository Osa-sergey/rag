"""Aiogram 3.x Telegram bot handlers for voice expense tracking.

Pipeline: voice message → download OGG → ffmpeg → GigaAM → classify → extract → store → reply
"""
from __future__ import annotations

import logging
import os
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

logger = logging.getLogger(__name__)
router = Router()


# ── Helpers ───────────────────────────────────────────────────


def _parse_period(text: str | None) -> tuple[date | None, date | None]:
    """Parse period from command arguments (today/week/month/YYYY-MM-DD)."""
    if not text or not text.strip():
        return None, None

    arg = text.strip().lower()
    today = date.today()

    if arg == "today" or arg == "сегодня":
        return today, today
    elif arg == "week" or arg == "неделя":
        return today - timedelta(days=7), today
    elif arg == "month" or arg == "месяц":
        return today.replace(day=1), today
    else:
        # Try to parse as date
        try:
            d = datetime.strptime(arg, "%Y-%m-%d").date()
            return d, d
        except ValueError:
            return None, None


def _format_money(amount: float, currency: str = "RUB") -> str:
    """Format money amount."""
    if currency == "RUB":
        return f"{amount:,.2f} ₽"
    return f"{amount:,.2f} {currency}"


# ── Handlers ──────────────────────────────────────────────────


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    await message.answer(
        "🎙 **Голосовой учёт расходов**\n\n"
        "Отправьте мне голосовое сообщение с информацией о трате или переводе, "
        "и я автоматически распознаю и сохраню данные.\n\n"
        "**Примеры:**\n"
        '• _"Потратил 500 рублей на обед в кафе"_\n'
        '• _"Перевёл Саше 2000 рублей за билеты"_\n\n'
        "**Команды:**\n"
        "/expenses [период] — список трат\n"
        "/expenses\\_by\\_category [категория] — фильтр по категории\n"
        "/transfers [период] — список переводов\n"
        "/summary [период] — сводка расходов\n"
        "/categories — список категорий\n\n"
        "_Период: today/сегодня, week/неделя, month/месяц, YYYY-MM-DD_",
        parse_mode="Markdown",
    )


@router.message(Command("categories"))
async def cmd_categories(message: Message, category_classifier) -> None:
    """Show available expense categories."""
    cats = category_classifier._categories
    lines = ["📋 **Категории расходов:**\n"]
    for i, cat in enumerate(cats, 1):
        examples = ", ".join(cat.examples[:3])
        lines.append(f"{i}. **{cat.display_name}** ({cat.name}) — _{examples}_")

    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("expenses"))
async def cmd_expenses(message: Message, storage) -> None:
    """Show expenses list."""
    args = message.text.split(maxsplit=1)[1] if " " in message.text else None
    start, end = _parse_period(args)
    user_id = message.from_user.id

    rows = await storage.get_expenses(user_id, start, end)
    if not rows:
        await message.answer("📭 Нет трат за указанный период.")
        return

    lines = ["💸 **Ваши траты:**\n"]
    total = 0.0
    for r in rows[:20]:  # Limit to 20
        lines.append(
            f"• {r['expense_date']} | {_format_money(float(r['amount']), r['currency'])} | "
            f"_{r['category']}_ — {r['description']}"
        )
        total += float(r["amount"])

    lines.append(f"\n**Итого:** {_format_money(total)}")
    if len(rows) > 20:
        lines.append(f"_...и ещё {len(rows) - 20} записей_")

    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("expenses_by_category"))
async def cmd_expenses_by_category(message: Message, storage) -> None:
    """Show expenses filtered by category."""
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Укажите категорию: /expenses\\_by\\_category еда [период]")
        return

    category = parts[1]
    period_text = parts[2] if len(parts) > 2 else None
    start, end = _parse_period(period_text)
    user_id = message.from_user.id

    rows = await storage.get_expenses_by_category(user_id, category, start, end)
    if not rows:
        await message.answer(f"📭 Нет трат в категории «{category}».")
        return

    lines = [f"💸 **Траты — {category}:**\n"]
    total = 0.0
    for r in rows[:20]:
        lines.append(
            f"• {r['expense_date']} | {_format_money(float(r['amount']), r['currency'])} — {r['description']}"
        )
        total += float(r["amount"])

    lines.append(f"\n**Итого:** {_format_money(total)}")
    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("transfers"))
async def cmd_transfers(message: Message, storage) -> None:
    """Show transfers list."""
    args = message.text.split(maxsplit=1)[1] if " " in message.text else None
    start, end = _parse_period(args)
    user_id = message.from_user.id

    rows = await storage.get_transfers(user_id, start, end)
    if not rows:
        await message.answer("📭 Нет переводов за указанный период.")
        return

    lines = ["💳 **Ваши переводы:**\n"]
    for r in rows[:20]:
        lines.append(
            f"• {r['transfer_date']} | {_format_money(float(r['amount']), r['currency'])} | "
            f"{r['from_person']} → {r['to_person']}"
        )

    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("summary"))
async def cmd_summary(message: Message, storage) -> None:
    """Show spending summary."""
    args = message.text.split(maxsplit=1)[1] if " " in message.text else None
    start, end = _parse_period(args)
    user_id = message.from_user.id

    summary = await storage.get_summary(user_id, start, end)

    if not summary["categories"]:
        await message.answer("📭 Нет данных для сводки.")
        return

    lines = ["📊 **Сводка расходов:**\n"]
    for cat in summary["categories"]:
        pct = (cat["total"] / summary["total"] * 100) if summary["total"] > 0 else 0
        lines.append(
            f"• **{cat['category']}**: {_format_money(cat['total'], cat['currency'])} "
            f"({cat['count']} шт., {pct:.0f}%)"
        )

    lines.append(f"\n🏷 **Всего:** {_format_money(summary['total'])}")
    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(F.voice)
async def handle_voice(
    message: Message,
    bot: Bot,
    transcriber,
    intent_classifier,
    category_classifier,
    extractor,
    storage,
) -> None:
    """Process voice message: transcribe → classify → extract → store."""
    user_id = message.from_user.id
    await message.answer("🎧 Обрабатываю голосовое сообщение...")

    # 1. Download voice file
    voice = message.voice
    file = await bot.get_file(voice.file_id)

    with tempfile.TemporaryDirectory() as tmp_dir:
        ogg_path = os.path.join(tmp_dir, f"voice_{voice.file_id}.ogg")
        await bot.download_file(file.file_path, ogg_path)
        logger.info("Downloaded voice message → %s", ogg_path)

        # 2. Transcribe
        try:
            text = transcriber.transcribe(ogg_path)
        except Exception as e:
            logger.error("Transcription failed: %s", e)
            await message.answer(f"❌ Ошибка распознавания: {e}")
            return

    if not text.strip():
        await message.answer("🤷 Не удалось распознать речь. Попробуйте ещё раз.")
        return

    await message.answer(f"📝 Распознано: _{text}_", parse_mode="Markdown")

    # 3. Classify intent
    result = intent_classifier.classify(text)
    logger.info("Intent: %s (%.2f), scores: %s", result.intent, result.confidence, result.scores)

    if result.intent == "unknown":
        await message.answer(
            "🤔 Не удалось определить тип записи. "
            "Скажите что-то вроде «потратил 500 на обед» или «перевёл Саше 1000»."
        )
        return

    # 4. Extract structured data and save
    try:
        if result.intent == "expense":
            expense = await extractor.extract_expense(text)

            # Classify category via embeddings
            cat = category_classifier.classify(expense.description or text)
            expense_category = cat.display_name

            expense_date = date.fromisoformat(expense.date)
            expense_id = await storage.add_expense(
                user_id=user_id,
                amount=expense.amount,
                currency=expense.currency,
                category=expense_category,
                description=expense.description,
                expense_date=expense_date,
                raw_text=text,
            )

            await message.answer(
                f"✅ **Трата #{expense_id} сохранена:**\n"
                f"💰 Сумма: {_format_money(expense.amount, expense.currency)}\n"
                f"📁 Категория: {expense_category}\n"
                f"📝 Описание: {expense.description}\n"
                f"📅 Дата: {expense.date}",
                parse_mode="Markdown",
            )

        elif result.intent == "transfer":
            transfer = await extractor.extract_transfer(text)
            transfer_date = date.fromisoformat(transfer.date)
            transfer_id = await storage.add_transfer(
                user_id=user_id,
                amount=transfer.amount,
                currency=transfer.currency,
                from_person=transfer.from_person,
                to_person=transfer.to_person,
                transfer_date=transfer_date,
                description=transfer.description,
                raw_text=text,
            )

            await message.answer(
                f"✅ **Перевод #{transfer_id} сохранён:**\n"
                f"💰 Сумма: {_format_money(transfer.amount, transfer.currency)}\n"
                f"👤 От: {transfer.from_person}\n"
                f"👤 Кому: {transfer.to_person}\n"
                f"📅 Дата: {transfer.date}",
                parse_mode="Markdown",
            )

    except Exception as e:
        logger.error("Extraction/storage failed: %s", e, exc_info=True)
        await message.answer(
            f"⚠️ Распознал текст, но не смог извлечь данные:\n_{text}_\n\nОшибка: {e}",
            parse_mode="Markdown",
        )
