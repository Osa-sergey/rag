"""PostgreSQL storage for expenses and transfers.

Uses asyncpg with a dedicated schema (voice_expenses).
Auto-creates schema and tables on first run.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional

import asyncpg

from voice_bot.schemas import DatabaseConfig

logger = logging.getLogger(__name__)

# ── DDL ───────────────────────────────────────────────────────

_INIT_SQL = """
CREATE SCHEMA IF NOT EXISTS {schema};

CREATE TABLE IF NOT EXISTS {schema}.expenses (
    id              SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    amount          NUMERIC(12, 2) NOT NULL,
    currency        VARCHAR(10) DEFAULT 'RUB',
    category        VARCHAR(100) NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    expense_date    DATE NOT NULL,
    raw_text        TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.transfers (
    id              SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    amount          NUMERIC(12, 2) NOT NULL,
    currency        VARCHAR(10) DEFAULT 'RUB',
    from_person     VARCHAR(200) NOT NULL,
    to_person       VARCHAR(200) NOT NULL,
    transfer_date   DATE NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    raw_text        TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_date
    ON {schema}.expenses (telegram_user_id, expense_date);
CREATE INDEX IF NOT EXISTS idx_transfers_user_date
    ON {schema}.transfers (telegram_user_id, transfer_date);
CREATE INDEX IF NOT EXISTS idx_expenses_category
    ON {schema}.expenses (category);
"""


class Storage:
    """Async PostgreSQL storage for expenses and transfers."""

    def __init__(self, cfg: DatabaseConfig) -> None:
        self._cfg = cfg
        self._schema = cfg.schema_name
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Create connection pool and initialize schema."""
        self._pool = await asyncpg.create_pool(
            host=self._cfg.host,
            port=self._cfg.port,
            user=self._cfg.user,
            password=self._cfg.password,
            database=self._cfg.database,
            min_size=2,
            max_size=10,
        )
        # Auto-create schema and tables
        async with self._pool.acquire() as conn:
            await conn.execute(_INIT_SQL.format(schema=self._schema))
        logger.info("Storage connected (schema=%s)", self._schema)

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("Storage connection closed")

    # ── Expenses ──────────────────────────────────────────────

    async def add_expense(
        self,
        user_id: int,
        amount: float,
        currency: str,
        category: str,
        description: str,
        expense_date: date,
        raw_text: str,
    ) -> int:
        """Insert an expense and return its ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                INSERT INTO {self._schema}.expenses
                    (telegram_user_id, amount, currency, category, description,
                     expense_date, raw_text)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                user_id, amount, currency, category, description,
                expense_date, raw_text,
            )
            logger.info("Expense #%d added (user=%d, %.2f %s)", row["id"], user_id, amount, currency)
            return row["id"]

    async def get_expenses(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[asyncpg.Record]:
        """Get expenses for a user, optionally filtered by date range."""
        query = f"SELECT * FROM {self._schema}.expenses WHERE telegram_user_id = $1"
        params: list = [user_id]
        idx = 2

        if start_date:
            query += f" AND expense_date >= ${idx}"
            params.append(start_date)
            idx += 1
        if end_date:
            query += f" AND expense_date <= ${idx}"
            params.append(end_date)
            idx += 1

        query += " ORDER BY expense_date DESC, created_at DESC"

        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *params)

    async def get_expenses_by_category(
        self,
        user_id: int,
        category: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[asyncpg.Record]:
        """Get expenses filtered by category."""
        query = f"""
            SELECT * FROM {self._schema}.expenses
            WHERE telegram_user_id = $1 AND category = $2
        """
        params: list = [user_id, category]
        idx = 3

        if start_date:
            query += f" AND expense_date >= ${idx}"
            params.append(start_date)
            idx += 1
        if end_date:
            query += f" AND expense_date <= ${idx}"
            params.append(end_date)
            idx += 1

        query += " ORDER BY expense_date DESC"

        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *params)

    # ── Transfers ─────────────────────────────────────────────

    async def add_transfer(
        self,
        user_id: int,
        amount: float,
        currency: str,
        from_person: str,
        to_person: str,
        transfer_date: date,
        description: str,
        raw_text: str,
    ) -> int:
        """Insert a transfer and return its ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                INSERT INTO {self._schema}.transfers
                    (telegram_user_id, amount, currency, from_person, to_person,
                     transfer_date, description, raw_text)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                """,
                user_id, amount, currency, from_person, to_person,
                transfer_date, description, raw_text,
            )
            logger.info("Transfer #%d added (user=%d, %.2f %s)", row["id"], user_id, amount, currency)
            return row["id"]

    async def get_transfers(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[asyncpg.Record]:
        """Get transfers for a user, optionally filtered by date range."""
        query = f"SELECT * FROM {self._schema}.transfers WHERE telegram_user_id = $1"
        params: list = [user_id]
        idx = 2

        if start_date:
            query += f" AND transfer_date >= ${idx}"
            params.append(start_date)
            idx += 1
        if end_date:
            query += f" AND transfer_date <= ${idx}"
            params.append(end_date)
            idx += 1

        query += " ORDER BY transfer_date DESC, created_at DESC"

        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *params)

    # ── Analytics ─────────────────────────────────────────────

    async def get_summary(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """Get expense summary by category for a user."""
        query = f"""
            SELECT
                category,
                COUNT(*) as count,
                SUM(amount) as total,
                currency
            FROM {self._schema}.expenses
            WHERE telegram_user_id = $1
        """
        params: list = [user_id]
        idx = 2

        if start_date:
            query += f" AND expense_date >= ${idx}"
            params.append(start_date)
            idx += 1
        if end_date:
            query += f" AND expense_date <= ${idx}"
            params.append(end_date)
            idx += 1

        query += " GROUP BY category, currency ORDER BY total DESC"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        total_sum = sum(r["total"] for r in rows)
        return {
            "categories": [
                {
                    "category": r["category"],
                    "count": r["count"],
                    "total": float(r["total"]),
                    "currency": r["currency"],
                }
                for r in rows
            ],
            "total": float(total_sum),
        }
