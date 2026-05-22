"""Endpoints de metas (CRUD + progresso)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.utils import get_request_tenant

from .models import Goal


def _no_tenant():
    return Response(
        {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _serialize(g: Goal, *, with_progress: bool = True) -> dict:
    out: dict = {
        "id": g.id,
        "name": g.name,
        "kind": g.kind,
        "period": g.period,
        "target_value": float(g.target_value),
        "starts_on": g.starts_on.isoformat(),
        "is_active": g.is_active,
        "created_at": g.created_at.isoformat(),
    }
    if with_progress:
        out["progress"] = g.current_progress()
    return out


VALID_KINDS = {c[0] for c in Goal.Kind.choices}
VALID_PERIODS = {c[0] for c in Goal.Period.choices}


def _parse_payload(data: dict) -> tuple[dict | None, Response | None]:
    name = (data.get("name") or "").strip()
    kind = (data.get("kind") or "").strip()
    period = (data.get("period") or "month").strip()
    target_raw = data.get("target_value")

    if not name:
        return None, Response(
            {"error": {"code": "missing_name", "message": "Informe um nome para a meta."}},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if kind not in VALID_KINDS:
        return None, Response(
            {"error": {"code": "invalid_kind", "message": f"kind inválido. Use: {sorted(VALID_KINDS)}"}},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if period not in VALID_PERIODS:
        return None, Response(
            {"error": {"code": "invalid_period", "message": f"period inválido. Use: {sorted(VALID_PERIODS)}"}},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        target = Decimal(str(target_raw))
    except (InvalidOperation, TypeError):
        return None, Response(
            {"error": {"code": "invalid_target", "message": "target_value precisa ser numérico."}},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if target <= 0:
        return None, Response(
            {"error": {"code": "invalid_target", "message": "target_value deve ser > 0."}},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return {"name": name[:120], "kind": kind, "period": period, "target_value": target}, None


class GoalsListView(APIView):
    """GET / POST"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _no_tenant()
        qs = Goal.unsafe_objects.filter(tenant_id=tenant.id).order_by("-is_active", "-created_at")
        return Response({"goals": [_serialize(g) for g in qs]})

    def post(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return _no_tenant()
        payload, err = _parse_payload(request.data)
        if err is not None:
            return err
        goal = Goal.unsafe_objects.create(tenant_id=tenant.id, **payload)
        return Response(_serialize(goal), status=status.HTTP_201_CREATED)


class GoalDetailView(APIView):
    """GET / PATCH / DELETE"""

    permission_classes = [IsAuthenticated]

    def _get_or_404(self, request: Request, pk: int) -> tuple[Goal | None, Response | None]:
        tenant = get_request_tenant(request)
        if tenant is None:
            return None, _no_tenant()
        try:
            g = Goal.unsafe_objects.get(tenant_id=tenant.id, id=pk)
        except Goal.DoesNotExist:
            return None, Response(
                {"error": {"code": "not_found", "message": "Meta não encontrada."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return g, None

    def get(self, request: Request, pk: int) -> Response:
        g, err = self._get_or_404(request, pk)
        if err is not None:
            return err
        return Response(_serialize(g))  # type: ignore[arg-type]

    def patch(self, request: Request, pk: int) -> Response:
        g, err = self._get_or_404(request, pk)
        if err is not None:
            return err
        assert g is not None
        # Aceita atualização parcial. Reusa validação se kind/target presentes.
        if "name" in request.data:
            g.name = (request.data.get("name") or "").strip()[:120] or g.name
        if "kind" in request.data:
            k = request.data.get("kind")
            if k not in VALID_KINDS:
                return Response(
                    {"error": {"code": "invalid_kind", "message": "kind inválido."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            g.kind = k
        if "period" in request.data:
            p = request.data.get("period")
            if p not in VALID_PERIODS:
                return Response(
                    {"error": {"code": "invalid_period", "message": "period inválido."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            g.period = p
        if "target_value" in request.data:
            try:
                target = Decimal(str(request.data.get("target_value")))
                if target <= 0:
                    raise InvalidOperation
                g.target_value = target
            except (InvalidOperation, TypeError):
                return Response(
                    {"error": {"code": "invalid_target", "message": "target_value precisa ser > 0."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if "is_active" in request.data:
            g.is_active = bool(request.data.get("is_active"))
        g.save()
        return Response(_serialize(g))

    def delete(self, request: Request, pk: int) -> Response:
        g, err = self._get_or_404(request, pk)
        if err is not None:
            return err
        assert g is not None
        g.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
