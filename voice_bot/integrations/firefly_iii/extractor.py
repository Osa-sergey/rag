"""LLM-based structured extraction of financial data for Firefly III.

Extends the base voice_bot extractor to produce Firefly-specific models
with account names and raw date strings.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date

from voice_bot.schemas import LLMConfig
from voice_bot.integrations.firefly_iii.schemas import ExtractedDeposit, ExtractedExpense, ExtractedTransfer

logger = logging.getLogger(__name__)

EXPENSE_SYSTEM_PROMPT = """Ты — ассистент для учёта финансов. Извлеки информацию о трате из текста.
Сегодняшняя дата: {today} ({weekday}).
Если дата не указана явно, используй сегодняшнюю дату.
Если упомянут счёт/карта, укажи его в source_account.
ВАЖНО: поле date_raw — это дата КАК ПРОИЗНЕСЕНА пользователем (например "вчера", "в четверг", "на прошлой неделе в среду"). Если дата не упомянута, оставь пустым.
Ответь ТОЛЬКО валидным JSON без комментариев.
"""

EXPENSE_USER_PROMPT = """Извлеки из текста трату в JSON:
{{
  "amount": <число>,
  "currency": "<валюта, по умолчанию RUB>",
  "description": "<краткое описание покупки>",
  "category": "<категория: {categories}>",
  "source_account": "<счёт-источник если упомянут, иначе пусто>",
  "date_raw": "<дата как произнесена, например вчера/в четверг/на прошлой неделе>",
  "date": "<дата YYYY-MM-DD>"
}}

Текст: "{text}"
"""

TRANSFER_SYSTEM_PROMPT = """Ты — ассистент для учёта финансов. Извлеки информацию о переводе между счетами.
Сегодняшняя дата: {today} ({weekday}).
Если дата не указана явно, используй сегодняшнюю дату.
ВАЖНО: poле date_raw — это дата КАК ПРОИЗНЕСЕНА пользователем.
Ответь ТОЛЬКО валидным JSON без комментариев.
"""

TRANSFER_USER_PROMPT = """Извлеки из текста перевод между счетами в JSON:
{{
  "amount": <число>,
  "currency": "<валюта, по умолчанию RUB>",
  "source_account": "<откуда переводим>",
  "destination_account": "<куда переводим>",
  "description": "<описание перевода>",
  "date_raw": "<дата как произнесена>",
  "date": "<дата YYYY-MM-DD>"
}}

Текст: "{text}"
"""

DEPOSIT_SYSTEM_PROMPT = """Ты — ассистент для учёта финансов. Извлеки информацию о доходе/пополнении.
Сегодняшняя дата: {today} ({weekday}).
Если дата не указана явно, используй сегодняшнюю дату.
ВАЖНО: поле date_raw — это дата КАК ПРОИЗНЕСЕНА пользователем.
Ответь ТОЛЬКО валидным JSON без комментариев.
"""

DEPOSIT_USER_PROMPT = """Извлеки из текста доход/пополнение в JSON:
{{
  "amount": <число>,
  "currency": "<валюта, по умолчанию RUB>",
  "description": "<описание дохода>",
  "destination_account": "<на какой счёт зачислено, если упомянут>",
  "revenue_account": "<источник дохода: зарплата, проценты и т.д.>",
  "date_raw": "<дата как произнесена>",
  "date": "<дата YYYY-MM-DD>"
}}

Текст: "{text}"
"""

_WEEKDAY_NAMES_RU = [
    "понедельник", "вторник", "среда", "четверг",
    "пятница", "суббота", "воскресенье",
]


class FireflyExtractor:
    """Extract structured financial data from text for Firefly III."""

    def __init__(
        self,
        cfg: LLMConfig,
        category_names: list[str] | None = None,
    ) -> None:
        from langchain_openai import ChatOpenAI

        self._llm = ChatOpenAI(
            model=cfg.model_name,
            base_url=cfg.base_url,
            api_key=cfg.api_key or "not-needed",
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        self._category_names = category_names or []
        logger.info(
            "FireflyExtractor initialized (model=%s, url=%s)",
            cfg.model_name, cfg.base_url,
        )

    async def extract_expense(self, text: str) -> ExtractedExpense:
        """Extract expense from text."""
        today = date.today()
        weekday = _WEEKDAY_NAMES_RU[today.weekday()]
        categories_str = "/".join(self._category_names) if self._category_names else "еда/транспорт/развлечения/другое"

        messages = [
            {"role": "system", "content": EXPENSE_SYSTEM_PROMPT.format(
                today=today.isoformat(), weekday=weekday,
            )},
            {"role": "user", "content": EXPENSE_USER_PROMPT.format(
                text=text, categories=categories_str,
            )},
        ]
        raw = await self._invoke(messages)
        data = self._parse_json(raw)
        return ExtractedExpense.model_validate(data)

    async def extract_transfer(self, text: str) -> ExtractedTransfer:
        """Extract transfer from text."""
        today = date.today()
        weekday = _WEEKDAY_NAMES_RU[today.weekday()]

        messages = [
            {"role": "system", "content": TRANSFER_SYSTEM_PROMPT.format(
                today=today.isoformat(), weekday=weekday,
            )},
            {"role": "user", "content": TRANSFER_USER_PROMPT.format(text=text)},
        ]
        raw = await self._invoke(messages)
        data = self._parse_json(raw)
        return ExtractedTransfer.model_validate(data)

    async def extract_deposit(self, text: str) -> ExtractedDeposit:
        """Extract deposit from text."""
        today = date.today()
        weekday = _WEEKDAY_NAMES_RU[today.weekday()]

        messages = [
            {"role": "system", "content": DEPOSIT_SYSTEM_PROMPT.format(
                today=today.isoformat(), weekday=weekday,
            )},
            {"role": "user", "content": DEPOSIT_USER_PROMPT.format(text=text)},
        ]
        raw = await self._invoke(messages)
        data = self._parse_json(raw)
        return ExtractedDeposit.model_validate(data)

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
        """Parse JSON from LLM response, handling markdown fences."""
        cleaned = re.sub(r"```(?:json)?\s*", "", raw)
        cleaned = cleaned.strip().rstrip("`")

        match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON: %s", raw[:300])
            raise ValueError(f"LLM returned invalid JSON: {e}") from e
