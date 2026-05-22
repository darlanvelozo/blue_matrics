"""Testes do model Goal."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.goals.models import Goal
from apps.sync.models import Customer, Sale


def _dt(y, m, d, h=12):
    return timezone.make_aware(datetime(y, m, d, h))


@pytest.mark.django_db
class TestCurrentPeriodRange:
    def test_month_range(self, make_tenant):
        t = make_tenant()
        g = Goal.unsafe_objects.create(
            tenant_id=t.id, name="m", kind=Goal.Kind.REVENUE,
            period=Goal.Period.MONTH, target_value=Decimal("1000"),
        )
        start, end = g.current_period_range(ref=date(2026, 4, 17))
        assert start == date(2026, 4, 1)
        assert end == date(2026, 4, 30)

    def test_quarter_range(self, make_tenant):
        t = make_tenant()
        g = Goal.unsafe_objects.create(
            tenant_id=t.id, name="q", kind=Goal.Kind.REVENUE,
            period=Goal.Period.QUARTER, target_value=Decimal("1000"),
        )
        # Q2 = abril-junho
        start, end = g.current_period_range(ref=date(2026, 5, 10))
        assert start == date(2026, 4, 1)
        assert end == date(2026, 6, 30)

    def test_year_range(self, make_tenant):
        t = make_tenant()
        g = Goal.unsafe_objects.create(
            tenant_id=t.id, name="y", kind=Goal.Kind.REVENUE,
            period=Goal.Period.YEAR, target_value=Decimal("1000"),
        )
        start, end = g.current_period_range(ref=date(2026, 3, 1))
        assert start == date(2026, 1, 1)
        assert end == date(2026, 12, 31)


@pytest.mark.django_db
class TestCurrentProgress:
    def test_revenue_progress(self, make_tenant):
        t = make_tenant()
        c = Customer.unsafe_objects.create(tenant_id=t.id, external_id="c", name="C")
        # 2 vendas em abril/2026 totalizando 500
        Sale.unsafe_objects.create(
            tenant_id=t.id, external_id="s1", status=Sale.Status.CLOSED,
            customer=c, issued_at=_dt(2026, 4, 5), total=Decimal("300"),
        )
        Sale.unsafe_objects.create(
            tenant_id=t.id, external_id="s2", status=Sale.Status.CLOSED,
            customer=c, issued_at=_dt(2026, 4, 20), total=Decimal("200"),
        )
        g = Goal.unsafe_objects.create(
            tenant_id=t.id, name="meta abril", kind=Goal.Kind.REVENUE,
            period=Goal.Period.MONTH, target_value=Decimal("1000"),
        )
        prog = g.current_progress(ref=date(2026, 4, 15))
        assert prog["current"] == 500.0
        assert prog["target"] == 1000.0
        assert prog["progress_pct"] == 50.0
        assert prog["achieved"] is False

    def test_num_sales_achieved(self, make_tenant):
        t = make_tenant()
        c = Customer.unsafe_objects.create(tenant_id=t.id, external_id="c", name="C")
        for i in range(5):
            Sale.unsafe_objects.create(
                tenant_id=t.id, external_id=f"s{i}", status=Sale.Status.CLOSED,
                customer=c, issued_at=_dt(2026, 4, i + 1), total=Decimal("10"),
            )
        g = Goal.unsafe_objects.create(
            tenant_id=t.id, name="vendas", kind=Goal.Kind.NUM_SALES,
            period=Goal.Period.MONTH, target_value=Decimal("3"),
        )
        prog = g.current_progress(ref=date(2026, 4, 15))
        assert prog["current"] == 5.0
        assert prog["achieved"] is True

    def test_progress_pct_capped(self, make_tenant):
        t = make_tenant()
        g = Goal.unsafe_objects.create(
            tenant_id=t.id, name="zero-target", kind=Goal.Kind.REVENUE,
            period=Goal.Period.MONTH, target_value=Decimal("0.01"),
        )
        c = Customer.unsafe_objects.create(tenant_id=t.id, external_id="c", name="C")
        Sale.unsafe_objects.create(
            tenant_id=t.id, external_id="s", status=Sale.Status.CLOSED,
            customer=c, issued_at=_dt(2026, 4, 5), total=Decimal("100000"),
        )
        prog = g.current_progress(ref=date(2026, 4, 15))
        assert prog["progress_pct"] == 999.99
