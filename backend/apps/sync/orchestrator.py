"""
Orquestrador de sincronização.

Cada `sync_resource(...)` cria um SyncLog, percorre o cursor da API
(usando `ContaAzulClient.paginate`) e faz upsert na Silver via mappers.

Ordens:
- Categorias e Vendedores primeiro (lookups para Sales/FinancialEntry)
- Depois Customers, Products
- Depois Sales (com itens)
- Depois Financeiro (receivables / payables)

Os endpoints Conta Azul podem mudar. O caminho é tomado a partir do
mapeamento abaixo — se um endpoint estiver indisponível, o recurso falha
graciosamente sem derrubar os demais.

Janela inicial de sincronização: 365 dias (12 meses, conforme escolhido).
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.integrations.models import ContaAzulConnection
from apps.tenants.context import set_current_tenant

from . import mappers
from .client import ContaAzulAPIError, ContaAzulClient
from .mappers import _to_decimal
from .models import (
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

logger = logging.getLogger(__name__)

INITIAL_WINDOW_DAYS = 365  # 12 meses

# Mapeamento de recurso → (endpoint Conta Azul v2, RawPayload.Resource)
# Validado contra api-v2.contaazul.com em 2026-05-22 com app dev.
# Recursos marcados com (opt-out) podem retornar 404 — falham graceful e o
# orquestrador segue.
RESOURCE_ENDPOINTS: dict[str, tuple[str, str]] = {
    "categories": ("/categorias", RawPayload.Resource.CATEGORIES),
    "customers": ("/pessoa", RawPayload.Resource.CUSTOMERS),  # singular!
    "products": ("/produtos", RawPayload.Resource.PRODUCTS),
    "salespeople": ("/venda/vendedores", RawPayload.Resource.SALESPEOPLE),
    "sales": ("/venda/busca", RawPayload.Resource.SALES),
    "financial_receivables": (
        "/financeiro/eventos-financeiros/contas-a-receber/buscar",
        RawPayload.Resource.FINANCIAL_RECEIVABLES,
    ),
    "financial_payables": (
        "/financeiro/eventos-financeiros/contas-a-pagar/buscar",
        RawPayload.Resource.FINANCIAL_PAYABLES,
    ),
}

# Recursos sem paginação convencional na API v2 — chamamos sem `pagina`/`tamanho_pagina`.
# `/venda/vendedores` responde com array no top-level (sem envelope `itens`/`paginacao`).
RESOURCES_WITHOUT_PAGINATION: set[str] = {"categories", "salespeople"}


# ============================================================================
# Helpers
# ============================================================================
def _save_raw(tenant_id: int, resource: str, payload: dict, sync_log: SyncLog) -> RawPayload | None:
    ext_id = str(payload.get("id") or payload.get("uuid") or "")
    if not ext_id:
        return None
    raw = RawPayload(
        resource=resource,
        external_id=ext_id,
        payload=payload,
        sync_log=sync_log,
        tenant_id=tenant_id,
    )
    raw.save()
    return raw


def _upsert(model, *, tenant_id: int, external_id: str, defaults: dict):  # type: ignore[no-untyped-def]
    obj, created = model.unsafe_objects.update_or_create(
        tenant_id=tenant_id,
        external_id=external_id,
        defaults=defaults,
    )
    return obj, created


# ============================================================================
# Sync por recurso
# ============================================================================
def _new_log(tenant_id: int, resource: str) -> SyncLog:
    return SyncLog.objects.create(
        tenant_id=tenant_id, resource=resource, status=SyncLog.Status.RUNNING
    )


def _finish_log(log: SyncLog, *, status: str, message: str = "") -> None:
    log.mark_finished(status, message=message)
    log.save()


def _sync_simple_resource(
    *,
    tenant_id: int,
    resource_key: str,
    client: ContaAzulClient,
    map_fn: Callable[[dict], dict],
    model: Any,
    params: dict | None = None,
) -> SyncLog:
    endpoint, raw_kind = RESOURCE_ENDPOINTS[resource_key]
    log = _new_log(tenant_id, resource_key)
    try:
        if resource_key in RESOURCES_WITHOUT_PAGINATION:
            # API responde tudo de uma vez (ex.: /categorias)
            data = client.get(endpoint, params=params)
            iterator = ContaAzulClient._extract_items(data)
        else:
            iterator = client.paginate(endpoint, params=params)
        for item in iterator:
            try:
                _save_raw(tenant_id, raw_kind, item, log)
                defaults = map_fn(item)
                ext = defaults.pop("external_id")
                with transaction.atomic():
                    _upsert(model, tenant_id=tenant_id, external_id=ext, defaults=defaults)
                log.fetched += 1
                log.upserted += 1
            except Exception as e:  # noqa: BLE001
                logger.exception("erro mapeando %s: %s", resource_key, e)
                log.errors += 1
        _finish_log(log, status=SyncLog.Status.SUCCESS if log.errors == 0 else SyncLog.Status.PARTIAL)
    except ContaAzulAPIError as e:
        _finish_log(log, status=SyncLog.Status.FAILED, message=str(e))
        raise
    return log


def sync_categories(tenant_id: int, client: ContaAzulClient) -> SyncLog:
    return _sync_simple_resource(
        tenant_id=tenant_id,
        resource_key="categories",
        client=client,
        map_fn=mappers.map_category,
        model=Category,
    )


def sync_salespeople(tenant_id: int, client: ContaAzulClient) -> SyncLog:
    return _sync_simple_resource(
        tenant_id=tenant_id,
        resource_key="salespeople",
        client=client,
        map_fn=mappers.map_salesperson,
        model=Salesperson,
    )


def sync_customers(tenant_id: int, client: ContaAzulClient) -> SyncLog:
    return _sync_simple_resource(
        tenant_id=tenant_id,
        resource_key="customers",
        client=client,
        map_fn=mappers.map_customer,
        model=Customer,
    )


def sync_products(tenant_id: int, client: ContaAzulClient) -> SyncLog:
    return _sync_simple_resource(
        tenant_id=tenant_id,
        resource_key="products",
        client=client,
        map_fn=mappers.map_product,
        model=Product,
    )


def sync_sales(tenant_id: int, client: ContaAzulClient, *, window_days: int = INITIAL_WINDOW_DAYS) -> SyncLog:
    endpoint, raw_kind = RESOURCE_ENDPOINTS["sales"]
    log = _new_log(tenant_id, "sales")
    today = timezone.now().date()
    since = (today - timedelta(days=window_days)).isoformat()
    until = today.isoformat()
    sales_params = {"data_inicio": since, "data_fim": until}

    customer_cache: dict[str, Customer | None] = {}
    salesperson_cache: dict[str, Salesperson | None] = {}
    product_cache: dict[str, Product | None] = {}

    def _customer(ext_id: str):  # type: ignore[no-untyped-def]
        if ext_id not in customer_cache:
            customer_cache[ext_id] = Customer.unsafe_objects.filter(
                tenant_id=tenant_id, external_id=ext_id
            ).first()
        return customer_cache[ext_id]

    def _salesperson(ext_id: str):  # type: ignore[no-untyped-def]
        if ext_id not in salesperson_cache:
            salesperson_cache[ext_id] = Salesperson.unsafe_objects.filter(
                tenant_id=tenant_id, external_id=ext_id
            ).first()
        return salesperson_cache[ext_id]

    def _product(ext_id: str):  # type: ignore[no-untyped-def]
        if ext_id not in product_cache:
            product_cache[ext_id] = Product.unsafe_objects.filter(
                tenant_id=tenant_id, external_id=ext_id
            ).first()
        return product_cache[ext_id]

    try:
        for item in client.paginate(endpoint, params=sales_params):
            try:
                _save_raw(tenant_id, raw_kind, item, log)
                defaults = mappers.map_sale(item, customer_lookup=_customer, salesperson_lookup=_salesperson)
                ext = defaults.pop("external_id")
                # Na v2 `/venda/busca` o campo `itens` da listagem é uma STRING
                # ("PRODUCT"/"SERVICE") e `total` vem 0. Os itens reais e o total
                # ficam em `/v1/venda/{id}/itens` (envelope `{itens, totais}`).
                detail_items: list[dict] = []
                detail_total: Decimal | None = None
                try:
                    detail = client.get(f"/venda/{ext}/itens")
                    if isinstance(detail, dict):
                        detail_items = [x for x in (detail.get("itens") or []) if isinstance(x, dict)]
                        totais = detail.get("totais") or {}
                        if isinstance(totais, dict):
                            t_prod = _to_decimal(totais.get("total_produtos"))
                            t_serv = _to_decimal(totais.get("total_servicos"))
                            t_unc = _to_decimal(totais.get("total_nao_consolidados"))
                            detail_total = t_prod + t_serv + t_unc
                except ContaAzulAPIError as detail_err:
                    logger.warning("detalhe da venda %s indisponível: %s", ext, detail_err)

                if detail_total is not None and detail_total > 0:
                    defaults["total"] = detail_total

                with transaction.atomic():
                    sale, _ = _upsert(Sale, tenant_id=tenant_id, external_id=ext, defaults=defaults)
                    SaleItem.unsafe_objects.filter(tenant_id=tenant_id, sale=sale).delete()
                    for raw_item in detail_items:
                        item_defaults = mappers.map_sale_item(raw_item, product_lookup=_product)
                        item_ext = item_defaults.pop("external_id", "") or ""
                        SaleItem.unsafe_objects.create(
                            tenant_id=tenant_id, sale=sale, external_id=item_ext, **item_defaults
                        )
                log.fetched += 1
                log.upserted += 1
            except Exception as e:  # noqa: BLE001
                logger.exception("erro em sale: %s", e)
                log.errors += 1
        _finish_log(log, status=SyncLog.Status.SUCCESS if log.errors == 0 else SyncLog.Status.PARTIAL)
    except ContaAzulAPIError as e:
        _finish_log(log, status=SyncLog.Status.FAILED, message=str(e))
        raise
    return log


def _ensure_categories_from_payload(tenant_id: int, payload: dict, *, kind: str) -> None:
    """Auto-cria/atualiza categorias mencionadas em FinancialEntry.

    A API v2 da Conta Azul retorna `categorias: [{id, nome}]` aninhado nos
    eventos financeiros, mas o endpoint `/categorias` não traz todas. Para
    rankings de categorias funcionarem, garantimos que toda categoria citada
    em um evento financeiro exista localmente.
    """
    cats = payload.get("categorias") or payload.get("categories") or []
    if not isinstance(cats, list):
        return
    for c in cats:
        if not isinstance(c, dict):
            continue
        ext = c.get("id") or c.get("uuid")
        nome = (c.get("nome") or c.get("name") or "").strip()
        if not ext or not nome:
            continue
        Category.unsafe_objects.update_or_create(
            tenant_id=tenant_id, external_id=str(ext),
            defaults={"name": nome, "kind": kind},
        )


def sync_financial(
    tenant_id: int,
    client: ContaAzulClient,
    *,
    direction: str,  # "receivable" | "payable"
    window_days: int = INITIAL_WINDOW_DAYS,
) -> SyncLog:
    resource_key = "financial_receivables" if direction == "receivable" else "financial_payables"
    endpoint, raw_kind = RESOURCE_ENDPOINTS[resource_key]
    log = _new_log(tenant_id, resource_key)
    today = timezone.now().date()
    since = (today - timedelta(days=window_days)).isoformat()
    until = (today + timedelta(days=window_days)).isoformat()
    # API exige `data_vencimento_de` (obrigatório). Pegamos janela ampla
    # cobrindo passado (recebidos/pagos) e futuro (a vencer).
    fin_params = {
        "data_vencimento_de": since,
        "data_vencimento_ate": until,
    }

    cat_cache: dict[str, Category | None] = {}
    cli_cache: dict[str, Customer | None] = {}

    def _cat(ext: str):  # type: ignore[no-untyped-def]
        if ext not in cat_cache:
            cat_cache[ext] = Category.unsafe_objects.filter(
                tenant_id=tenant_id, external_id=ext
            ).first()
        return cat_cache[ext]

    def _cli(ext: str):  # type: ignore[no-untyped-def]
        if ext not in cli_cache:
            cli_cache[ext] = Customer.unsafe_objects.filter(
                tenant_id=tenant_id, external_id=ext
            ).first()
        return cli_cache[ext]

    try:
        # Categorias mencionadas no payload financeiro são auto-criadas:
        # o endpoint `/categorias` não retorna todas; aqui garantimos cobertura.
        cat_kind = "revenue" if direction == "receivable" else "expense"
        for item in client.paginate(endpoint, params=fin_params):
            try:
                _save_raw(tenant_id, raw_kind, item, log)
                _ensure_categories_from_payload(tenant_id, item, kind=cat_kind)
                defaults = mappers.map_financial_entry(
                    item,
                    direction=direction,
                    category_lookup=_cat,
                    customer_lookup=_cli,
                )
                ext = defaults.pop("external_id")
                with transaction.atomic():
                    _upsert(FinancialEntry, tenant_id=tenant_id, external_id=ext, defaults=defaults)
                log.fetched += 1
                log.upserted += 1
            except Exception as e:  # noqa: BLE001
                logger.exception("erro em financial %s: %s", direction, e)
                log.errors += 1
        _finish_log(log, status=SyncLog.Status.SUCCESS if log.errors == 0 else SyncLog.Status.PARTIAL)
    except ContaAzulAPIError as e:
        _finish_log(log, status=SyncLog.Status.FAILED, message=str(e))
        raise
    return log


# ============================================================================
# Orquestrador master
# ============================================================================
def sync_tenant(
    tenant_id: int,
    *,
    full: bool = False,
    http_client=None,  # type: ignore[no-untyped-def]
) -> SyncLog:
    """
    Sincroniza tudo de 1 tenant. Retorna o log master.
    Cada recurso é sincronizado em sequência; falha em um não derruba os demais.
    """
    conn = ContaAzulConnection.objects.select_related("tenant").get(tenant_id=tenant_id)
    if conn.status != ContaAzulConnection.Status.CONNECTED:
        raise RuntimeError(f"Tenant {tenant_id} não está conectado à Conta Azul")

    master = SyncLog.objects.create(
        tenant_id=tenant_id, resource="", status=SyncLog.Status.RUNNING
    )

    with set_current_tenant(tenant_id):
        client = ContaAzulClient(conn, http_client=http_client)
        try:
            order = [
                ("categories", sync_categories),
                ("salespeople", sync_salespeople),
                ("customers", sync_customers),
                ("products", sync_products),
                ("sales", lambda t, c: sync_sales(t, c)),
                ("financial_receivables", lambda t, c: sync_financial(t, c, direction="receivable")),
                ("financial_payables", lambda t, c: sync_financial(t, c, direction="payable")),
            ]
            partials = 0
            failures = 0
            total_fetched = 0
            total_upserted = 0
            for _name, fn in order:
                try:
                    sub = fn(tenant_id, client)
                    total_fetched += sub.fetched
                    total_upserted += sub.upserted
                    if sub.status == SyncLog.Status.PARTIAL:
                        partials += 1
                    elif sub.status == SyncLog.Status.FAILED:
                        failures += 1
                except Exception as e:  # noqa: BLE001
                    logger.exception("recurso falhou: %s", e)
                    failures += 1

            if failures > 0:
                final_status = SyncLog.Status.PARTIAL if (failures < len(order)) else SyncLog.Status.FAILED
            elif partials > 0:
                final_status = SyncLog.Status.PARTIAL
            else:
                final_status = SyncLog.Status.SUCCESS

            master.fetched = total_fetched
            master.upserted = total_upserted
            master.errors = failures
            _finish_log(master, status=final_status)

            conn.last_synced_at = timezone.now()
            conn.save(update_fields=["last_synced_at", "updated_at"])
        finally:
            client.close()

    return master
