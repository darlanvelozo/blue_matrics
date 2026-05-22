"""Testes das regras de insights."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.insights import rules
from apps.insights.models import Insight
from apps.sync.models import Customer, FinancialEntry, Sale


def _dt(y, m, d, h=12):
    return timezone.make_aware(datetime(y, m, d, h))


@pytest.fixture
def setup_data(db, make_tenant):
    t = make_tenant("insights-test")
    cust = Customer.unsafe_objects.create(tenant_id=t.id, external_id="c1", name="Ativo")
    cust2 = Customer.unsafe_objects.create(tenant_id=t.id, external_id="c2", name="Outro")
    return {"tenant": t, "cust": cust, "cust2": cust2}


def _make_sale(t, *, total, when, customer):
    return Sale.unsafe_objects.create(
        tenant_id=t.id,
        external_id=f"s-{when.isoformat()}-{total}",
        status=Sale.Status.CLOSED,
        issued_at=when,
        total=Decimal(str(total)),
        customer=customer,
    )


def _make_fin(t, **kwargs):
    return FinancialEntry.unsafe_objects.create(
        tenant_id=t.id,
        external_id=f"f-{kwargs.get('description', 'x')}-{kwargs['amount']}",
        **kwargs,
    )


@pytest.mark.django_db
class TestRevenueChange:
    def test_drop_creates_insight(self, setup_data):
        t = setup_data["tenant"]
        # Mar/2026: R$ 1000 ; Abr/2026: R$ 700 → queda 30%
        _make_sale(t, total=1000, when=_dt(2026, 3, 15), customer=setup_data["cust"])
        _make_sale(t, total=700, when=_dt(2026, 4, 10), customer=setup_data["cust"])

        out = rules.rule_revenue_change(t.id, ref=date(2026, 5, 14))
        assert len(out) == 1
        i = out[0]
        assert i["kind"] == "revenue_drop"
        assert i["severity"] == "critical"  # > 25%
        assert "30,0%" in i["title"]
        assert i["data"]["current"] == 700.0
        assert i["data"]["previous"] == 1000.0

    def test_surge(self, setup_data):
        t = setup_data["tenant"]
        _make_sale(t, total=1000, when=_dt(2026, 3, 15), customer=setup_data["cust"])
        _make_sale(t, total=2000, when=_dt(2026, 4, 10), customer=setup_data["cust"])

        out = rules.rule_revenue_change(t.id, ref=date(2026, 5, 14))
        assert len(out) == 1
        assert out[0]["kind"] == "revenue_surge"
        assert out[0]["severity"] == "success"

    def test_small_change_no_insight(self, setup_data):
        t = setup_data["tenant"]
        _make_sale(t, total=1000, when=_dt(2026, 3, 15), customer=setup_data["cust"])
        _make_sale(t, total=950, when=_dt(2026, 4, 10), customer=setup_data["cust"])
        out = rules.rule_revenue_change(t.id, ref=date(2026, 5, 14))
        assert out == []

    def test_zero_previous_no_insight(self, setup_data):
        t = setup_data["tenant"]
        _make_sale(t, total=1000, when=_dt(2026, 4, 10), customer=setup_data["cust"])
        # nada em março
        out = rules.rule_revenue_change(t.id, ref=date(2026, 5, 14))
        assert out == []


@pytest.mark.django_db
class TestExpenseSurge:
    def test_triggers_above_threshold(self, setup_data):
        t = setup_data["tenant"]
        _make_fin(t, direction="payable", status=FinancialEntry.Status.PAID,
                  amount=1000, due_date=date(2026, 3, 10), paid_at=date(2026, 3, 10))
        _make_fin(t, direction="payable", status=FinancialEntry.Status.PAID,
                  amount=1500, due_date=date(2026, 4, 5), paid_at=date(2026, 4, 5))
        out = rules.rule_expense_surge(t.id, ref=date(2026, 5, 14))
        assert len(out) == 1
        assert out[0]["kind"] == "expense_surge"


@pytest.mark.django_db
class TestOverdue:
    def test_high_overdue_triggers(self, setup_data):
        t = setup_data["tenant"]
        today = date(2026, 5, 14)
        _make_fin(t, direction="receivable", status=FinancialEntry.Status.PENDING,
                  amount=8000, due_date=today - timedelta(days=10))
        _make_fin(t, direction="receivable", status=FinancialEntry.Status.PAID,
                  amount=2000, due_date=today - timedelta(days=20),
                  paid_at=today - timedelta(days=20))
        out = rules.rule_overdue_high(t.id, ref=today)
        assert len(out) == 1
        assert out[0]["kind"] == "overdue_high"

    def test_low_overdue_no_insight(self, setup_data):
        t = setup_data["tenant"]
        today = date(2026, 5, 14)
        _make_fin(t, direction="receivable", status=FinancialEntry.Status.PENDING,
                  amount=100, due_date=today - timedelta(days=10))
        _make_fin(t, direction="receivable", status=FinancialEntry.Status.PAID,
                  amount=9900, due_date=today - timedelta(days=10),
                  paid_at=today - timedelta(days=10))
        out = rules.rule_overdue_high(t.id, ref=today)
        assert out == []


@pytest.mark.django_db
class TestInactiveCustomers:
    def test_detects_regular_customer_who_stopped(self, setup_data):
        t = setup_data["tenant"]
        c = setup_data["cust"]
        ref = date(2026, 5, 14)
        # 4 compras em 2025-12, depois nada
        for d in [1, 5, 10, 20]:
            _make_sale(t, total=100, when=_dt(2025, 12, d), customer=c)
        out = rules.rule_inactive_customers(t.id, ref=ref)
        assert len(out) == 1
        assert out[0]["kind"] == "inactive_customer"
        assert out[0]["data"]["count"] == 1

    def test_ignores_active_customer(self, setup_data):
        t = setup_data["tenant"]
        c = setup_data["cust"]
        ref = date(2026, 5, 14)
        # Compras recentes
        for d in [1, 5, 10]:
            _make_sale(t, total=100, when=_dt(2026, 5, d), customer=c)
        out = rules.rule_inactive_customers(t.id, ref=ref)
        assert out == []


@pytest.mark.django_db
class TestMaterialize:
    def test_creates_and_dedupes(self, setup_data):
        t = setup_data["tenant"]
        _make_sale(t, total=1000, when=_dt(2026, 3, 15), customer=setup_data["cust"])
        _make_sale(t, total=600, when=_dt(2026, 4, 10), customer=setup_data["cust"])

        # Primeira execução cria
        stats1 = rules.generate_insights_for_tenant(t.id, ref=date(2026, 5, 14))
        assert stats1["created"] >= 1
        # Segunda atualiza (idempotente)
        stats2 = rules.generate_insights_for_tenant(t.id, ref=date(2026, 5, 14))
        assert stats2["created"] == 0
        assert stats2["updated"] >= 1


@pytest.mark.django_db
class TestTenantIsolation:
    def test_insights_do_not_leak(self, setup_data, make_tenant):
        t1 = setup_data["tenant"]
        t2 = make_tenant("other")
        # Cria insight em t1 manualmente
        Insight.unsafe_objects.create(
            tenant_id=t1.id, kind="revenue_drop", severity="warning",
            title="A", narrative="", data={},
            period_start=date(2026, 4, 1), period_end=date(2026, 4, 30),
        )
        assert Insight.unsafe_objects.filter(tenant_id=t1.id).count() == 1
        assert Insight.unsafe_objects.filter(tenant_id=t2.id).count() == 0
