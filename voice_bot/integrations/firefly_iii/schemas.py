"""Pydantic configuration and data models for Firefly III integration."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ── Config ────────────────────────────────────────────────────


class AccountSynonymConfig(BaseModel):
    """Mapping of synonyms to canonical Firefly III account names.

    Example::

        synonyms:
          сбер: "Сбер расчетный счет"
          зарплатная: "Сбер расчетный счет"
          альфа: "Альфа расчетный счет"
          тинькофф: "Тинькофф расчетный счет"
          наличка: "Наличка"
    """

    synonyms: dict[str, str] = Field(default_factory=dict)


class FireflyConfig(BaseModel):
    """Firefly III connection and account settings."""

    base_url: str = "http://localhost:9090"
    token: str = ""
    default_source_account: str = "Сбер расчетный счет"
    account_synonyms: AccountSynonymConfig = Field(
        default_factory=AccountSynonymConfig
    )

    model_config = {"extra": "allow"}


# ── API Request / Response Models ─────────────────────────────


class TransactionSplit(BaseModel):
    """Single split in a Firefly III transaction."""

    type: str  # "withdrawal", "transfer", "deposit"
    date: str  # YYYY-MM-DD
    amount: str  # decimal as string
    description: str
    source_name: Optional[str] = None
    source_id: Optional[str] = None
    destination_name: Optional[str] = None
    destination_id: Optional[str] = None
    category_name: Optional[str] = None
    budget_name: Optional[str] = None
    currency_code: str = "RUB"
    notes: Optional[str] = None


class TransactionRequest(BaseModel):
    """Request body for POST /api/v1/transactions."""

    error_if_duplicate_hash: bool = False
    apply_rules: bool = True
    fire_webhooks: bool = True
    group_title: Optional[str] = None
    transactions: list[TransactionSplit]


class FireflyAccount(BaseModel):
    """Parsed account from Firefly III API response."""

    id: str
    name: str
    account_type: str  # "asset", "expense", "revenue", "liabilities"
    currency_code: str = "RUB"
    current_balance: Optional[str] = None


# ── Extracted data models (from LLM) ─────────────────────────


class ExtractedExpense(BaseModel):
    """Structured expense extracted from voice text for Firefly."""

    amount: float = Field(..., description="Сумма траты")
    currency: str = Field("RUB", description="Валюта")
    description: str = Field(..., description="Краткое описание покупки")
    category: str = Field("", description="Категория расхода")
    source_account: str = Field("", description="Счёт-источник (если упомянут)")
    date_raw: str = Field(
        "", description="Дата как произнесена (вчера, в четверг, и т.д.)"
    )
    date: str = Field("", description="Дата в формате YYYY-MM-DD")


class ExtractedTransfer(BaseModel):
    """Structured transfer extracted from voice text for Firefly."""

    amount: float = Field(..., description="Сумма перевода")
    currency: str = Field("RUB", description="Валюта")
    source_account: str = Field(..., description="Счёт-источник")
    destination_account: str = Field(..., description="Счёт-назначения")
    description: str = Field("", description="Описание перевода")
    date_raw: str = Field(
        "", description="Дата как произнесена (вчера, в четверг, и т.д.)"
    )
    date: str = Field("", description="Дата в формате YYYY-MM-DD")


class ExtractedDeposit(BaseModel):
    """Structured deposit (income) extracted from voice text for Firefly."""

    amount: float = Field(..., description="Сумма пополнения")
    currency: str = Field("RUB", description="Валюта")
    description: str = Field(..., description="Описание дохода")
    destination_account: str = Field("", description="Счёт-назначения")
    revenue_account: str = Field(
        "", description="Источник дохода (зарплата, проценты и т.д.)"
    )
    date_raw: str = Field(
        "", description="Дата как произнесена (вчера, в четверг, и т.д.)"
    )
    date: str = Field("", description="Дата в формате YYYY-MM-DD")
