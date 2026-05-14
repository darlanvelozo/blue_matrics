"""
Helpers de período. Aceita presets ("last_30d", "this_month", "ytd", "last_12m")
ou range explícito (start, end). Devolve datas em UTC.

Inclui período de comparação automático para MoM/YoY.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.utils import timezone


@dataclass(frozen=True)
class Period:
    start: date
    end: date  # inclusivo

    def days(self) -> int:
        return (self.end - self.start).days + 1

    def shift_for_comparison(self, mode: str) -> Period:
        """
        mode='prev_period' → mesmo número de dias, imediatamente anterior
        mode='yoy'         → mesmo período do ano anterior
        """
        if mode == "yoy":
            return Period(
                start=self.start - relativedelta(years=1),
                end=self.end - relativedelta(years=1),
            )
        # prev_period (padrão)
        delta = self.end - self.start + timedelta(days=1)
        return Period(start=self.start - delta, end=self.start - timedelta(days=1))


def today() -> date:
    return timezone.now().date()


def resolve_period(
    *,
    preset: str | None = None,
    start: str | date | None = None,
    end: str | date | None = None,
) -> Period:
    """Resolve preset string OU range explícito para `Period`."""
    if start and end:
        s = _parse(start)
        e = _parse(end)
        if s > e:
            s, e = e, s
        return Period(start=s, end=e)

    p = (preset or "last_30d").lower()
    t = today()

    if p == "last_30d":
        return Period(start=t - timedelta(days=29), end=t)
    if p == "last_90d":
        return Period(start=t - timedelta(days=89), end=t)
    if p == "this_month":
        return Period(start=t.replace(day=1), end=t)
    if p == "last_month":
        first_this = t.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        return Period(start=last_prev.replace(day=1), end=last_prev)
    if p == "ytd":
        return Period(start=t.replace(month=1, day=1), end=t)
    if p == "last_12m":
        return Period(start=t - relativedelta(months=12) + timedelta(days=1), end=t)
    # default
    return Period(start=t - timedelta(days=29), end=t)


def _parse(v: str | date | datetime) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return datetime.strptime(str(v), "%Y-%m-%d").date()


def month_buckets(period: Period) -> list[tuple[date, date]]:
    """Lista (start, end) de cada mês dentro do período (truncado nas pontas)."""
    out: list[tuple[date, date]] = []
    cursor = period.start.replace(day=1)
    while cursor <= period.end:
        month_end = (cursor + relativedelta(months=1)) - timedelta(days=1)
        bucket_start = max(cursor, period.start)
        bucket_end = min(month_end, period.end)
        out.append((bucket_start, bucket_end))
        cursor = cursor + relativedelta(months=1)
    return out
