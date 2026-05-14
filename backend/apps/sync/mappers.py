"""
Mapeadores Bronze → Silver.

Cada função recebe o payload bruto da Conta Azul e retorna um dict com os
campos prontos para `Model.objects.update_or_create(defaults=...)`.

Não tocam no banco — pura transformação. Isso facilita o teste e suporta
reprocessar Silver a partir do Bronze sem chamar a API.

Os schemas da Conta Azul v2 mudam; mantemos o código defensivo e tolerante a
chaves ausentes. Quando algo essencial faltar, levantamos `MapperError`.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from dateutil.parser import isoparse


class MapperError(ValueError):
    """Payload em formato inesperado."""


# -------------------- helpers -------------------------------------------------
def _to_decimal(v: Any, default: str = "0") -> Decimal:
    if v is None or v == "":
        return Decimal(default)
    try:
        return Decimal(str(v))
    except (InvalidOperation, TypeError):
        return Decimal(default)


def _to_datetime(v: Any) -> datetime | None:
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    try:
        return isoparse(str(v))
    except (ValueError, TypeError):
        return None


def _to_date(v: Any) -> date | None:
    dt = _to_datetime(v)
    return dt.date() if dt else None


def _get_external_id(payload: dict, *keys: str) -> str:
    for k in keys:
        v = payload.get(k)
        if v:
            return str(v)
    raise MapperError(f"external_id ausente em payload com chaves {list(payload)[:8]}")


def _first(payload: dict, *keys: str, default: str = "") -> str:
    """Retorna o primeiro valor truthy entre as chaves, como string."""
    for k in keys:
        v = payload.get(k)
        if v:
            return str(v)
    return default


# -------------------- mappers -------------------------------------------------
def map_customer(payload: dict) -> dict:
    """Pessoa (cliente) — endpoint `/pessoas`."""
    return {
        "external_id": _get_external_id(payload, "id", "uuid"),
        "name": (payload.get("nome") or payload.get("name") or "").strip() or "—",
        "document": (payload.get("documento") or payload.get("document") or "").strip(),
        "email": (payload.get("email") or "").strip(),
        "phone": (
            payload.get("telefone")
            or payload.get("phone")
            or (payload.get("contatos") or [{}])[0].get("telefone", "")
        )[:40],
        "is_active": bool(payload.get("ativo", payload.get("active", True))),
        "created_at_external": _to_datetime(
            payload.get("dataCriacao") or payload.get("created_at")
        ),
    }


def map_product(payload: dict) -> dict:
    return {
        "external_id": _get_external_id(payload, "id", "uuid"),
        "sku": (payload.get("sku") or payload.get("codigo") or "").strip()[:64],
        "name": (payload.get("nome") or payload.get("name") or "").strip() or "—",
        "price": _to_decimal(
            payload.get("valorVenda") or payload.get("price") or payload.get("preco")
        ),
        "cost": _to_decimal(
            payload.get("valorCusto") or payload.get("cost") or payload.get("custo")
        ),
        "is_active": bool(payload.get("ativo", payload.get("active", True))),
    }


def map_category(payload: dict) -> dict:
    kind_raw = (payload.get("tipo") or payload.get("type") or "").lower()
    if kind_raw in ("receita", "revenue", "income"):
        kind = "revenue"
    elif kind_raw in ("despesa", "expense"):
        kind = "expense"
    else:
        kind = "other"
    return {
        "external_id": _get_external_id(payload, "id", "uuid"),
        "name": (payload.get("nome") or payload.get("name") or "").strip() or "—",
        "kind": kind,
        "parent_external_id": str(
            payload.get("parentId") or payload.get("idPai") or ""
        ),
    }


def map_salesperson(payload: dict) -> dict:
    return {
        "external_id": _get_external_id(payload, "id", "uuid"),
        "name": (payload.get("nome") or payload.get("name") or "").strip() or "—",
        "is_active": bool(payload.get("ativo", payload.get("active", True))),
    }


def map_sale(payload: dict, *, customer_lookup=None, salesperson_lookup=None) -> dict:
    """`customer_lookup` e `salesperson_lookup` são funções (external_id) -> Model | None."""
    status_raw = (payload.get("situacao") or payload.get("status") or "").lower()
    status_map = {
        "rascunho": "draft", "draft": "draft",
        "aberta": "open", "open": "open", "aprovada": "open",
        "fechada": "closed", "closed": "closed", "finalizada": "closed",
        "cancelada": "canceled", "canceled": "canceled", "cancelled": "canceled",
    }
    status = status_map.get(status_raw, "open")

    customer_ext = _first(payload, "idCliente", "clienteId", "customerId")
    sp_ext = _first(payload, "idVendedor", "vendedorId", "salespersonId")

    return {
        "external_id": _get_external_id(payload, "id", "uuid"),
        "number": str(payload.get("numero") or payload.get("number") or "")[:40],
        "status": status,
        "issued_at": _to_datetime(
            payload.get("dataEmissao") or payload.get("data") or payload.get("issued_at")
        ),
        "total": _to_decimal(
            payload.get("valorTotal") or payload.get("total") or payload.get("valor")
        ),
        "discount": _to_decimal(payload.get("desconto") or payload.get("discount")),
        "customer": customer_lookup(customer_ext) if (customer_lookup and customer_ext) else None,
        "salesperson": salesperson_lookup(sp_ext) if (salesperson_lookup and sp_ext) else None,
    }


def map_sale_item(payload: dict, *, product_lookup=None) -> dict:
    product_ext = _first(payload, "idProduto", "productId", "produtoId")
    qty = _to_decimal(payload.get("quantidade") or payload.get("quantity"), "1")
    unit = _to_decimal(payload.get("valorUnitario") or payload.get("unitPrice"))
    total = _to_decimal(payload.get("valorTotal") or payload.get("total")) or (qty * unit)
    return {
        "external_id": str(payload.get("id") or ""),
        "description": (payload.get("descricao") or payload.get("description") or "")[:255],
        "quantity": qty,
        "unit_price": unit,
        "total": total,
        "product": product_lookup(product_ext) if (product_lookup and product_ext) else None,
    }


def map_financial_entry(
    payload: dict,
    *,
    direction: str,
    category_lookup=None,
    customer_lookup=None,
) -> dict:
    """`direction` é 'receivable' ou 'payable' — definido pelo endpoint chamado."""
    status_raw = (payload.get("situacao") or payload.get("status") or "").lower()
    status_map = {
        "pendente": "pending", "pending": "pending", "aberta": "pending", "aberto": "pending",
        "pago": "paid", "paid": "paid", "recebido": "paid", "received": "paid", "quitado": "paid",
        "atrasado": "overdue", "overdue": "overdue", "vencido": "overdue",
        "cancelado": "canceled", "canceled": "canceled", "cancelada": "canceled",
    }
    status = status_map.get(status_raw, "pending")

    cat_ext = _first(payload, "idCategoria", "categoryId")
    cli_ext = _first(payload, "idCliente", "idFornecedor", "customerId")

    return {
        "external_id": _get_external_id(payload, "id", "uuid"),
        "direction": direction,
        "status": status,
        "description": (payload.get("descricao") or payload.get("description") or "")[:255],
        "amount": _to_decimal(
            payload.get("valor") or payload.get("amount") or payload.get("valorTotal")
        ),
        "due_date": _to_date(
            payload.get("dataVencimento") or payload.get("dueDate") or payload.get("vencimento")
        ),
        "paid_at": _to_date(
            payload.get("dataPagamento") or payload.get("paidAt") or payload.get("pagamento")
        ),
        "category": category_lookup(cat_ext) if (category_lookup and cat_ext) else None,
        "customer": customer_lookup(cli_ext) if (customer_lookup and cli_ext) else None,
    }
