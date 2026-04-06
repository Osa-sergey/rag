"""Tests for firefly_iii.date_parser — Russian natural-language date parser."""
from datetime import date, timedelta

import pytest

from voice_bot.date_parser import DateParser

# Fixed reference date: Sunday, 2026-03-22
REF = date(2026, 3, 22)


@pytest.fixture
def parser():
    return DateParser()


class TestExactKeywords:
    def test_segodnya(self, parser):
        assert parser.parse("сегодня", REF) == REF

    def test_empty_string(self, parser):
        assert parser.parse("", REF) == REF

    def test_vchera(self, parser):
        assert parser.parse("вчера", REF) == date(2026, 3, 21)

    def test_pozavchera(self, parser):
        assert parser.parse("позавчера", REF) == date(2026, 3, 20)

    def test_zavtra(self, parser):
        assert parser.parse("завтра", REF) == date(2026, 3, 23)

    def test_poslezavtra(self, parser):
        assert parser.parse("послезавтра", REF) == date(2026, 3, 24)


class TestNDaysAgo:
    def test_3_days_ago(self, parser):
        assert parser.parse("3 дня назад", REF) == date(2026, 3, 19)

    def test_1_den_nazad(self, parser):
        assert parser.parse("1 день назад", REF) == date(2026, 3, 21)

    def test_7_dney_nazad(self, parser):
        assert parser.parse("7 дней назад", REF) == date(2026, 3, 15)

    def test_nedelyu_nazad(self, parser):
        assert parser.parse("неделю назад", REF) == date(2026, 3, 15)

    def test_2_nedeli_nazad(self, parser):
        assert parser.parse("2 недели назад", REF) == date(2026, 3, 8)

    def test_word_number(self, parser):
        assert parser.parse("пять дней назад", REF) == date(2026, 3, 17)

    def test_word_number_two(self, parser):
        assert parser.parse("два дня назад", REF) == date(2026, 3, 20)


class TestWeekday:
    """REF = Saturday 2026-03-22."""

    def test_v_chetverg(self, parser):
        # Most recent Thursday = March 19
        assert parser.parse("в четверг", REF) == date(2026, 3, 19)

    def test_v_etot_chetverg(self, parser):
        assert parser.parse("в этот четверг", REF) == date(2026, 3, 19)

    def test_v_ponedelnik(self, parser):
        # Most recent Monday = March 16
        assert parser.parse("в понедельник", REF) == date(2026, 3, 16)

    def test_v_subbotu(self, parser):
        # REF is Sunday 2026-03-22 → most recent Saturday = March 21
        assert parser.parse("в субботу", REF) == date(2026, 3, 21)

    def test_v_pyatnitzu(self, parser):
        # Most recent Friday = March 20
        assert parser.parse("в пятницу", REF) == date(2026, 3, 20)

    def test_v_sredu(self, parser):
        # Most recent Wednesday = March 18
        assert parser.parse("в среду", REF) == date(2026, 3, 18)


class TestLastWeekWeekday:
    """REF = Saturday 2026-03-22 → current week Mon = Mar 16.
    Last week: Mon Mar 9 — Sun Mar 15."""

    def test_last_week_thursday(self, parser):
        assert parser.parse("на прошлой неделе в четверг", REF) == date(2026, 3, 12)

    def test_last_week_monday(self, parser):
        assert parser.parse("на прошлой неделе в понедельник", REF) == date(2026, 3, 9)

    def test_last_week_friday(self, parser):
        assert parser.parse("на прошлой неделе в пятницу", REF) == date(2026, 3, 13)

    def test_last_week_sunday(self, parser):
        assert parser.parse("на прошлой неделе в воскресенье", REF) == date(2026, 3, 15)

    def test_last_week_no_day(self, parser):
        # Without day → Monday of last week
        assert parser.parse("на прошлой неделе", REF) == date(2026, 3, 9)


class TestISODate:
    def test_iso_format(self, parser):
        assert parser.parse("2026-01-15", REF) == date(2026, 1, 15)

    def test_dd_mm_yyyy(self, parser):
        assert parser.parse("15.01.2026", REF) == date(2026, 1, 15)


class TestFallback:
    def test_unrecognized(self, parser):
        # Unrecognized text → returns reference date
        assert parser.parse("какая-то ерунда", REF) == REF
