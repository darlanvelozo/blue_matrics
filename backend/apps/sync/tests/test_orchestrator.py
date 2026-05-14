"""Testes do orquestrador de sync (com cliente mockado)."""
from __future__ import annotations

import httpx
import pytest

from apps.integrations.models import ContaAzulConnection
from apps.sync.models import (
    Category,
    Customer,
    FinancialEntry,
    Product,
    RawPayload,
    Sale,
    SaleItem,
    Salesperson,
    SyncLog,
)
from apps.sync.orchestrator import sync_tenant


@pytest.fixture(autouse=True)
def _settings(settings):
    settings.CONTA_AZUL = {
        "CLIENT_ID": "cid",
        "CLIENT_SECRET": "csec",
        "REDIRECT_URI": "http://x",
        "AUTH_URL": "https://auth.contaazul.com/oauth2/authorize",
        "TOKEN_URL": "https://auth.contaazul.com/oauth2/token",
        "API_BASE": "https://api-v2.contaazul.com/v1",
        "SCOPE": "openid",
    }


@pytest.fixture
def connected_tenant(make_tenant):
    t = make_tenant()
    conn = ContaAzulConnection.objects.create(tenant=t, client_id="cid")
    conn.set_client_secret("csec")
    conn.set_access_token("valid", expires_in=3600)
    conn.set_refresh_token("ref")
    conn.mark_connected()
    conn.save()
    return t, conn


# Payloads sintéticos por endpoint
RESPONSES = {
    "/categorias": {"data": [
        {"id": "cat-r", "nome": "Vendas", "tipo": "receita"},
        {"id": "cat-d", "nome": "Aluguel", "tipo": "despesa"},
    ]},
    "/vendedores": {"data": [{"id": "vend-1", "nome": "Maria"}]},
    "/pessoas": {"data": [
        {"id": "cli-1", "nome": "Padaria Pão Bom", "documento": "12345"},
        {"id": "cli-2", "nome": "Mercearia X"},
    ]},
    "/produtos": {"data": [
        {"id": "prod-1", "nome": "Pão Francês", "valorVenda": "0.50"},
    ]},
    "/vendas": {"data": [
        {
            "id": "sale-1",
            "numero": "001",
            "situacao": "finalizada",
            "valorTotal": "100.00",
            "dataEmissao": "2026-04-01T10:00:00",
            "idCliente": "cli-1",
            "idVendedor": "vend-1",
            "itens": [
                {"id": "i1", "idProduto": "prod-1", "quantidade": 200, "valorUnitario": "0.50", "valorTotal": "100"},
            ],
        }
    ]},
    "/financeiro/contas-a-receber": {"data": [
        {"id": "ar-1", "valor": "100", "situacao": "pago", "idCategoria": "cat-r", "idCliente": "cli-1", "dataVencimento": "2026-04-10"},
    ]},
    "/financeiro/contas-a-pagar": {"data": [
        {"id": "ap-1", "valor": "500", "situacao": "pendente", "idCategoria": "cat-d", "dataVencimento": "2026-04-15"},
    ]},
}


def _make_handler():
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path
        # remove prefix /v1
        for p in RESPONSES:
            if path.endswith(p):
                calls.append(p)
                page = int(httpx.QueryParams(req.url.query).get("page", 1))
                if page == 1:
                    return httpx.Response(200, json=RESPONSES[p])
                return httpx.Response(200, json={"data": []})
        return httpx.Response(404, text=f"unknown path: {path}")

    return handler, calls


@pytest.mark.django_db
class TestSyncTenant:
    def test_full_sync_populates_silver(self, connected_tenant):
        tenant, _ = connected_tenant
        handler, calls = _make_handler()

        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            master = sync_tenant(tenant.id, http_client=http)

        assert master.status in (SyncLog.Status.SUCCESS, SyncLog.Status.PARTIAL)
        assert master.fetched > 0

        # categorias
        assert Category.unsafe_objects.filter(tenant_id=tenant.id).count() == 2
        # vendedores
        assert Salesperson.unsafe_objects.filter(tenant_id=tenant.id).count() == 1
        # clientes
        assert Customer.unsafe_objects.filter(tenant_id=tenant.id).count() == 2
        # produtos
        assert Product.unsafe_objects.filter(tenant_id=tenant.id).count() == 1
        # vendas com FK resolvida
        sales = Sale.unsafe_objects.filter(tenant_id=tenant.id)
        assert sales.count() == 1
        sale = sales.first()
        assert sale.customer is not None
        assert sale.customer.external_id == "cli-1"
        assert sale.salesperson is not None
        assert SaleItem.unsafe_objects.filter(sale=sale).count() == 1
        # financeiro
        ar = FinancialEntry.unsafe_objects.filter(tenant_id=tenant.id, direction="receivable")
        ap = FinancialEntry.unsafe_objects.filter(tenant_id=tenant.id, direction="payable")
        assert ar.count() == 1
        assert ap.count() == 1
        # bronze guarda raw
        assert RawPayload.unsafe_objects.filter(tenant_id=tenant.id).count() >= 6

        # connection.last_synced_at atualizado
        from apps.integrations.models import ContaAzulConnection
        conn = ContaAzulConnection.objects.get(tenant_id=tenant.id)
        assert conn.last_synced_at is not None

    def test_sync_is_idempotent(self, connected_tenant):
        tenant, _ = connected_tenant
        handler, _ = _make_handler()

        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            sync_tenant(tenant.id, http_client=http)
            count_1 = Sale.unsafe_objects.filter(tenant_id=tenant.id).count()
            # rodar de novo não duplica
            sync_tenant(tenant.id, http_client=http)
            count_2 = Sale.unsafe_objects.filter(tenant_id=tenant.id).count()
        assert count_1 == count_2 == 1

    def test_one_resource_failing_does_not_kill_others(self, connected_tenant):
        tenant, _ = connected_tenant

        def handler(req: httpx.Request) -> httpx.Response:
            if "/vendas" in req.url.path:
                return httpx.Response(500, text="oops")
            for p, data in RESPONSES.items():
                if req.url.path.endswith(p):
                    page = int(httpx.QueryParams(req.url.query).get("page", 1))
                    return httpx.Response(200, json=data if page == 1 else {"data": []})
            return httpx.Response(404)

        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            master = sync_tenant(tenant.id, http_client=http)

        # status master deve indicar parcial
        assert master.status in (SyncLog.Status.PARTIAL, SyncLog.Status.FAILED)
        # outros recursos sincronizaram
        assert Customer.unsafe_objects.filter(tenant_id=tenant.id).count() == 2

    def test_raises_when_not_connected(self, make_tenant):
        t = make_tenant()
        ContaAzulConnection.objects.create(tenant=t)  # disconnected
        with pytest.raises(RuntimeError, match="não está conectado"):
            sync_tenant(t.id)
