"""Testes do explorer (drill-down + listagens)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.sync.models import Customer, FinancialEntry, Product, Sale, SaleItem, Salesperson


def _dt(y, m, d, h=12):
    return timezone.make_aware(datetime(y, m, d, h))


@pytest.fixture
def populated(db, make_tenant):
    t = make_tenant("explorer")
    c1 = Customer.unsafe_objects.create(tenant_id=t.id, external_id="c1", name="Alpha LTDA")
    c2 = Customer.unsafe_objects.create(tenant_id=t.id, external_id="c2", name="Beta LTDA")
    sp = Salesperson.unsafe_objects.create(tenant_id=t.id, external_id="sp1", name="Maria")
    p1 = Product.unsafe_objects.create(
        tenant_id=t.id, external_id="p1", name="Pão",
        price=Decimal("5"), cost=Decimal("2"),
    )
    s1 = Sale.unsafe_objects.create(
        tenant_id=t.id, external_id="s1", number="0001",
        status=Sale.Status.CLOSED, customer=c1, salesperson=sp,
        issued_at=_dt(2026, 4, 10), total=Decimal("100"),
    )
    SaleItem.unsafe_objects.create(
        tenant_id=t.id, sale=s1, product=p1,
        description="Pão", quantity=Decimal("20"),
        unit_price=Decimal("5"), total=Decimal("100"),
    )
    Sale.unsafe_objects.create(
        tenant_id=t.id, external_id="s2", number="0002",
        status=Sale.Status.CLOSED, customer=c2, salesperson=sp,
        issued_at=_dt(2026, 4, 15), total=Decimal("50"),
    )
    return {"tenant": t, "c1": c1, "c2": c2, "sp": sp, "p1": p1, "s1": s1}


@pytest.mark.django_db
class TestCustomers:
    URL = "/api/explorer/customers"

    def test_requires_auth(self, api_client):
        assert api_client.get(self.URL).status_code == 401

    def test_lists_with_aggregates(self, authed_client, make_tenant):
        # Garante que vê somente do próprio tenant
        cust = Customer.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="x", name="Mine",
        )
        other = make_tenant("other")
        Customer.unsafe_objects.create(tenant_id=other.id, external_id="o", name="Other tenant")

        resp = authed_client.get(self.URL)
        assert resp.status_code == 200
        names = [r["name"] for r in resp.json()["results"]]
        assert "Mine" in names
        assert "Other tenant" not in names
        _ = cust  # quiet

    def test_search(self, authed_client):
        Customer.unsafe_objects.create(tenant_id=authed_client.tenant.id, external_id="a", name="Padaria")
        Customer.unsafe_objects.create(tenant_id=authed_client.tenant.id, external_id="b", name="Lavanderia")
        resp = authed_client.get(self.URL + "?q=padar")
        names = [r["name"] for r in resp.json()["results"]]
        assert "Padaria" in names
        assert "Lavanderia" not in names


@pytest.mark.django_db
class TestProducts:
    URL = "/api/explorer/products"

    def test_list(self, authed_client):
        Product.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="p", name="Pão",
            price=Decimal("10"), cost=Decimal("4"),
        )
        resp = authed_client.get(self.URL)
        body = resp.json()
        assert len(body["results"]) >= 1
        p = body["results"][0]
        assert p["price"] == 10.0
        assert p["margin_pct"] == 60.0


@pytest.mark.django_db
class TestSales:
    URL = "/api/explorer/sales"

    def test_filter_by_date(self, authed_client, populated):
        # cria sales no authed_client.tenant
        c = Customer.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="cz", name="Z",
        )
        Sale.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="x1",
            status=Sale.Status.CLOSED, customer=c, issued_at=_dt(2026, 3, 15),
            total=Decimal("100"),
        )
        Sale.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="x2",
            status=Sale.Status.CLOSED, customer=c, issued_at=_dt(2026, 5, 1),
            total=Decimal("200"),
        )
        resp = authed_client.get(self.URL + "?start=2026-04-01&end=2026-04-30")
        results = resp.json()["results"]
        assert len(results) == 0  # nada em abril

        resp = authed_client.get(self.URL + "?start=2026-03-01&end=2026-03-31")
        assert len(resp.json()["results"]) == 1

    def test_pagination(self, authed_client):
        c = Customer.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="c", name="C",
        )
        for i in range(25):
            Sale.unsafe_objects.create(
                tenant_id=authed_client.tenant.id, external_id=f"s{i}",
                status=Sale.Status.CLOSED, customer=c,
                issued_at=_dt(2026, 4, i + 1),
                total=Decimal(str(10 * (i + 1))),
            )
        resp = authed_client.get(self.URL + "?page=1&page_size=10")
        body = resp.json()
        assert len(body["results"]) == 10
        assert body["meta"]["total"] == 25
        assert body["meta"]["total_pages"] == 3
        assert body["summary"]["total_value"] > 0

    def test_filter_by_customer(self, authed_client):
        c1 = Customer.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="c1", name="A",
        )
        c2 = Customer.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="c2", name="B",
        )
        Sale.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="s1",
            status=Sale.Status.CLOSED, customer=c1, issued_at=_dt(2026, 4, 1),
            total=Decimal("100"),
        )
        Sale.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="s2",
            status=Sale.Status.CLOSED, customer=c2, issued_at=_dt(2026, 4, 2),
            total=Decimal("200"),
        )
        resp = authed_client.get(self.URL + f"?customer={c1.id}")
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["customer"]["id"] == c1.id


@pytest.mark.django_db
class TestSaleDetail:
    def test_returns_with_items(self, authed_client):
        c = Customer.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="c", name="C",
        )
        p = Product.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="p", name="Pão",
            price=Decimal("5"), cost=Decimal("2"),
        )
        s = Sale.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="s",
            status=Sale.Status.CLOSED, customer=c, issued_at=_dt(2026, 4, 1),
            total=Decimal("50"),
        )
        SaleItem.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, sale=s, product=p,
            description="Pão", quantity=Decimal("10"),
            unit_price=Decimal("5"), total=Decimal("50"),
        )
        resp = authed_client.get(f"/api/explorer/sales/{s.id}")
        assert resp.status_code == 200
        d = resp.json()
        assert d["number"] == ""
        assert d["customer"]["name"] == "C"
        assert len(d["items"]) == 1
        assert d["items"][0]["total"] == 50.0

    def test_404_for_other_tenant(self, authed_client, make_tenant, populated):
        # sale do populated é de outro tenant
        resp = authed_client.get(f"/api/explorer/sales/{populated['s1'].id}")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestFinancial:
    URL = "/api/explorer/financial"

    def test_filter_by_direction_and_status(self, authed_client):
        from datetime import date
        FinancialEntry.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="f1",
            direction="receivable", status="paid", amount=Decimal("100"),
            due_date=date(2026, 4, 1), paid_at=date(2026, 4, 1),
        )
        FinancialEntry.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="f2",
            direction="payable", status="paid", amount=Decimal("80"),
            due_date=date(2026, 4, 5), paid_at=date(2026, 4, 5),
        )
        resp = authed_client.get(self.URL + "?direction=receivable")
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["direction"] == "receivable"


@pytest.mark.django_db
class TestFilterOptions:
    URL = "/api/explorer/filter-options"

    def test_returns_lists(self, authed_client):
        from apps.sync.models import Category
        Salesperson.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="s", name="Maria",
        )
        Category.unsafe_objects.create(
            tenant_id=authed_client.tenant.id, external_id="c", name="Vendas", kind="revenue",
        )
        resp = authed_client.get(self.URL)
        d = resp.json()
        assert "salespeople" in d
        assert "categories" in d
        assert "customers" in d
        assert "products" in d
        assert any(s["name"] == "Maria" for s in d["salespeople"])
