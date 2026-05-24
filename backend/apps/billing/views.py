"""Endpoints de billing."""
from __future__ import annotations

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.utils import get_request_tenant

from .models import Invoice, Plan, Subscription
from .services import BillingError, ensure_subscription_for_tenant, get_billing_service


def _serialize_plan(p: Plan) -> dict:
    return {
        "code": p.code,
        "name": p.name,
        "description": p.description,
        "price_monthly": float(p.price_monthly),
        "billing_amount": float(p.billing_amount),
        "billing_interval": p.billing_interval,
        "billing_interval_count": p.billing_interval_count,
        "currency": p.currency,
        "max_users": p.max_users,
        "features": p.features,
        "sort_order": p.sort_order,
    }


def _serialize_subscription(s: Subscription) -> dict:
    return {
        "plan": _serialize_plan(s.plan),
        "status": s.status,
        "is_active": s.is_active,
        "is_trialing": s.is_trialing,
        "trial_expired": s.trial_expired,
        "trial_ends_at": s.trial_ends_at.isoformat() if s.trial_ends_at else None,
        "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
        "cancel_at_period_end": s.cancel_at_period_end,
        "canceled_at": s.canceled_at.isoformat() if s.canceled_at else None,
    }


def _serialize_invoice(i: Invoice) -> dict:
    return {
        "id": i.id,
        "amount": float(i.amount),
        "currency": i.currency,
        "status": i.status,
        "period_start": i.period_start.isoformat() if i.period_start else None,
        "period_end": i.period_end.isoformat() if i.period_end else None,
        "paid_at": i.paid_at.isoformat() if i.paid_at else None,
        "hosted_invoice_url": i.hosted_invoice_url,
        "invoice_pdf_url": i.invoice_pdf_url,
        "created_at": i.created_at.isoformat(),
    }


class ListPlansView(APIView):
    """Catálogo público de planos (usado também na landing)."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        plans = Plan.objects.filter(is_active=True)
        return Response({"plans": [_serialize_plan(p) for p in plans]})


class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            sub = ensure_subscription_for_tenant(tenant)
        except BillingError as e:
            return Response(
                {"error": {"code": "billing_error", "message": str(e)}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        invoices = Invoice.objects.filter(tenant=tenant).order_by("-created_at")[:24]
        return Response({
            "subscription": _serialize_subscription(sub),
            "invoices": [_serialize_invoice(i) for i in invoices],
            "provider": get_billing_service().name,
        })


class CheckoutView(APIView):
    """Inicia checkout. Body: { plan_code }. Resp: { url } para redirect."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        plan_code = (request.data.get("plan_code") or "").strip()
        if not plan_code:
            return Response(
                {"error": {"code": "missing_plan", "message": "Informe plan_code."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            plan = Plan.objects.get(code=plan_code, is_active=True)
        except Plan.DoesNotExist:
            return Response(
                {"error": {"code": "invalid_plan", "message": f"Plano '{plan_code}' não existe."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sub = ensure_subscription_for_tenant(tenant)
        front = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        try:
            session = get_billing_service().create_checkout_session(
                subscription=sub,
                plan=plan,
                success_url=f"{front.rstrip('/')}/app/billing",
                cancel_url=f"{front.rstrip('/')}/app/billing",
            )
        except BillingError as e:
            return Response(
                {"error": {"code": "checkout_failed", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"url": session.url, "session_id": session.session_id})


class CancelView(APIView):
    """Cancela no fim do período."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            sub = Subscription.objects.get(tenant=tenant)
        except Subscription.DoesNotExist:
            return Response(
                {"error": {"code": "no_subscription", "message": "Sem assinatura."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        get_billing_service().cancel_subscription(sub)
        sub.refresh_from_db()
        return Response(_serialize_subscription(sub))


class ReactivateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            sub = Subscription.objects.get(tenant=tenant)
        except Subscription.DoesNotExist:
            return Response(
                {"error": {"code": "no_subscription", "message": "Sem assinatura."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        get_billing_service().reactivate_subscription(sub)
        sub.refresh_from_db()
        return Response(_serialize_subscription(sub))


class StripeWebhookView(APIView):
    """
    Webhook Stripe. Verifica assinatura, atualiza Subscription/Invoice.
    Em modo mock, este endpoint não é chamado (mock completa tudo no checkout).
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []  # webhook não tem JWT

    def post(self, request: Request) -> Response:
        secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
        if not secret:
            return Response({"received": True, "skipped": "no_secret"})
        try:
            import stripe  # type: ignore[import-untyped]
        except ImportError:
            return Response({"received": True, "skipped": "no_stripe_sdk"})

        sig = request.headers.get("Stripe-Signature", "")
        try:
            event = stripe.Webhook.construct_event(request.body, sig, secret)
        except Exception as e:  # noqa: BLE001
            return Response(
                {"error": {"code": "invalid_signature", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        handler = _WEBHOOK_HANDLERS.get(event["type"])
        if handler:
            handler(event["data"]["object"])
        return Response({"received": True, "type": event["type"]})


# ---------------------------------------------------------------------------
# Handlers de webhook (atualizam DB local quando Stripe avisa)
# ---------------------------------------------------------------------------
def _on_checkout_completed(obj: dict) -> None:
    sub_id = obj.get("subscription")
    customer_id = obj.get("customer")
    tenant_id = (obj.get("metadata") or {}).get("tenant_id")
    if not tenant_id:
        return
    sub = Subscription.objects.filter(tenant_id=int(tenant_id)).first()
    if sub is None:
        return
    if sub_id:
        sub.stripe_subscription_id = sub_id
    if customer_id:
        sub.stripe_customer_id = customer_id
    sub.status = Subscription.Status.ACTIVE
    sub.save()


def _on_invoice_paid(obj: dict) -> None:
    sub_id = obj.get("subscription")
    if not sub_id:
        return
    sub = Subscription.objects.filter(stripe_subscription_id=sub_id).first()
    if sub is None:
        return
    from django.utils import timezone as tz
    Invoice.objects.update_or_create(
        stripe_invoice_id=obj["id"],
        defaults={
            "tenant": sub.tenant,
            "subscription": sub,
            "amount": (obj.get("amount_paid") or 0) / 100,
            "currency": (obj.get("currency") or "brl").upper(),
            "status": Invoice.Status.PAID,
            "paid_at": tz.now(),
            "hosted_invoice_url": obj.get("hosted_invoice_url") or "",
            "invoice_pdf_url": obj.get("invoice_pdf") or "",
        },
    )
    sub.status = Subscription.Status.ACTIVE
    sub.save(update_fields=["status", "updated_at"])


def _on_subscription_updated(obj: dict) -> None:
    sub = Subscription.objects.filter(stripe_subscription_id=obj["id"]).first()
    if sub is None:
        return
    sub.cancel_at_period_end = bool(obj.get("cancel_at_period_end"))
    sub.status = {
        "active": Subscription.Status.ACTIVE,
        "trialing": Subscription.Status.TRIALING,
        "past_due": Subscription.Status.PAST_DUE,
        "canceled": Subscription.Status.CANCELED,
        "incomplete": Subscription.Status.INCOMPLETE,
    }.get(obj.get("status", ""), sub.status)
    sub.save()


def _on_subscription_deleted(obj: dict) -> None:
    sub = Subscription.objects.filter(stripe_subscription_id=obj["id"]).first()
    if sub is None:
        return
    from django.utils import timezone as tz
    sub.status = Subscription.Status.CANCELED
    sub.canceled_at = tz.now()
    sub.save()


def _primary_owner_email(sub: Subscription) -> tuple[str, str] | None:
    """Acha o e-mail do owner do tenant para mandar alertas. Retorna (email, nome)."""
    membership = (
        sub.tenant.memberships
        .select_related("user")
        .filter(is_active=True, role="owner")
        .order_by("created_at")
        .first()
    )
    if not membership or not membership.user.email:
        return None
    return (membership.user.email, membership.user.full_name or membership.user.email.split("@")[0])


def _on_invoice_payment_failed(obj: dict) -> None:
    sub_id = obj.get("subscription")
    if not sub_id:
        return
    sub = Subscription.objects.filter(stripe_subscription_id=sub_id).first()
    if sub is None:
        return
    sub.status = Subscription.Status.PAST_DUE
    sub.save(update_fields=["status", "updated_at"])

    from django.utils import timezone as tz
    Invoice.objects.update_or_create(
        stripe_invoice_id=obj["id"],
        defaults={
            "tenant": sub.tenant,
            "subscription": sub,
            "amount": (obj.get("amount_due") or 0) / 100,
            "currency": (obj.get("currency") or "brl").upper(),
            "status": Invoice.Status.OPEN,
            "hosted_invoice_url": obj.get("hosted_invoice_url") or "",
            "invoice_pdf_url": obj.get("invoice_pdf") or "",
        },
    )
    target = _primary_owner_email(sub)
    if target:
        from apps.notifications.mailer import send_payment_failed
        front = getattr(settings, "FRONTEND_URL", "").rstrip("/")
        amount = f"R$ {(obj.get('amount_due') or 0) / 100:.2f}".replace(".", ",")
        send_payment_failed(
            to=target[0],
            name=target[1],
            amount=amount,
            retry_url=obj.get("hosted_invoice_url") or f"{front}/app/billing",
        )


def _on_trial_will_end(obj: dict) -> None:
    """customer.subscription.trial_will_end: dispara ~3 dias antes do fim do trial."""
    sub_id = obj.get("id")
    if not sub_id:
        return
    sub = Subscription.objects.filter(stripe_subscription_id=sub_id).first()
    if sub is None:
        return
    target = _primary_owner_email(sub)
    if not target:
        return
    from django.utils import timezone as tz

    from apps.notifications.mailer import send_trial_ending
    trial_end_ts = obj.get("trial_end")
    if trial_end_ts:
        days_left = max(1, (
            tz.datetime.fromtimestamp(trial_end_ts, tz=tz.get_current_timezone()) - tz.now()
        ).days)
    else:
        days_left = 3
    front = getattr(settings, "FRONTEND_URL", "").rstrip("/")
    send_trial_ending(
        to=target[0],
        name=target[1],
        days_left=days_left,
        billing_url=f"{front}/app/billing",
    )


_WEBHOOK_HANDLERS = {
    "checkout.session.completed": _on_checkout_completed,
    "invoice.paid": _on_invoice_paid,
    "invoice.payment_failed": _on_invoice_payment_failed,
    "customer.subscription.updated": _on_subscription_updated,
    "customer.subscription.deleted": _on_subscription_deleted,
    "customer.subscription.trial_will_end": _on_trial_will_end,
}
