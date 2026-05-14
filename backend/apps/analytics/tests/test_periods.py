"""Testes dos helpers de período."""
from __future__ import annotations

from datetime import date

from freezegun import freeze_time

from apps.analytics.periods import Period, month_buckets, resolve_period


@freeze_time("2026-05-14")
class TestResolvePeriod:
    def test_last_30d(self):
        p = resolve_period(preset="last_30d")
        assert p.end == date(2026, 5, 14)
        assert p.start == date(2026, 4, 15)
        assert p.days() == 30

    def test_this_month(self):
        p = resolve_period(preset="this_month")
        assert p.start == date(2026, 5, 1)
        assert p.end == date(2026, 5, 14)

    def test_last_month(self):
        p = resolve_period(preset="last_month")
        assert p.start == date(2026, 4, 1)
        assert p.end == date(2026, 4, 30)

    def test_ytd(self):
        p = resolve_period(preset="ytd")
        assert p.start == date(2026, 1, 1)
        assert p.end == date(2026, 5, 14)

    def test_last_12m(self):
        p = resolve_period(preset="last_12m")
        assert p.end == date(2026, 5, 14)
        assert p.start == date(2025, 5, 15)

    def test_explicit_range(self):
        p = resolve_period(start="2026-01-01", end="2026-03-31")
        assert p.start == date(2026, 1, 1)
        assert p.end == date(2026, 3, 31)

    def test_swaps_inverted_range(self):
        p = resolve_period(start="2026-03-31", end="2026-01-01")
        assert p.start == date(2026, 1, 1)
        assert p.end == date(2026, 3, 31)


class TestComparison:
    def test_prev_period_same_size(self):
        p = Period(start=date(2026, 4, 1), end=date(2026, 4, 30))
        c = p.shift_for_comparison("prev_period")
        assert c.start == date(2026, 3, 2)
        assert c.end == date(2026, 3, 31)
        assert c.days() == p.days()

    def test_yoy(self):
        p = Period(start=date(2026, 4, 1), end=date(2026, 4, 30))
        c = p.shift_for_comparison("yoy")
        assert c.start == date(2025, 4, 1)
        assert c.end == date(2025, 4, 30)


class TestMonthBuckets:
    def test_single_month(self):
        p = Period(start=date(2026, 4, 5), end=date(2026, 4, 20))
        buckets = month_buckets(p)
        assert buckets == [(date(2026, 4, 5), date(2026, 4, 20))]

    def test_multi_month_truncates_edges(self):
        p = Period(start=date(2026, 1, 15), end=date(2026, 3, 10))
        buckets = month_buckets(p)
        assert buckets == [
            (date(2026, 1, 15), date(2026, 1, 31)),
            (date(2026, 2, 1), date(2026, 2, 28)),
            (date(2026, 3, 1), date(2026, 3, 10)),
        ]
