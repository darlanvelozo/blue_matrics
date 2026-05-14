"""Testes dos mappers Bronze→Silver."""
from __future__ import annotations

from decimal import Decimal

import pytest

from apps.sync import mappers


class TestMapCustomer:
    def test_pt_br_keys(self):
        out = mappers.map_customer(
            {"id": "abc", "nome": "Padaria X", "documento": "12345678000199", "email": "a@b.com"}
        )
        assert out == {
            "external_id": "abc",
            "name": "Padaria X",
            "document": "12345678000199",
            "email": "a@b.com",
            "phone": "",
            "is_active": True,
            "created_at_external": None,
        }

    def test_en_keys_fallback(self):
        out = mappers.map_customer({"uuid": "z", "name": "X", "active": False})
        assert out["external_id"] == "z"
        assert out["is_active"] is False

    def test_missing_id_raises(self):
        with pytest.raises(mappers.MapperError):
            mappers.map_customer({"nome": "sem id"})


class TestMapProduct:
    def test_basic(self):
        out = mappers.map_product(
            {"id": "p1", "nome": "Pão", "valorVenda": "5.50", "valorCusto": "2.00"}
        )
        assert out["price"] == Decimal("5.50")
        assert out["cost"] == Decimal("2.00")
        assert out["name"] == "Pão"


class TestMapSale:
    def test_status_normalization(self):
        for raw, normalized in [
            ("rascunho", "draft"),
            ("aprovada", "open"),
            ("finalizada", "closed"),
            ("cancelada", "canceled"),
            ("XXX", "open"),
        ]:
            out = mappers.map_sale({"id": "s", "situacao": raw, "valorTotal": 0})
            assert out["status"] == normalized

    def test_lookups_called(self):
        out = mappers.map_sale(
            {"id": "s1", "idCliente": "c1", "idVendedor": "v1", "valorTotal": "100"},
            customer_lookup=lambda x: f"CUST:{x}",
            salesperson_lookup=lambda x: f"SP:{x}",
        )
        assert out["customer"] == "CUST:c1"
        assert out["salesperson"] == "SP:v1"
        assert out["total"] == Decimal("100")


class TestMapFinancialEntry:
    def test_direction_and_status(self):
        out = mappers.map_financial_entry(
            {"id": "f1", "situacao": "pago", "valor": "150", "dataVencimento": "2026-01-15"},
            direction="receivable",
        )
        assert out["direction"] == "receivable"
        assert out["status"] == "paid"
        assert out["amount"] == Decimal("150")
        assert str(out["due_date"]) == "2026-01-15"


class TestMapCategory:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("receita", "revenue"),
            ("revenue", "revenue"),
            ("despesa", "expense"),
            ("expense", "expense"),
            ("desconhecido", "other"),
            ("", "other"),
        ],
    )
    def test_kind_mapping(self, raw, expected):
        out = mappers.map_category({"id": "c", "nome": "X", "tipo": raw})
        assert out["kind"] == expected
