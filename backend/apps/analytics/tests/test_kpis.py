"""Testes dos KPIs sobre dados Silver."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.analytics import kpis
from apps.analytics.periods import Period
from apps.sync.models import Customer, FinancialEntry, Product, Sale, SaleItem, Salesperson


@pytest.fixture
def setup_data(db, make_tenant):
    t = make_tenant("dashboards")
    cust = Customer.unsafe_objects.create(tenant_id=t.id, external_id="c1", name="Cliente Top")
    cust2 = Customer.unsafe_objects.create(tenant_id=t.id, external_id="c2", name="Outro")
    sp = Salesperson.unsafe_objects.create(tenant_id=t.id, external_id="s1", name="Maria")
    prod = Product.unsafe_objects.create(
        tenant_id=t.id, external_id="p1", name="Pão", price=Decimal("10"), cost=Decimal("3")
    )

    def make_sale(*, total, when, status=Sale.Status.CLOSED, customer=cust, salesperson=sp):
        return Sale.unsafe_objects.create(
            tenant_id=t.id,
            external_id=f"sale-{when.isoformat()}-{total}",
            number=f"n-{total}",
            status=status,
            customer=customer,
            salesperson=salesperson,
            issued_at=when,
            total=Decimal(str(total)),
        )

    def make_item(sale, *, qty, unit_price, total=None, product=prod):
        return SaleItem.unsafe_objects.create(
            tenant_id=t.id, sale=sale, product=product,
            description=product.name, quantity=Decimal(str(qty)),
            unit_price=Decimal(str(unit_price)),
            total=Decimal(str(total if total is not None else qty * unit_price)),
        )

    def make_fin(*, direction, status, amount, due, paid=None):
        return FinancialEntry.unsafe_objects.create(
            tenant_id=t.id,
            external_id=f"fin-{direction}-{due.isoformat()}-{amount}",
            direction=direction,
            status=status,
            amount=Decimal(str(amount)),
            due_date=due,
            paid_at=paid,
        )

    return {
        "tenant": t,
        "cust": cust,
        "cust2": cust2,
        "sp": sp,
        "prod": prod,
        "make_sale": make_sale,
        "make_item": make_item,
        "make_fin": make_fin,
    }


def _dt(y, m, d, h=12):
    return timezone.make_aware(datetime(y, m, d, h))


@pytest.mark.django_db
class TestRevenue:
    def test_sums_closed_sales_in_period(self, setup_data):
        t = setup_data["tenant"]
        setup_data["make_sale"](total=100, when=_dt(2026, 4, 5))
        setup_data["make_sale"](total=200, when=_dt(2026, 4, 20))
        setup_data["make_sale"](total=999, when=_dt(2026, 5, 1))  # fora

        p = Period(start=date(2026, 4, 1), end=date(2026, 4, 30))
        assert kpis.revenue(t.id, p) == Decimal("300")

    def test_ignores_non_closed_sales(self, setup_data):
        t = setup_data["tenant"]
        setup_data["make_sale"](total=100, when=_dt(2026, 4, 5))
        setup_data["make_sale"](total=200, when=_dt(2026, 4, 6), status=Sale.Status.OPEN)
        setup_data["make_sale"](total=300, when=_dt(2026, 4, 7), status=Sale.Status.CANCELED)

        p = Period(start=date(2026, 4, 1), end=date(2026, 4, 30))
        assert kpis.revenue(t.id, p) == Decimal("100")

    def test_zero_when_empty(self, setup_data):
        t = setup_data["tenant"]
        p = Period(start=date(2026, 4, 1), end=date(2026, 4, 30))
        assert kpis.revenue(t.id, p) == Decimal("0")


@pytest.mark.django_db
class TestAvgTicket:
    def test_average(self, setup_data):
        t = setup_data["tenant"]
        setup_data["make_sale"](total=100, when=_dt(2026, 4, 5))
        setup_data["make_sale"](total=200, when=_dt(2026, 4, 6))
        setup_data["make_sale"](total=300, when=_dt(2026, 4, 7))

        p = Period(start=date(2026, 4, 1), end=date(2026, 4, 30))
        assert kpis.avg_ticket(t.id, p) == Decimal("200")

    def test_zero_when_no_sales(self, setup_data):
        t = setup_data["tenant"]
        p = Period(start=date(2026, 4, 1), end=date(2026, 4, 30))
        assert kpis.avg_ticket(t.id, p) == Decimal("0")


@pytest.mark.django_db
class TestCashFlow:
    def test_cash_in_and_out(self, setup_data):
        t = setup_data["tenant"]
        d = setup_data["make_fin"]
        # in
        d(direction="receivable", status=FinancialEntry.Status.PAID,
          amount=500, due=date(2026, 4, 10), paid=date(2026, 4, 10))
        d(direction="receivable", status=FinancialEntry.Status.PAID,
          amount=300, due=date(2026, 4, 12), paid=date(2026, 4, 15))
        # out
        d(direction="payable", status=FinancialEntry.Status.PAID,
          amount=200, due=date(2026, 4, 1), paid=date(2026, 4, 1))
        d(direction="payable", status=FinancialEntry.Status.PAID,
          amount=100, due=date(2026, 4, 5), paid=date(2026, 4, 5))

        p = Period(start=date(2026, 4, 1), end=date(2026, 4, 30))
        assert kpis.cash_in(t.id, p) == Decimal("800")
        assert kpis.cash_out(t.id, p) == Decimal("300")
        assert kpis.net_profit(t.id, p) == Decimal("500")

    def test_ignores_unpaid(self, setup_data):
        t = setup_data["tenant"]
        setup_data["make_fin"](
            direction="receivable", status=FinancialEntry.Status.PENDING,
            amount=1000, due=date(2026, 4, 10),
        )
        p = Period(start=date(2026, 4, 1), end=date(2026, 4, 30))
        assert kpis.cash_in(t.id, p) == Decimal("0")


@pytest.mark.django_db
class TestOverdueRate:
    def test_calculates_percentage(self, setup_data):
        t = setup_data["tenant"]
        d = setup_data["make_fin"]
        today = timezone.now().date()
        # 1000 total: 300 vencido, 700 a vencer
        d(direction="receivable", status=FinancialEntry.Status.PENDING,
          amount=300, due=today - timedelta(days=10))
        d(direction="receivable", status=FinancialEntry.Status.PENDING,
          amount=700, due=today + timedelta(days=10))
        rate = kpis.overdue_rate(t.id)
        assert 29.9 < rate < 30.1

    def test_zero_when_no_data(self, setup_data):
        assert kpis.overdue_rate(setup_data["tenant"].id) == 0.0


@pytest.mark.django_db
class TestTopCustomers:
    def test_orders_by_total_desc(self, setup_data):
        t = setup_data["tenant"]
        setup_data["make_sale"](total=100, when=_dt(2026, 4, 5), customer=setup_data["cust"])
        setup_data["make_sale"](total=200, when=_dt(2026, 4, 6), customer=setup_data["cust"])
        setup_data["make_sale"](total=50, when=_dt(2026, 4, 7), customer=setup_data["cust2"])

        p = Period(start=date(2026, 4, 1), end=date(2026, 4, 30))
        top = kpis.top_customers(t.id, p, limit=10)
        assert [c["name"] for c in top] == ["Cliente Top", "Outro"]
        assert top[0]["total"] == 300.0
        assert top[0]["sales"] == 2


@pytest.mark.django_db
class TestRevenueByMonth:
    def test_buckets_into_months(self, setup_data):
        t = setup_data["tenant"]
        setup_data["make_sale"](total=100, when=_dt(2026, 3, 15))
        setup_data["make_sale"](total=200, when=_dt(2026, 4, 1))
        setup_data["make_sale"](total=300, when=_dt(2026, 4, 20))

        p = Period(start=date(2026, 3, 1), end=date(2026, 4, 30))
        out = kpis.revenue_by_month(t.id, p)
        assert len(out) == 2
        assert out[0]["month"] == "2026-03"
        assert out[0]["revenue"] == 100.0
        assert out[1]["month"] == "2026-04"
        assert out[1]["revenue"] == 500.0


@pytest.mark.django_db
class TestExecutiveSummary:
    def test_full_payload_with_comparison(self, setup_data):
        t = setup_data["tenant"]
        # current
        setup_data["make_sale"](total=1000, when=_dt(2026, 4, 5))
        # previous (prev_period: marzo)
        setup_data["make_sale"](total=500, when=_dt(2026, 3, 5))

        p = Period(start=date(2026, 4, 1), end=date(2026, 4, 30))
        data = kpis.executive_summary(t.id, p, "prev_period")
        assert data["period"]["start"] == "2026-04-01"
        assert data["revenue"]["current"] == 1000.0
        assert data["revenue"]["previous"] == 500.0
        assert data["revenue"]["change_pct"] == 100.0
        assert "revenue_by_month" in data
        assert "top_customers" in data
        assert "overdue_rate" in data


@pytest.mark.django_db
class TestTenantIsolation:
    def test_revenue_does_not_leak_between_tenants(self, setup_data, make_tenant):
        t1 = setup_data["tenant"]
        t2 = make_tenant("other")
        setup_data["make_sale"](total=100, when=_dt(2026, 4, 5))

        # cria sale no outro tenant
        Sale.unsafe_objects.create(
            tenant_id=t2.id, external_id="other-sale", number="x",
            status=Sale.Status.CLOSED, issued_at=_dt(2026, 4, 5),
            total=Decimal("99999"),
        )

        p = Period(start=date(2026, 4, 1), end=date(2026, 4, 30))
        assert kpis.revenue(t1.id, p) == Decimal("100")
        assert kpis.revenue(t2.id, p) == Decimal("99999")
