"""Paginação padrão simples — `?page=1&page_size=20`."""
from __future__ import annotations

from collections.abc import Iterable
from math import ceil
from typing import Any


def paginate(qs: Iterable, *, page: int, page_size: int) -> tuple[list[Any], dict]:
    """
    Devolve (items, meta). Funciona com QuerySet (preferido) ou list/iterable.

    Meta:
        { "page", "page_size", "total", "total_pages" }
    """
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    if hasattr(qs, "count"):
        total = qs.count()
        start = (page - 1) * page_size
        items = list(qs[start : start + page_size])
    else:
        all_items = list(qs)
        total = len(all_items)
        start = (page - 1) * page_size
        items = all_items[start : start + page_size]

    total_pages = ceil(total / page_size) if total else 0
    return items, {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


def parse_pagination(request) -> tuple[int, int]:  # type: ignore[no-untyped-def]
    try:
        page = int(request.query_params.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.query_params.get("page_size", 20))
    except (TypeError, ValueError):
        page_size = 20
    return page, page_size
