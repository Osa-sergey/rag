"""Confirmation UI with inline keyboards for Telegram bot.

Flow:
  1. LLM extracts transaction data → build PendingTransaction
  2. Bot sends confirmation message with inline keyboard (edit_text for all updates)
  3. User: ✅ Confirm → post to Firefly III, show success in same message
       or: ✏️ Edit field → show field editor (same message)
           - Enum fields (account, category, date): show option buttons
           - Text fields (amount, description): ForceReply, then update original
  4. Cancel → clear, show cancelled in same message
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

logger = logging.getLogger(__name__)

# ── Data model ────────────────────────────────────────────────


@dataclass
class PendingTransaction:
    """Transaction data awaiting user confirmation."""

    tx_type: str  # "expense" | "transfer" | "deposit"
    amount: float
    currency: str
    description: str
    date: str  # YYYY-MM-DD
    # expense / deposit
    source_account: str = ""
    destination_account: str = ""
    category: str = ""
    revenue_account: str = ""
    # raw source text for notes
    raw_text: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, s: str) -> "PendingTransaction":
        return cls(**json.loads(s))

    def format_preview(self) -> str:
        """Build a human-readable preview string for the confirmation message."""
        type_labels = {
            "expense": "💸 Трата",
            "transfer": "💳 Перевод",
            "deposit": "💰 Доход",
        }
        label = type_labels.get(self.tx_type, self.tx_type)
        lines = [f"*{label} — подтвердите данные:*\n"]

        lines.append(f"💵 Сумма: *{self.amount:,.2f} {self.currency}*")
        lines.append(f"📝 Описание: _{self.description}_")
        lines.append(f"📅 Дата: *{self.date}*")

        if self.tx_type == "expense":
            lines.append(f"🏦 Счёт списания: *{self.source_account or '—'}*")
            lines.append(f"📂 Категория: *{self.category or '—'}*")
        elif self.tx_type == "transfer":
            lines.append(f"🏦 Откуда: *{self.source_account or '—'}*")
            lines.append(f"🏦 Куда: *{self.destination_account or '—'}*")
        elif self.tx_type == "deposit":
            lines.append(f"🏦 Счёт зачисления: *{self.destination_account or '—'}*")
            lines.append(f"💼 Источник дохода: *{self.revenue_account or '—'}*")

        return "\n".join(lines)


# ── Callback data helpers ─────────────────────────────────────
# We use compact prefixes to stay within Telegram's 64-byte callback_data limit.
# Format: "prefix:value"

CB_CONFIRM = "fx:confirm"
CB_CANCEL = "fx:cancel"
CB_EDIT = "fx:edit:"       # fx:edit:amount  fx:edit:date  etc.
CB_SET = "fx:set:"         # fx:set:account:Наличка
CB_BACK = "fx:back"

# Quick-date options shown as buttons
_DATE_SHORTCUTS = [
    ("Сегодня", 0),
    ("Вчера", 1),
    ("Позавчера", 2),
    ("3 дня назад", 3),
    ("Неделю назад", 7),
]


# ── Keyboard builders ─────────────────────────────────────────


def kb_confirm(tx: PendingTransaction) -> InlineKeyboardMarkup:
    """Main confirmation keyboard: Confirm + per-field edit buttons + Cancel."""

    def edit(label: str, field_key: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=f"✏️ {label}",
            callback_data=f"{CB_EDIT}{field_key}",
        )

    rows: list[list[InlineKeyboardButton]] = []

    # Field edit buttons (2 per row)
    field_buttons: list[InlineKeyboardButton] = [
        edit("Сумму", "amount"),
        edit("Описание", "description"),
        edit("Дату", "date"),
    ]
    if tx.tx_type == "expense":
        field_buttons += [edit("Счёт", "source_account"), edit("Категорию", "category")]
    elif tx.tx_type == "transfer":
        field_buttons += [edit("Откуда", "source_account"), edit("Куда", "destination_account")]
    elif tx.tx_type == "deposit":
        field_buttons += [edit("Счёт", "destination_account"), edit("Источник дохода", "revenue_account")]

    # Split into pairs
    for i in range(0, len(field_buttons), 2):
        rows.append(field_buttons[i : i + 2])

    # Bottom row: confirm / cancel
    rows.append([
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=CB_CONFIRM),
        InlineKeyboardButton(text="❌ Отмена", callback_data=CB_CANCEL),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_account_select(
    accounts: list[str],
    field_key: str,
) -> InlineKeyboardMarkup:
    """Keyboard for selecting an account from a list."""
    rows: list[list[InlineKeyboardButton]] = []
    for name in accounts:
        # Truncate long names for display
        display = name if len(name) <= 30 else name[:28] + "…"
        cb = f"{CB_SET}{field_key}:{name}"
        # Telegram limit is 64 bytes for callback_data — trim if needed
        if len(cb.encode()) > 64:
            cb = cb.encode()[:64].decode("utf-8", errors="ignore")
        rows.append([InlineKeyboardButton(text=display, callback_data=cb)])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=CB_BACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_category_select(categories: list[str]) -> InlineKeyboardMarkup:
    """Keyboard for selecting a category."""
    rows: list[list[InlineKeyboardButton]] = []
    # 2 per row
    buttons = [
        InlineKeyboardButton(
            text=cat,
            callback_data=f"{CB_SET}category:{cat}",
        )
        for cat in categories
    ]
    for i in range(0, len(buttons), 2):
        rows.append(buttons[i : i + 2])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=CB_BACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_date_select() -> InlineKeyboardMarkup:
    """Keyboard for quick date selection + custom date prompt."""
    today = date.today()
    rows: list[list[InlineKeyboardButton]] = []
    for label, delta in _DATE_SHORTCUTS:
        d = today - timedelta(days=delta)
        rows.append([
            InlineKeyboardButton(
                text=f"{label} ({d.isoformat()})",
                callback_data=f"{CB_SET}date:{d.isoformat()}",
            )
        ])
    rows.append([
        InlineKeyboardButton(
            text="✏️ Ввести вручную (ГГГГ-ММ-ДД)",
            callback_data=f"{CB_EDIT}date_custom",
        )
    ])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=CB_BACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_text_input_prompt(field_key: str, field_label: str) -> InlineKeyboardMarkup:
    """Shown while waiting for free-text input from user."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад (без изменений)", callback_data=CB_BACK)
    ]])
