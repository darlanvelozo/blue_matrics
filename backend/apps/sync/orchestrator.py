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
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.integrations.models import ContaAzulConnection
from apps.tenants.context import set_current_tenant

from . import mappers
from .client import ContaAzulAPIError, ContaAzulClient
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

# Mapeamento de recurso → (endpoint Conta Azul, RawPayload.Resource)
# OBS: endpoints podem variar. Documentamos o "melhor palpite" baseado na v2;
# se forem diferentes no portal, ajustar aqui.
RESOURCE_ENDPOINTS: dict[str, tuple[str, str]] = {
    "categories": ("/categorias", RawPayload.Resource.CATEGORIES),
    "salespeople": ("/vendedores", RawPayload.Resource.SALESPEOPLE),
    "customers": ("/pessoas", RawPayload.Resource.CUSTOMERS),
    "products": ("/produtos", RawPayload.Resource.PRODUCTS),
    "sales": ("/vendas", RawPayload.Resource.SALES),
    "financial_receivables": (
        "/financeiro/contas-a-receber",
        RawPayload.Resource.FINANCIAL_RECEIVABLES,
    ),
    "financial_payables": (
        "/financeiro/contas-a-pagar",
        RawPayload.Resource.FINANCIAL_PAYABLES,
    ),
}


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
        for item in client.paginate(endpoint, params=params):
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
    since = (timezone.now() - timedelta(days=window_days)).date().isoformat()

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
        for item in client.paginate(endpoint, params={"dataInicial": since}):
            try:
                _save_raw(tenant_id, raw_kind, item, log)
                defaults = mappers.map_sale(item, customer_lookup=_customer, salesperson_lookup=_salesperson)
                ext = defaults.pop("external_id")
                with transaction.atomic():
                    sale, _ = _upsert(Sale, tenant_id=tenant_id, external_id=ext, defaults=defaults)
                    SaleItem.unsafe_objects.filter(tenant_id=tenant_id, sale=sale).delete()
                    raw_items: Iterable[dict] = (
                        item.get("itens") or item.get("items") or []
                    )
                    for raw_item in raw_items:
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
    since = (timezone.now() - timedelta(days=window_days)).date().isoformat()

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
        for item in client.paginate(endpoint, params={"dataInicial": since}):
            try:
                _save_raw(tenant_id, raw_kind, item, log)
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
