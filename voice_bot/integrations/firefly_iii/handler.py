"""Intent handlers for Firefly III — bridge between classifier and API.

Each handler implements the IntentHandler protocol:
- intent_name: str property
- handle(text, result) async method
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from voice_bot.integrations.firefly_iii.account_resolver import AccountResolver
from voice_bot.integrations.firefly_iii.client import FireflyClient
from voice_bot.date_parser import DateParser
from voice_bot.integrations.firefly_iii.extractor import FireflyExtractor

logger = logging.getLogger(__name__)


@dataclass
class HandlerResult:
    """Result returned by an intent handler to the bot for formatting."""

    success: bool
    message: str  # User-friendly message
    transaction_id: str = ""
    details: dict[str, Any] | None = None


class FireflyExpenseHandler:
    """Handle 'expense' intents — create withdrawals in Firefly III."""

    def __init__(
        self,
        client: FireflyClient,
        extractor: FireflyExtractor,
        date_parser: DateParser,
        account_resolver: AccountResolver,
    ) -> None:
        self._client = client
        self._extractor = extractor
        self._date_parser = date_parser
        self._resolver = account_resolver

    @property
    def intent_name(self) -> str:
        return "expense"

    async def handle(self, text: str, **kwargs) -> HandlerResult:
        """Extract expense from text and create withdrawal in Firefly III."""
        try:
            extracted = await self._extractor.extract_expense(text)

            # Parse date from raw expression
            parsed_date = self._date_parser.parse(
                extracted.date_raw or extracted.date or ""
            )

            # Resolve source account
            resolved = self._resolver.resolve(
                extracted.source_account or None
            )
            source_name = resolved.name if resolved else "Unknown"

            # Create withdrawal
            result = await self._client.create_withdrawal(
                amount=extracted.amount,
                description=extracted.description,
                source_name=source_name,
                date=parsed_date.isoformat(),
                category_name=extracted.category,
                currency_code=extracted.currency,
                notes=f"[voice] {text}",
            )

            tx_id = result.get("data", {}).get("id", "?")

            return HandlerResult(
                success=True,
                message=(
                    f"✅ **Трата записана в Firefly III:**\n"
                    f"💰 Сумма: {extracted.amount:,.2f} {extracted.currency}\n"
                    f"📁 Категория: {extracted.category}\n"
                    f"📝 Описание: {extracted.description}\n"
                    f"🏦 Счёт: {source_name}\n"
                    f"📅 Дата: {parsed_date.isoformat()}"
                ),
                transaction_id=str(tx_id),
                details={
                    "type": "withdrawal",
                    "amount": extracted.amount,
                    "category": extracted.category,
                    "source": source_name,
                    "date": parsed_date.isoformat(),
                },
            )

        except Exception as e:
            logger.error("Expense handler failed: %s", e, exc_info=True)
            return HandlerResult(
                success=False,
                message=f"⚠️ Не удалось записать трату: {e}",
            )


class FireflyTransferHandler:
    """Handle 'transfer' intents — create transfers in Firefly III."""

    def __init__(
        self,
        client: FireflyClient,
        extractor: FireflyExtractor,
        date_parser: DateParser,
        account_resolver: AccountResolver,
    ) -> None:
        self._client = client
        self._extractor = extractor
        self._date_parser = date_parser
        self._resolver = account_resolver

    @property
    def intent_name(self) -> str:
        return "transfer"

    async def handle(self, text: str, **kwargs) -> HandlerResult:
        """Extract transfer from text and create in Firefly III."""
        try:
            extracted = await self._extractor.extract_transfer(text)

            parsed_date = self._date_parser.parse(
                extracted.date_raw or extracted.date or ""
            )

            # Resolve accounts
            source = self._resolver.resolve(extracted.source_account)
            dest = self._resolver.resolve(extracted.destination_account)

            source_name = source.name if source else "Unknown"
            dest_name = dest.name if dest else "Unknown"

            description = extracted.description or f"Перевод {source_name} → {dest_name}"

            result = await self._client.create_transfer(
                amount=extracted.amount,
                description=description,
                source_name=source_name,
                destination_name=dest_name,
                date=parsed_date.isoformat(),
                currency_code=extracted.currency,
                notes=f"[voice] {text}",
            )

            tx_id = result.get("data", {}).get("id", "?")

            return HandlerResult(
                success=True,
                message=(
                    f"✅ **Перевод записан в Firefly III:**\n"
                    f"💰 Сумма: {extracted.amount:,.2f} {extracted.currency}\n"
                    f"🏦 Откуда: {source_name}\n"
                    f"🏦 Куда: {dest_name}\n"
                    f"📝 Описание: {description}\n"
                    f"📅 Дата: {parsed_date.isoformat()}"
                ),
                transaction_id=str(tx_id),
                details={
                    "type": "transfer",
                    "amount": extracted.amount,
                    "source": source_name,
                    "destination": dest_name,
                    "date": parsed_date.isoformat(),
                },
            )

        except Exception as e:
            logger.error("Transfer handler failed: %s", e, exc_info=True)
            return HandlerResult(
                success=False,
                message=f"⚠️ Не удалось записать перевод: {e}",
            )


class FireflyDepositHandler:
    """Handle 'deposit' intents — create deposits in Firefly III."""

    def __init__(
        self,
        client: FireflyClient,
        extractor: FireflyExtractor,
        date_parser: DateParser,
        account_resolver: AccountResolver,
    ) -> None:
        self._client = client
        self._extractor = extractor
        self._date_parser = date_parser
        self._resolver = account_resolver

    @property
    def intent_name(self) -> str:
        return "deposit"

    async def handle(self, text: str, **kwargs) -> HandlerResult:
        """Extract deposit from text and create in Firefly III."""
        try:
            extracted = await self._extractor.extract_deposit(text)

            parsed_date = self._date_parser.parse(
                extracted.date_raw or extracted.date or ""
            )

            dest = self._resolver.resolve(
                extracted.destination_account or None
            )
            dest_name = dest.name if dest else "Unknown"

            result = await self._client.create_deposit(
                amount=extracted.amount,
                description=extracted.description,
                destination_name=dest_name,
                date=parsed_date.isoformat(),
                revenue_name=extracted.revenue_account,
                currency_code=extracted.currency,
                notes=f"[voice] {text}",
            )

            tx_id = result.get("data", {}).get("id", "?")

            return HandlerResult(
                success=True,
                message=(
                    f"✅ **Доход записан в Firefly III:**\n"
                    f"💰 Сумма: {extracted.amount:,.2f} {extracted.currency}\n"
                    f"🏦 Счёт: {dest_name}\n"
                    f"📝 Описание: {extracted.description}\n"
                    f"💼 Источник: {extracted.revenue_account}\n"
                    f"📅 Дата: {parsed_date.isoformat()}"
                ),
                transaction_id=str(tx_id),
                details={
                    "type": "deposit",
                    "amount": extracted.amount,
                    "destination": dest_name,
                    "revenue": extracted.revenue_account,
                    "date": parsed_date.isoformat(),
                },
            )

        except Exception as e:
            logger.error("Deposit handler failed: %s", e, exc_info=True)
            return HandlerResult(
                success=False,
                message=f"⚠️ Не удалось записать доход: {e}",
            )
