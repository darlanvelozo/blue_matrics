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


def _nested_id(payload: dict, *keys: str) -> str:
    """Extrai `id` de um objeto aninhado. Ex: `{"cliente": {"id": "abc"}}`."""
    for k in keys:
        v = payload.get(k)
        if isinstance(v, dict):
            inner = v.get("id") or v.get("uuid") or v.get("id_legado")
            if inner:
                return str(inner)
    return ""


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
    # Conta Azul v2 usa snake_case e nomes específicos:
    #   - codigo (SKU)
    #   - valor_venda (preço — frequentemente 0 quando a empresa não define)
    #   - custo_medio (custo médio do estoque)
    #   - saldo (estoque atual)
    #   - status: "ATIVO" | "INATIVO"
    status_raw = (payload.get("status") or "").upper()
    is_active = (
        status_raw == "ATIVO"
        if status_raw
        else bool(payload.get("ativo", payload.get("active", True)))
    )
    return {
        "external_id": _get_external_id(payload, "id", "uuid"),
        "sku": (
            payload.get("codigo") or payload.get("sku") or payload.get("ean") or ""
        ).strip()[:64],
        "name": (payload.get("nome") or payload.get("name") or "").strip() or "—",
        "price": _to_decimal(
            payload.get("valor_venda")
            or payload.get("valorVenda")
            or payload.get("price")
            or payload.get("preco")
        ),
        "cost": _to_decimal(
            payload.get("custo_medio")
            or payload.get("custoMedio")
            or payload.get("valor_custo")
            or payload.get("valorCusto")
            or payload.get("cost")
            or payload.get("custo")
        ),
        "is_active": is_active,
        "stock_balance": _to_decimal(payload.get("saldo") or payload.get("stock") or 0),
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
        "parent_external_id": _first(payload, "categoria_pai", "parentId", "idPai"),
    }


def map_salesperson(payload: dict) -> dict:
    # `/venda/vendedores` v2 retorna `{id, nome, id_legado}`. Sem campo `ativo`.
    return {
        "external_id": _get_external_id(payload, "id", "uuid", "id_legado"),
        "name": (payload.get("nome") or payload.get("name") or "").strip() or "—",
        "is_active": bool(payload.get("ativo", payload.get("active", True))),
    }


def _status_text(payload: dict, *keys: str) -> str:
    """Extrai texto de status que pode vir como string ou objeto aninhado.

    Conta Azul v2 retorna `situacao: {"nome": "APROVADO", "descricao": "..."}`
    em alguns endpoints (vendas, financeiro). Outros endpoints/versões usam
    string crua. Normalizamos para uma string lowercase.
    """
    for k in keys:
        v = payload.get(k)
        if isinstance(v, dict):
            inner = v.get("nome") or v.get("valor") or v.get("codigo") or v.get("descricao")
            if inner:
                return str(inner).lower()
        elif v:
            return str(v).lower()
    return ""


def map_sale(payload: dict, *, customer_lookup=None, salesperson_lookup=None) -> dict:
    """`customer_lookup` e `salesperson_lookup` são funções (external_id) -> Model | None."""
    status_raw = _status_text(payload, "situacao", "status")
    status_map = {
        "rascunho": "draft", "draft": "draft",
        # `/venda/busca` v2: situacao.nome = APROVADO, CANCELADO, ESPERANDO_APROVACAO
        "aberta": "open", "open": "open",
        "aprovada": "open", "aprovado": "open", "approved": "open",
        "esperando_aprovacao": "open", "waiting_approved": "open", "waiting": "open",
        "fechada": "closed", "closed": "closed",
        "finalizada": "closed", "finalizado": "closed",
        "cancelada": "canceled", "cancelado": "canceled",
        "canceled": "canceled", "cancelled": "canceled",
    }
    status = status_map.get(status_raw, "open")

    customer_ext = (
        _first(payload, "idCliente", "clienteId", "customerId", "id_cliente")
        or _nested_id(payload, "cliente", "customer")
    )
    sp_ext = (
        _first(payload, "idVendedor", "vendedorId", "salespersonId", "id_vendedor")
        or _nested_id(payload, "vendedor", "salesperson")
    )

    return {
        "external_id": _get_external_id(payload, "id", "uuid"),
        "number": str(payload.get("numero") or payload.get("number") or "")[:40],
        "status": status,
        "issued_at": _to_datetime(
            payload.get("dataEmissao")
            or payload.get("data_emissao")
            or payload.get("data")
            or payload.get("issued_at")
        ),
        "total": _to_decimal(
            payload.get("valorTotal")
            or payload.get("valor_total")
            or payload.get("total")
            or payload.get("valor")
        ),
        "discount": _to_decimal(
            payload.get("desconto") or payload.get("discount")
        ),
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
    status_raw = _status_text(payload, "situacao", "status")
    status_map = {
        # PT-BR (situacao.nome em UPPERCASE no payload bruto, normalizado para lowercase)
        "pendente": "pending", "aberta": "pending", "aberto": "pending",
        "em_aberto": "pending", "a_vencer": "pending",
        "pago": "paid", "recebido": "paid", "quitado": "paid",
        "atrasado": "overdue", "vencido": "overdue",
        "cancelado": "canceled", "cancelada": "canceled",
        # EN (Conta Azul v2 usa esses no campo `status`)
        "pending": "pending", "paid": "paid", "received": "paid",
        "acquitted": "paid",  # /financeiro v2 = quitado/recebido
        "overdue": "overdue", "canceled": "canceled",
    }
    status = status_map.get(status_raw, "pending")

    # Categoria: pode vir como array `categorias: [{id, nome}]` (v2) ou objeto singular.
    cat_ext = (
        _first(payload, "idCategoria", "categoryId", "id_categoria")
        or _nested_id(payload, "categoria", "category")
    )
    if not cat_ext:
        cats = payload.get("categorias") or payload.get("categories") or []
        if isinstance(cats, list) and cats and isinstance(cats[0], dict):
            cat_ext = str(cats[0].get("id") or cats[0].get("uuid") or "")

    # Cliente/Fornecedor: aninhado. Em payables vem em `fornecedor`, em receivables em `cliente`.
    cli_ext = (
        _first(
            payload,
            "idCliente", "idFornecedor", "customerId",
            "id_cliente", "id_fornecedor",
        )
        or _nested_id(payload, "cliente", "fornecedor", "customer", "supplier")
    )

    # Valor: a v2 usa `total` (decimal). Fallback: `pago`, `valor`, etc.
    amount = _to_decimal(
        payload.get("total")
        or payload.get("valor")
        or payload.get("amount")
        or payload.get("valorTotal")
        or payload.get("valor_total")
        or payload.get("pago")
    )

    # paid_at: a v2 da Conta Azul NÃO retorna data de pagamento explícita.
    # Heurística de fallback, em ordem de qualidade:
    #   1. dataPagamento explícito (se algum dia aparecer)
    #   2. data_competencia — quando o evento financeiro foi reconhecido. É a
    #      melhor proxy para a data efetiva de pagamento na maioria dos casos.
    #   3. data_vencimento — para boletos pagos pontualmente, é uma boa proxy.
    #   4. NUNCA usar data_alteracao/data_criacao — refletem a data da
    #      sincronização ou ajuste em massa, NÃO o pagamento real. Já causou
    #      inflação artificial de receita (incidente 2026-05-26: R$ 1,1M
    #      falsos concentrados em 2025-12-04 em vez de espalhados pelos meses).
    paid_at = _to_date(
        payload.get("dataPagamento")
        or payload.get("data_pagamento")
        or payload.get("paidAt")
        or payload.get("pagamento")
    )
    if paid_at is None and status == "paid":
        paid_at = _to_date(
            payload.get("data_competencia")
            or payload.get("dataCompetencia")
            or payload.get("data_vencimento")
            or payload.get("dataVencimento")
            or payload.get("dueDate")
            or payload.get("vencimento")
        )

    return {
        "external_id": _get_external_id(payload, "id", "uuid"),
        "direction": direction,
        "status": status,
        "description": (
            payload.get("descricao") or payload.get("description") or ""
        )[:255],
        "amount": amount,
        "due_date": _to_date(
            payload.get("dataVencimento")
            or payload.get("data_vencimento")
            or payload.get("dueDate")
            or payload.get("vencimento")
        ),
        "paid_at": paid_at,
        "category": category_lookup(cat_ext) if (category_lookup and cat_ext) else None,
        "customer": customer_lookup(cli_ext) if (customer_lookup and cli_ext) else None,
    }
