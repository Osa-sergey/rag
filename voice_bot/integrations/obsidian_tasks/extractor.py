"""LLM-based extractor for Obsidian task intents.

Extracts all structured task metadata from free-form voice text,
including people names, dates (due/start/scheduled), time slots,
recurrence rules, priority and tags.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date

from voice_bot.schemas import LLMConfig
from voice_bot.integrations.obsidian_tasks.schemas import (
    ExtractedTask,
    ExtractedTaskQuery,
    ExtractedTaskUpdate,
)

logger = logging.getLogger(__name__)

_WEEKDAY_NAMES_RU = [
    "понедельник", "вторник", "среда", "четверг",
    "пятница", "суббота", "воскресенье",
]

# ── Prompts ───────────────────────────────────────────────────

TASK_CREATE_SYSTEM = """Ты — ассистент по управлению задачами. \
Извлеки из голосового текста все структурированные данные о задаче.
Сегодняшняя дата: {today} ({weekday}).

Правила:
- Если дата не указана — used today для due_date.
- priority: high (срочно/важно), medium (средний), low (не срочно/потом), normal (по умолчанию).
- people: имена людей, упомянутых в задаче (Иванов, Маша, Котиков Федор и пр.)
- time_slot: формат "HH:MM-HH:MM" или пусто. Извлекай из "в 10:00", "с 10 до 11" и пр.
- recurrence: "every day", "every monday", "every mon,wed,fri", "every week" или пусто.
- tags: короткие ключевые слова без пробелов на русском.

Ответь ТОЛЬКО валидным JSON без комментариев и без markdown-обёртки.
"""

TASK_CREATE_USER = """Извлеки из текста задачу в JSON:
{{
  "title": "<краткое название задачи>",
  "date_raw": "<дата срока как произнесена, например 'завтра', 'в пятницу', 'через неделю'>",
  "priority": "<high|medium|low|normal>",
  "tags": ["<тег1>", "<тег2>"],
  "notes": "<дополнительные заметки если есть, иначе пусто>",
  "start_date_raw": "<дата начала как произнесена, например 'с понедельника', 'со следующей недели', иначе пусто>",
  "scheduled_date_raw": "<запланированная дата как произнесена если отдельно указана от срока, иначе пусто>",
  "time_slot": "<время в формате HH:MM-HH:MM или пусто>",
  "recurrence": "<правило повторения по-английски или пусто>",
  "people": ["<имя1>", "<имя2>"]
}}

Текст: "{text}"
"""

TASK_SHOW_SYSTEM = """Ты — ассистент по управлению задачами. \
Определи за какую дату/период пользователь хочет увидеть задачи.
Сегодняшняя дата: {today} ({weekday}).
Ответь ТОЛЬКО валидным JSON без комментариев.
"""

TASK_SHOW_USER = """Извлеки параметры запроса задач из текста в JSON:
{{
  "date_raw": "<дата как произнесена или пусто = сегодня>",
  "date_end_raw": "<конец диапазона как произнесена если диапазон, иначе пусто>",
  "show_done": <true если нужны выполненные, иначе false>
}}

Текст: "{text}"
"""


TASK_UPDATE_SYSTEM = """Ты — ассистент по управлению задачами. \
Пользователь хочет изменить существующую задачу.
Сегодняшняя дата: {today} ({weekday}).
Выдели: что нужно найти (search_query) и что нужно изменить (changes).
Ответь ТОЛЬКО валидным JSON.
"""

TASK_UPDATE_USER = """Извлеки из текста запрос на обновление задачи в JSON:
{{
  "search_query": "<ключевые слова для поиска задачи, например 'купить молоко'>",
  "search_date_raw": "<дата задачи которую ищем, если указана, иначе пусто>",
  "changes": {{
    "title": "<новое название или пусто>",
    "date_raw": "<новая дата срока как произнесена или пусто>",
    "priority": "<новый приоритет high|medium|low|normal или пусто>",
    "recurrence": "<новое правило повтора или пусто>",
    "time_slot": "<новый временной слот HH:MM-HH:MM или пусто>",
    "people_add": ["<имена для добавления>"],
    "people_remove": ["<имена для удаления>"]
  }}
}}

Текст: "{text}"
"""


AGENDA_SUMMARY_SYSTEM = """Ты — персональный ассистент. \
Суммаризуй повестку дня в 1–3 предложения на русском. \
Укажи самые важные задачи, встречи, дедлайны и ключевых людей. \
Будь кратким и конкретным. Не добавляй приветствий."""

AGENDA_SUMMARY_USER = """Вот повестка дня:

{agenda_text}

Напиши краткое резюме дня (1–3 предложения):"""


class TaskExtractor:
    """Extract rich structured task data from voice text using LLM."""

    def __init__(self, cfg: LLMConfig) -> None:
        from langchain_openai import ChatOpenAI
        self._llm = ChatOpenAI(
            model=cfg.model_name,
            base_url=cfg.base_url,
            api_key=cfg.api_key or "not-needed",
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        logger.info("TaskExtractor initialized (model=%s)", cfg.model_name)

    async def extract_create(self, text: str) -> ExtractedTask:
        """Extract full task creation data from text."""
        today = date.today()
        weekday = _WEEKDAY_NAMES_RU[today.weekday()]
        messages = [
            {"role": "system", "content": TASK_CREATE_SYSTEM.format(
                today=today.isoformat(), weekday=weekday,
            )},
            {"role": "user", "content": TASK_CREATE_USER.format(text=text)},
        ]
        raw = await self._invoke(messages)
        data = self._parse_json(raw)
        return ExtractedTask(
            title=data.get("title", text[:60]),
            date_raw=data.get("date_raw", ""),
            priority=data.get("priority", "normal"),
            tags=data.get("tags", []),
            notes=data.get("notes", ""),
            start_date_raw=data.get("start_date_raw", ""),
            scheduled_date_raw=data.get("scheduled_date_raw", ""),
            time_slot=data.get("time_slot", ""),
            recurrence=data.get("recurrence", ""),
            people=data.get("people", []),
        )

    async def extract_show_query(self, text: str) -> ExtractedTaskQuery:
        """Extract show/list query parameters."""
        today = date.today()
        weekday = _WEEKDAY_NAMES_RU[today.weekday()]
        messages = [
            {"role": "system", "content": TASK_SHOW_SYSTEM.format(
                today=today.isoformat(), weekday=weekday,
            )},
            {"role": "user", "content": TASK_SHOW_USER.format(text=text)},
        ]
        raw = await self._invoke(messages)
        data = self._parse_json(raw)
        return ExtractedTaskQuery(
            date_raw=data.get("date_raw", ""),
            date_end=data.get("date_end_raw", ""),
            show_done=bool(data.get("show_done", False)),
        )

    async def extract_update(self, text: str) -> ExtractedTaskUpdate:
        """Extract task search query + changes from voice text."""
        today = date.today()
        weekday = _WEEKDAY_NAMES_RU[today.weekday()]
        messages = [
            {"role": "system", "content": TASK_UPDATE_SYSTEM.format(
                today=today.isoformat(), weekday=weekday,
            )},
            {"role": "user", "content": TASK_UPDATE_USER.format(text=text)},
        ]
        raw = await self._invoke(messages)
        data = self._parse_json(raw)
        changes = data.get("changes", {})
        return ExtractedTaskUpdate(
            search_query=data.get("search_query", ""),
            search_date=data.get("search_date_raw", ""),
            new_title=changes.get("title", ""),
            new_date=changes.get("date_raw", ""),
            new_priority=changes.get("priority", ""),
            new_recurrence=changes.get("recurrence", ""),
            new_time_slot=changes.get("time_slot", ""),
            people_add=changes.get("people_add", []),
            people_remove=changes.get("people_remove", []),
        )

    async def summarize_agenda(self, agenda_text: str) -> str:
        """Generate a 1–3 sentence summary of the day's agenda via LLM."""
        messages = [
            {"role": "system", "content": AGENDA_SUMMARY_SYSTEM},
            {"role": "user", "content": AGENDA_SUMMARY_USER.format(agenda_text=agenda_text)},
        ]
        try:
            raw = await self._invoke(messages)
            # Strip quotes and whitespace from LLM response
            return raw.strip().strip('"').strip()
        except Exception as e:
            logger.warning("Agenda summarization failed: %s", e)
            return ""

    # ── Internal ──────────────────────────────────────────────

    async def _invoke(self, messages: list[dict]) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage
        lc = [
            SystemMessage(content=m["content"]) if m["role"] == "system"
            else HumanMessage(content=m["content"])
            for m in messages
        ]
        response = await self._llm.ainvoke(lc)
        return response.content

    @staticmethod
    def _parse_json(raw: str) -> dict:
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON: %s | raw: %.200s", e, raw)
            return {}
