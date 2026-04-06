"""Async HTTP client for Firefly III REST API v1.

Uses httpx with Bearer token auth to create transactions,
list accounts, categories, etc.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from voice_bot.integrations.firefly_iii.schemas import (
    FireflyAccount,
    FireflyConfig,
    TransactionRequest,
    TransactionSplit,
)

logger = logging.getLogger(__name__)

# Timeout for API calls (seconds)
_TIMEOUT = 30.0


class FireflyClient:
    """Async client for Firefly III REST API.

    Usage::

        client = FireflyClient(config)
        accounts = await client.get_accounts()
        tx_id = await client.create_withdrawal(...)
        await client.close()
    """

    def __init__(self, cfg: FireflyConfig) -> None:
        base_url = cfg.base_url.rstrip("/")
        self._api_url = f"{base_url}/api/v1"
        self._client = httpx.AsyncClient(
            base_url=self._api_url,
            headers={
                "Authorization": f"Bearer {cfg.token}",
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/json",
            },
            timeout=_TIMEOUT,
        )
        logger.info("FireflyClient initialized (url=%s)", self._api_url)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # ── Accounts ──────────────────────────────────────────────

    async def get_accounts(
        self,
        account_type: Optional[str] = None,
    ) -> list[FireflyAccount]:
        """Fetch all accounts, optionally filtered by type.

        Firefly types: asset, expense, revenue, liabilities, cash
        """
        params = {}
        if account_type:
            params["type"] = account_type

        accounts: list[FireflyAccount] = []
        page = 1

        while True:
            params["page"] = page
            resp = await self._client.get("/accounts", params=params)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                accounts.append(
                    FireflyAccount(
                        id=item["id"],
                        name=attrs.get("name", ""),
                        account_type=attrs.get("type", ""),
                        currency_code=attrs.get("currency_code", "RUB"),
                        current_balance=attrs.get("current_balance"),
                    )
                )

            # Check for next page
            meta = data.get("meta", {}).get("pagination", {})
            total_pages = meta.get("total_pages", 1)
            if page >= total_pages:
                break
            page += 1

        logger.info(
            "Fetched %d accounts (type=%s)", len(accounts), account_type or "all"
        )
        return accounts

    async def get_account_by_name(self, name: str) -> FireflyAccount | None:
        """Search for an account by exact name."""
        accounts = await self.get_accounts()
        for acc in accounts:
            if acc.name.lower() == name.lower():
                return acc
        return None

    # ── Categories ────────────────────────────────────────────

    async def get_categories(self) -> list[dict]:
        """Fetch all categories."""
        resp = await self._client.get("/categories")
        resp.raise_for_status()
        data = resp.json()
        categories = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            categories.append({
                "id": item["id"],
                "name": attrs.get("name", ""),
            })
        logger.info("Fetched %d categories", len(categories))
        return categories

    # ── Transactions ──────────────────────────────────────────

    async def create_transaction(
        self,
        request: TransactionRequest,
    ) -> dict:
        """Create a transaction (withdrawal, transfer, or deposit).

        Returns the full API response dict.
        """
        payload = request.model_dump(exclude_none=True)
        logger.debug("Creating transaction: %s", payload)

        resp = await self._client.post("/transactions", json=payload)
        resp.raise_for_status()
        result = resp.json()

        tx_data = result.get("data", {})
        tx_id = tx_data.get("id", "?")
        logger.info("Transaction #%s created successfully", tx_id)
        return result

    async def create_withdrawal(
        self,
        amount: float,
        description: str,
        source_name: str,
        date: str,
        category_name: str = "",
        currency_code: str = "RUB",
        notes: str = "",
    ) -> dict:
        """Create a withdrawal (expense) transaction.

        Args:
            amount: Transaction amount
            description: What was purchased
            source_name: Source account name (your asset account)
            date: Date in YYYY-MM-DD format
            category_name: Optional expense category
            currency_code: Currency code (default: RUB)
            notes: Optional notes (e.g.raw voice text)
        """
        split = TransactionSplit(
            type="withdrawal",
            date=date,
            amount=str(amount),
            description=description,
            source_name=source_name,
            category_name=category_name or None,
            currency_code=currency_code,
            notes=notes or None,
        )
        request = TransactionRequest(transactions=[split])
        return await self.create_transaction(request)

    async def create_transfer(
        self,
        amount: float,
        description: str,
        source_name: str,
        destination_name: str,
        date: str,
        currency_code: str = "RUB",
        notes: str = "",
    ) -> dict:
        """Create a transfer between two asset accounts.

        Args:
            amount: Transfer amount
            description: Transfer description
            source_name: Source account name
            destination_name: Destination account name
            date: Date in YYYY-MM-DD format
            currency_code: Currency code (default: RUB)
            notes: Optional notes
        """
        split = TransactionSplit(
            type="transfer",
            date=date,
            amount=str(amount),
            description=description,
            source_name=source_name,
            destination_name=destination_name,
            currency_code=currency_code,
            notes=notes or None,
        )
        request = TransactionRequest(transactions=[split])
        return await self.create_transaction(request)

    async def create_deposit(
        self,
        amount: float,
        description: str,
        destination_name: str,
        date: str,
        revenue_name: str = "",
        category_name: str = "",
        currency_code: str = "RUB",
        notes: str = "",
    ) -> dict:
        """Create a deposit (income) transaction.

        Args:
            amount: Deposit amount
            description: Income description
            destination_name: Destination asset account name
            date: Date in YYYY-MM-DD format
            revenue_name: Revenue account name (salary source, etc.)
            category_name: Optional category
            currency_code: Currency code (default: RUB)
            notes: Optional notes
        """
        split = TransactionSplit(
            type="deposit",
            date=date,
            amount=str(amount),
            description=description,
            destination_name=destination_name,
            source_name=revenue_name or None,
            category_name=category_name or None,
            currency_code=currency_code,
            notes=notes or None,
        )
        request = TransactionRequest(transactions=[split])
        return await self.create_transaction(request)

    # ── Piggy Banks ───────────────────────────────────────────

    async def get_piggy_banks(self) -> list[dict]:
        """Fetch all piggy banks."""
        resp = await self._client.get("/piggy-banks")
        resp.raise_for_status()
        data = resp.json()
        piggy_banks = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            piggy_banks.append({
                "id": item["id"],
                "name": attrs.get("name", ""),
                "target_amount": attrs.get("target_amount"),
                "current_amount": attrs.get("current_amount"),
                "account_id": attrs.get("account_id"),
            })
        logger.info("Fetched %d piggy banks", len(piggy_banks))
        return piggy_banks
