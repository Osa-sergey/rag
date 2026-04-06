"""Natural language date parser for Russian voice input.

Converts spoken date references like "вчера", "в четверг",
"на прошлой неделе в среду", "3 дня назад" to concrete dates.

No heavy NLP dependencies — uses regex + weekday mapping.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

# Weekday names (Monday=0 … Sunday=6) — Russian → Python weekday int
_WEEKDAYS_RU: dict[str, int] = {
    "понедельник": 0,
    "вторник": 1,
    "среда": 2, "среду": 2,
    "четверг": 3,
    "пятница": 4, "пятницу": 4,
    "суббота": 5, "субботу": 5,
    "воскресенье": 6, "воскресение": 6,
}

# Numeric words → int
_NUM_WORDS: dict[str, int] = {
    "один": 1, "одну": 1, "одного": 1,
    "два": 2, "две": 2, "двух": 2,
    "три": 3, "трёх": 3, "трех": 3,
    "четыре": 4, "четырёх": 4, "четырех": 4,
    "пять": 5, "пяти": 5,
    "шесть": 6, "шести": 6,
    "семь": 7, "семи": 7,
    "восемь": 8, "восьми": 8,
    "девять": 9, "девяти": 9,
    "десять": 10, "десяти": 10,
}


class DateParser:
    """Parse Russian natural-language date references to ``datetime.date``.

    Usage::

        parser = DateParser()
        parser.parse("вчера")                        # today - 1
        parser.parse("на прошлой неделе в четверг")   # last week's Thursday
        parser.parse("3 дня назад")                  # today - 3
    """

    def parse(self, text: str, reference: date | None = None) -> date:
        """Parse a date expression relative to *reference* (default: today).

        Returns *reference* if nothing is recognized.
        """
        ref = reference or date.today()
        text = text.lower().strip()

        # ── Exact keywords ────────────────────────────────────
        if text in ("сегодня", ""):
            return ref

        if text == "вчера":
            return ref - timedelta(days=1)

        if text == "позавчера":
            return ref - timedelta(days=2)

        if text == "завтра":
            return ref + timedelta(days=1)

        if text == "послезавтра":
            return ref + timedelta(days=2)

        # ── "N дней/недель назад" ─────────────────────────────
        m = re.search(
            r"(\d+|" + "|".join(_NUM_WORDS.keys()) + r")\s+"
            r"(день|дня|дней|неделю|недели|недель|месяц|месяца|месяцев)\s+назад",
            text,
        )
        if m:
            raw_n, unit = m.group(1), m.group(2)
            n = int(raw_n) if raw_n.isdigit() else _NUM_WORDS.get(raw_n, 1)
            if unit.startswith("день") or unit.startswith("дн"):
                return ref - timedelta(days=n)
            if unit.startswith("недел"):
                return ref - timedelta(weeks=n)
            if unit.startswith("месяц") or unit.startswith("месяц"):
                # Approximate month as 30 days
                return ref - timedelta(days=n * 30)

        # ── "неделю назад" / "на прошлой неделе" (without day) ─
        if re.search(r"неделю\s+назад", text) and not self._has_weekday(text):
            return ref - timedelta(weeks=1)

        # ── "на прошлой неделе в <weekday>" ───────────────────
        m = re.search(
            r"(?:на\s+)?прошл\w*\s+недел\w*"
            r"(?:\s+в\s+|\s+)(" + "|".join(_WEEKDAYS_RU.keys()) + r")",
            text,
        )
        if m:
            target_wd = _WEEKDAYS_RU[m.group(1)]
            return self._last_week_weekday(ref, target_wd)

        # ── "на позапрошлой неделе в <weekday>" ───────────────
        m = re.search(
            r"(?:на\s+)?позапрошл\w*\s+недел\w*"
            r"(?:\s+в\s+|\s+)(" + "|".join(_WEEKDAYS_RU.keys()) + r")",
            text,
        )
        if m:
            target_wd = _WEEKDAYS_RU[m.group(1)]
            return self._last_week_weekday(ref - timedelta(weeks=1), target_wd)

        # ── "в <weekday>" / "в этот <weekday>" ────────────────
        m = re.search(
            r"(?:в\s+(?:этот|эту|это)?\s*)?(" + "|".join(_WEEKDAYS_RU.keys()) + r")",
            text,
        )
        if m:
            target_wd = _WEEKDAYS_RU[m.group(1)]
            return self._most_recent_weekday(ref, target_wd)

        # ── "на прошлой неделе" (no weekday → Monday) ─────────
        if re.search(r"(?:на\s+)?прошл\w*\s+недел", text):
            return self._last_week_weekday(ref, 0)

        # ── ISO date fallback (YYYY-MM-DD) ────────────────────
        m = re.search(r"\d{4}-\d{2}-\d{2}", text)
        if m:
            return date.fromisoformat(m.group(0))

        # ── DD.MM.YYYY format ─────────────────────────────────
        m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
        if m:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))

        # Nothing matched — return reference date
        return ref

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _most_recent_weekday(ref: date, target_wd: int) -> date:
        """Return the most recent occurrence of *target_wd* on or before *ref*.

        If today IS the target weekday, returns today.
        """
        current_wd = ref.weekday()
        diff = (current_wd - target_wd) % 7
        return ref - timedelta(days=diff)

    @staticmethod
    def _last_week_weekday(ref: date, target_wd: int) -> date:
        """Return *target_wd* of the calendar week BEFORE the week of *ref*.

        E.g., if ref is Saturday 2026-03-22, "last week's Thursday"
        → week of March 16–22 is current, so last week is March 9–15,
        Thursday = March 12.
        """
        # Monday of current week
        current_monday = ref - timedelta(days=ref.weekday())
        # Monday of previous week
        last_monday = current_monday - timedelta(weeks=1)
        return last_monday + timedelta(days=target_wd)

    @staticmethod
    def _has_weekday(text: str) -> bool:
        """Check if text contains any weekday name."""
        return any(wd in text for wd in _WEEKDAYS_RU)
