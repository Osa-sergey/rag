"""LLM-based structured extraction of expenses and transfers.

Uses llama-cpp server (OpenAI-compatible API) with Pydantic JSON schema
for structured output generation.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date

from voice_bot.schemas import Expense, LLMConfig, Transfer

logger = logging.getLogger(__name__)


EXPENSE_SYSTEM_PROMPT = """Ты — ассистент для учёта расходов. Извлеки информацию о трате из текста.
Если дата не указана явно, используй сегодняшнюю: {today}.
Ответь ТОЛЬКО валидным JSON без комментариев.
"""

EXPENSE_USER_PROMPT = """Извлеки из текста информацию о трате в JSON формате:
{{
  "amount": <число (сумма)>,
  "currency": "<валюта, по умолчанию RUB>",
  "category": "<категория: {categories}>",
  "description": "<краткое описание покупки>",
  "date": "<дата YYYY-MM-DD>"
}}

Текст: "{text}"
"""

TRANSFER_SYSTEM_PROMPT = """Ты — ассистент для учёта переводов между людьми. Извлеки информацию о переводе из текста.
Если дата не указана явно, используй сегодняшнюю: {today}.
Ответь ТОЛЬКО валидным JSON без комментариев.
"""

TRANSFER_USER_PROMPT = """Извлеки из текста информацию о переводе в JSON формате:
{{
  "amount": <число (сумма)>,
  "currency": "<валюта, по умолчанию RUB>",
  "from_person": "<кто переводит>",
  "to_person": "<кому переводят>",
  "date": "<дата YYYY-MM-DD>",
  "description": "<краткое описание>"
}}

Текст: "{text}"
"""


class Extractor:
    """Extract structured expense/transfer data from text via LLM."""

    def __init__(self, cfg: LLMConfig, category_names: list[str] | None = None) -> None:
        from langchain_openai import ChatOpenAI

        self._llm = ChatOpenAI(
            model=cfg.model_name,
            base_url=cfg.base_url,
            api_key=cfg.api_key or "not-needed",
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        self._category_names = category_names or [
            "еда", "транспорт", "развлечения", "одежда",
            "здоровье", "связь", "жильё", "другое",
        ]
        logger.info(
            "Extractor initialized (model=%s, url=%s)",
            cfg.model_name,
            cfg.base_url,
        )

    async def extract_expense(self, text: str) -> Expense:
        """Extract expense fields from text."""
        today = date.today().isoformat()
        categories_str = "/".join(self._category_names)

        messages = [
            {"role": "system", "content": EXPENSE_SYSTEM_PROMPT.format(today=today)},
            {
                "role": "user",
                "content": EXPENSE_USER_PROMPT.format(
                    text=text, categories=categories_str,
                ),
            },
        ]

        raw = await self._invoke(messages)
        data = self._parse_json(raw)
        return Expense.model_validate(data)

    async def extract_transfer(self, text: str) -> Transfer:
        """Extract transfer fields from text."""
        today = date.today().isoformat()

        messages = [
            {"role": "system", "content": TRANSFER_SYSTEM_PROMPT.format(today=today)},
            {"role": "user", "content": TRANSFER_USER_PROMPT.format(text=text)},
        ]

        raw = await self._invoke(messages)
        data = self._parse_json(raw)
        return Transfer.model_validate(data)

    # ── Internal ──────────────────────────────────────────────

    async def _invoke(self, messages: list[dict]) -> str:
        """Call LLM and return raw content string."""
        from langchain_core.messages import HumanMessage, SystemMessage

        lc_messages = []
        for m in messages:
            if m["role"] == "system":
                lc_messages.append(SystemMessage(content=m["content"]))
            else:
                lc_messages.append(HumanMessage(content=m["content"]))

        response = await self._llm.ainvoke(lc_messages)
        content = response.content
        logger.debug("LLM raw response: %s", content[:200])
        return content

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """Parse JSON from LLM response, handling markdown fences and extra text."""
        # Strip markdown code fences
        cleaned = re.sub(r"```(?:json)?\s*", "", raw)
        cleaned = cleaned.strip().rstrip("`")

        # Try to find JSON object
        match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: try parsing the whole thing
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON response: %s", raw[:300])
            raise ValueError(f"LLM returned invalid JSON: {e}") from e
