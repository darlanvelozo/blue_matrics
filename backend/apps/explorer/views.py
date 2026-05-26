"""
Endpoints de listagem (drill-down) — leitura paginada de Customer/Product/Sale/FinancialEntry.

Todos respeitam o tenant atual (via `unsafe_objects` + filter explícito).
Aceitam filtros opcionais para uso em drill-down do dashboard.
"""
from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from typing import Any

from django.db.models import Count, Max, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.sync.models import (
    Category,
    Customer,
    FinancialEntry,
    Product,
    Sale,
    SaleItem,
    Salesperson,
)
from apps.tenants.utils import get_request_tenant

from .pagination import paginate, parse_pagination


def _aware(d, *, end_of_day: bool = False):  # type: ignore[no-untyped-def]
    t = time.max if end_of_day else time.min
    return timezone.make_aware(datetime.combine(d, t))


def _parse_date(s: str | None):  # type: ignore[no-untyped-def]
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _to_float(v: Any) -> float:
    return float(v) if v is not None else 0.0


def _no_tenant_response() -> Response:
    return Response(
        {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
        status=status.HTTP_400_BAD_REQUEST,
    )


# ===========================================================================
# Customers
# ===========================================================================
class CustomersListView(APIView):
    """
    GET /api/explorer/customers?q=&page=&page_size=&type=customer|supplier|all

    Anota agregados financeiros: total recebido (cliente), total pago (fornecedor),
    nº de transações e data da última. Para tenants que não usam o módulo Sale
    (ex.: varejo), estes valores são a única forma significativa de ranquear.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _no_tenant_response()

        q = request.query_params.get("q", "").strip()
        kind = (request.query_params.get("type") or "all").lower()
        page, page_size = parse_pagination(request)

        from django.db.models import Q
        from apps.sync.models import FinancialEntry

        # Filtros condicionais aplicados nas annotations
        recv_filter = Q(financial_entries__direction=FinancialEntry.Direction.RECEIVABLE)
        pay_filter = Q(financial_entries__direction=FinancialEntry.Direction.PAYABLE)

        qs = (
            Customer.unsafe_objects.filter(tenant_id=tenant.id)
            .annotate(
                total_received=Sum("financial_entries__amount", filter=recv_filter),
                total_paid=Sum("financial_entries__amount", filter=pay_filter),
                received_count=Count("financial_entries", filter=recv_filter),
                paid_count=Count("financial_entries", filter=pay_filter),
                last_received=Max("financial_entries__paid_at", filter=recv_filter),
                last_paid=Max("financial_entries__paid_at", filter=pay_filter),
                sales_count=Count("sales", distinct=True),
                total_spent_sales=Sum(
                    "sales__total", filter=Q(sales__status=Sale.Status.CLOSED),
                ),
            )
            .order_by("name")
        )

        if q:
            qs = qs.filter(name__icontains=q)
        if kind == "customer":
            qs = qs.filter(total_received__gt=0)
        elif kind == "supplier":
            qs = qs.filter(total_paid__gt=0)
        elif kind == "active":
            qs = qs.filter(Q(total_received__gt=0) | Q(total_paid__gt=0) | Q(sales_count__gt=0))

        # Sumário GLOBAL (do tenant inteiro — ignora filtros de tipo/busca)
        agg_real = Customer.unsafe_objects.filter(tenant_id=tenant.id).aggregate(
            grand_received=Sum(
                "financial_entries__amount",
                filter=recv_filter,
            ),
            grand_paid=Sum(
                "financial_entries__amount",
                filter=pay_filter,
            ),
        )

        items, meta = paginate(qs, page=page, page_size=page_size)

        results = []
        for c in items:
            received = float(c.total_received or 0)
            paid = float(c.total_paid or 0)
            from_sales = float(c.total_spent_sales or 0)
            # Combina datas de Sale e FinancialEntry para "última transação"
            last_dates = [d for d in [c.last_received, c.last_paid] if d]
            last_txn = max(last_dates).isoformat() if last_dates else None

            customer_type = []
            if received > 0 or (c.sales_count or 0) > 0:
                customer_type.append("Cliente")
            if paid > 0:
                customer_type.append("Fornecedor")

            results.append({
                "id": c.id,
                "external_id": c.external_id,
                "name": c.name,
                "document": c.document or "",
                "email": c.email or "",
                "phone": c.phone or "",
                "is_active": c.is_active,
                "type": " · ".join(customer_type) or "—",
                "total_received": received,
                "total_paid": paid,
                "received_count": c.received_count or 0,
                "paid_count": c.paid_count or 0,
                "last_transaction": last_txn,
                "sales_count": c.sales_count or 0,
                "total_spent_sales": from_sales,
            })

        return Response({
            "results": results,
            "meta": meta,
            "summary": {
                "total_received": _to_float(agg_real["grand_received"]),
                "total_paid": _to_float(agg_real["grand_paid"]),
            },
        })


# ===========================================================================
# Products
# ===========================================================================
class ProductsListView(APIView):
    """GET /api/explorer/products?q=&page=&page_size="""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _no_tenant_response()

        q = request.query_params.get("q", "").strip()
        page, page_size = parse_pagination(request)

        qs = Product.unsafe_objects.filter(tenant_id=tenant.id).order_by("name")
        if q:
            qs = qs.filter(name__icontains=q)

        # Sumário do conjunto filtrado (antes da paginação)
        from django.db.models import DecimalField, ExpressionWrapper, F, Sum
        agg = qs.annotate(
            estoque_valor=ExpressionWrapper(
                F("stock_balance") * F("cost"),
                output_field=DecimalField(max_digits=20, decimal_places=2),
            ),
        ).aggregate(
            total_stock_value=Sum("estoque_valor"),
            total_stock_qty=Sum("stock_balance"),
        )

        items, meta = paginate(qs, page=page, page_size=page_size)

        return Response({
            "results": [
                {
                    "id": p.id,
                    "external_id": p.external_id,
                    "sku": p.sku,
                    "name": p.name,
                    "price": _to_float(p.price),
                    "cost": _to_float(p.cost),
                    "stock_balance": _to_float(p.stock_balance),
                    "stock_value": _to_float(p.stock_balance * p.cost),
                    "margin_pct": (
                        float((p.price - p.cost) / p.price * 100)
                        if p.price and p.cost is not None else 0.0
                    ),
                    "is_active": p.is_active,
                }
                for p in items
            ],
            "meta": meta,
            "summary": {
                "total_stock_value": _to_float(agg["total_stock_value"]),
                "total_stock_qty": _to_float(agg["total_stock_qty"]),
            },
        })


# ===========================================================================
# Sales
# ===========================================================================
class SalesListView(APIView):
    """
    GET /api/explorer/sales?
        start=YYYY-MM-DD&end=YYYY-MM-DD
        &customer=<id>&salesperson=<id>&product=<id>&status=<closed|open|...>
        &q=&page=&page_size=

    Aceita combinação livre de filtros (todos opcionais).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _no_tenant_response()

        page, page_size = parse_pagination(request)
        start = _parse_date(request.query_params.get("start"))
        end = _parse_date(request.query_params.get("end"))
        customer_id = request.query_params.get("customer")
        salesperson_id = request.query_params.get("salesperson")
        product_id = request.query_params.get("product")
        sale_status = request.query_params.get("status", "").strip()
        q = request.query_params.get("q", "").strip()

        qs = (
            Sale.unsafe_objects.filter(tenant_id=tenant.id)
            .select_related("customer", "salesperson")
            .order_by("-issued_at", "-id")
        )

        if start:
            qs = qs.filter(issued_at__gte=_aware(start))
        if end:
            qs = qs.filter(issued_at__lte=_aware(end, end_of_day=True))
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if salesperson_id:
            qs = qs.filter(salesperson_id=salesperson_id)
        if product_id:
            qs = qs.filter(items__product_id=product_id).distinct()
        if sale_status:
            qs = qs.filter(status=sale_status)
        if q:
            qs = qs.filter(number__icontains=q) | qs.filter(customer__name__icontains=q)

        items, meta = paginate(qs, page=page, page_size=page_size)

        total_value = Decimal("0")
        if meta["total"]:
            agg = qs.aggregate(t=Sum("total"))
            total_value = agg.get("t") or Decimal("0")

        return Response({
            "results": [
                {
                    "id": s.id,
                    "external_id": s.external_id,
                    "number": s.number,
                    "status": s.status,
                    "customer": {"id": s.customer_id, "name": s.customer.name} if s.customer else None,
                    "salesperson": (
                        {"id": s.salesperson_id, "name": s.salesperson.name}
                        if s.salesperson else None
                    ),
                    "issued_at": s.issued_at.isoformat() if s.issued_at else None,
                    "total": _to_float(s.total),
                    "discount": _to_float(s.discount),
                }
                for s in items
            ],
            "meta": meta,
            "summary": {
                "total_value": _to_float(total_value),
                "filters": {
                    "start": start.isoformat() if start else None,
                    "end": end.isoformat() if end else None,
                    "customer_id": customer_id,
                    "salesperson_id": salesperson_id,
                    "product_id": product_id,
                    "status": sale_status or None,
                },
            },
        })


class SaleDetailView(APIView):
    """GET /api/explorer/sales/<id> — detalhes + itens"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: int) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _no_tenant_response()

        try:
            sale = (
                Sale.unsafe_objects.select_related("customer", "salesperson")
                .get(tenant_id=tenant.id, id=pk)
            )
        except Sale.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Venda não encontrada."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        items = SaleItem.unsafe_objects.filter(tenant_id=tenant.id, sale=sale).select_related("product")

        return Response({
            "id": sale.id,
            "external_id": sale.external_id,
            "number": sale.number,
            "status": sale.status,
            "issued_at": sale.issued_at.isoformat() if sale.issued_at else None,
            "total": _to_float(sale.total),
            "discount": _to_float(sale.discount),
            "customer": {"id": sale.customer_id, "name": sale.customer.name} if sale.customer else None,
            "salesperson": (
                {"id": sale.salesperson_id, "name": sale.salesperson.name}
                if sale.salesperson else None
            ),
            "items": [
                {
                    "id": it.id,
                    "description": it.description,
                    "product": {"id": it.product_id, "name": it.product.name} if it.product else None,
                    "quantity": _to_float(it.quantity),
                    "unit_price": _to_float(it.unit_price),
                    "total": _to_float(it.total),
                }
                for it in items
            ],
        })


# ===========================================================================
# Financial entries
# ===========================================================================
class FinancialListView(APIView):
    """
    GET /api/explorer/financial?
        direction=receivable|payable
        &status=pending|paid|overdue|canceled
        &start=&end=&category=<id>&customer=<id>
        &page=&page_size=
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _no_tenant_response()

        page, page_size = parse_pagination(request)
        direction = request.query_params.get("direction", "").strip()
        fin_status = request.query_params.get("status", "").strip()
        start = _parse_date(request.query_params.get("start"))
        end = _parse_date(request.query_params.get("end"))
        category_id = request.query_params.get("category")
        customer_id = request.query_params.get("customer")

        qs = (
            FinancialEntry.unsafe_objects.filter(tenant_id=tenant.id)
            .select_related("category", "customer")
            .order_by("-due_date", "-id")
        )
        if direction:
            qs = qs.filter(direction=direction)
        if fin_status:
            qs = qs.filter(status=fin_status)
        if start:
            qs = qs.filter(due_date__gte=start)
        if end:
            qs = qs.filter(due_date__lte=end)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)

        items, meta = paginate(qs, page=page, page_size=page_size)
        total_value = qs.aggregate(t=Sum("amount")).get("t") or Decimal("0")

        return Response({
            "results": [
                {
                    "id": e.id,
                    "external_id": e.external_id,
                    "direction": e.direction,
                    "status": e.status,
                    "description": e.description,
                    "amount": _to_float(e.amount),
                    "due_date": e.due_date.isoformat() if e.due_date else None,
                    "paid_at": e.paid_at.isoformat() if e.paid_at else None,
                    "category": (
                        {"id": e.category_id, "name": e.category.name, "kind": e.category.kind}
                        if e.category else None
                    ),
                    "customer": (
                        {"id": e.customer_id, "name": e.customer.name}
                        if e.customer else None
                    ),
                }
                for e in items
            ],
            "meta": meta,
            "summary": {"total_value": _to_float(total_value)},
        })


# ===========================================================================
# Filter options (dropdowns)
# ===========================================================================
class FilterOptionsView(APIView):
    """
    GET /api/explorer/filter-options

    Devolve listas leves de salespeople, categories, products, customers
    para popular filtros (dropdowns) no frontend. Limitado a 200 cada.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _no_tenant_response()
        tid = tenant.id

        return Response({
            "salespeople": [
                {"id": x.id, "name": x.name}
                for x in Salesperson.unsafe_objects.filter(
                    tenant_id=tid, is_active=True
                ).order_by("name")[:200]
            ],
            "categories": [
                {"id": x.id, "name": x.name, "kind": x.kind}
                for x in Category.unsafe_objects.filter(tenant_id=tid).order_by("name")[:200]
            ],
            "customers": [
                {"id": x.id, "name": x.name}
                for x in Customer.unsafe_objects.filter(
                    tenant_id=tid, is_active=True
                ).order_by("name")[:200]
            ],
            "products": [
                {"id": x.id, "name": x.name}
                for x in Product.unsafe_objects.filter(
                    tenant_id=tid, is_active=True
                ).order_by("name")[:200]
            ],
        })
