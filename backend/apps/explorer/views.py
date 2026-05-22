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
    GET /api/explorer/customers?q=&page=&page_size=
    Annotated with sales count and total spent.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _no_tenant_response()

        q = request.query_params.get("q", "").strip()
        page, page_size = parse_pagination(request)

        qs = (
            Customer.unsafe_objects.filter(tenant_id=tenant.id)
            .annotate(
                total_spent=Sum(
                    "sales__total",
                    filter=Sale.Status.CLOSED == Sale._meta.get_field("status"),
                ),
                sales_count=Count("sales"),
                last_purchase=Max("sales__issued_at"),
            )
            .order_by("name")
        )
        if q:
            qs = qs.filter(name__icontains=q)

        items, meta = paginate(qs, page=page, page_size=page_size)

        return Response({
            "results": [
                {
                    "id": c.id,
                    "external_id": c.external_id,
                    "name": c.name,
                    "document": c.document,
                    "email": c.email,
                    "phone": c.phone,
                    "is_active": c.is_active,
                    "total_spent": _to_float(c.total_spent),
                    "sales_count": c.sales_count or 0,
                    "last_purchase": c.last_purchase.isoformat() if c.last_purchase else None,
                }
                for c in items
            ],
            "meta": meta,
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
                    "margin_pct": (
                        float((p.price - p.cost) / p.price * 100)
                        if p.price and p.cost is not None else 0.0
                    ),
                    "is_active": p.is_active,
                }
                for p in items
            ],
            "meta": meta,
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
