"""
Métricas SaaS operacionais. Todas read-only sobre os dados do próprio sistema.

Fórmulas:
- MRR = soma de (price_monthly) de subscriptions com status ACTIVE
- ARR = MRR * 12
- Active subscribers = subs com status ACTIVE
- Trialing = subs com status TRIALING e trial_ends_at futuro
- Churn % (mês) = subs canceladas no mês / subs ativas no início do mês
- Trial → Paid conversion = subs ACTIVE com trial_ends_at no período / subs criadas em trial no período
- MAU = users que logaram nos últimos 30 dias (placeholder: usa last_login)
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.billing.models import Invoice, Subscription
from apps.tenants.models import Tenant


def _to_float(v) -> float:  # type: ignore[no-untyped-def]
    if v is None:
        return 0.0
    return float(v)


# ---------------------------------------------------------------------------
def mrr() -> Decimal:
    qs = Subscription.objects.filter(status=Subscription.Status.ACTIVE).select_related("plan")
    return Decimal(sum((s.plan.price_monthly for s in qs), Decimal("0")))


def arr() -> Decimal:
    return mrr() * 12


def total_tenants() -> int:
    return Tenant.objects.count()


def active_subscribers() -> int:
    return Subscription.objects.filter(status=Subscription.Status.ACTIVE).count()


def trialing_count() -> int:
    now = timezone.now()
    return Subscription.objects.filter(
        status=Subscription.Status.TRIALING, trial_ends_at__gt=now
    ).count()


def expired_trials_count() -> int:
    now = timezone.now()
    return Subscription.objects.filter(
        status=Subscription.Status.TRIALING, trial_ends_at__lte=now
    ).count()


def canceled_in_period(start: date, end: date) -> int:
    return Subscription.objects.filter(
        canceled_at__date__gte=start, canceled_at__date__lte=end
    ).count()


def churn_pct_last_30d(*, ref: date | None = None) -> float:
    ref = ref or timezone.now().date()
    start = ref - timedelta(days=30)
    # subs ativas no início do período
    base = Subscription.objects.filter(
        created_at__date__lt=start,
    ).exclude(canceled_at__date__lt=start).count()
    if base == 0:
        return 0.0
    canceled = canceled_in_period(start, ref)
    return canceled / base * 100


def trial_to_paid_conversion(*, ref: date | None = None) -> float:
    """De todas as subs criadas como trial nos últimos 30d, quantas viraram ACTIVE."""
    ref = ref or timezone.now().date()
    start = ref - timedelta(days=30)
    base = Subscription.objects.filter(created_at__date__gte=start).count()
    if base == 0:
        return 0.0
    paid = Subscription.objects.filter(
        created_at__date__gte=start, status=Subscription.Status.ACTIVE
    ).count()
    return paid / base * 100


def mau_last_30d(*, ref: date | None = None) -> int:
    ref = ref or timezone.now().date()
    start = timezone.make_aware(
        timezone.datetime.combine(ref - timedelta(days=30), timezone.datetime.min.time())
    )
    return User.objects.filter(last_login__gte=start).count()


def signups_by_day(*, days: int = 30) -> list[dict[str, Any]]:
    today = timezone.now().date()
    start = today - timedelta(days=days - 1)
    qs = (
        Tenant.objects.filter(created_at__date__gte=start)
        .extra(select={"day": "DATE(created_at)"})  # noqa: S610 — uso intencional
        .values("day")
        .annotate(n=Count("id"))
        .order_by("day")
    )
    # Constrói série densa (preenche dias zero)
    bucket = {row["day"]: row["n"] for row in qs}
    out = []
    cur = start
    while cur <= today:
        out.append({"date": cur.isoformat(), "count": bucket.get(cur, 0)})
        cur += timedelta(days=1)
    return out


def mrr_by_plan() -> list[dict[str, Any]]:
    """Quebra do MRR por plano."""
    qs = (
        Subscription.objects.filter(status=Subscription.Status.ACTIVE)
        .values("plan__code", "plan__name", "plan__price_monthly")
        .annotate(n=Count("id"))
        .order_by("-plan__price_monthly")
    )
    out = []
    for r in qs:
        price = r["plan__price_monthly"] or Decimal("0")
        out.append({
            "plan_code": r["plan__code"],
            "plan_name": r["plan__name"],
            "subscribers": r["n"],
            "mrr": _to_float(price * r["n"]),
        })
    return out


def recent_revenue(*, days: int = 30) -> Decimal:
    """Receita real (faturas pagas) nos últimos N dias."""
    start = timezone.now() - timedelta(days=days)
    return Decimal(
        Invoice.objects.filter(status=Invoice.Status.PAID, paid_at__gte=start)
        .aggregate(t=Sum("amount"))["t"] or 0
    )


# ---------------------------------------------------------------------------
def saas_summary() -> dict[str, Any]:
    return {
        "mrr": _to_float(mrr()),
        "arr": _to_float(arr()),
        "total_tenants": total_tenants(),
        "active_subscribers": active_subscribers(),
        "trialing": trialing_count(),
        "expired_trials": expired_trials_count(),
        "churn_30d_pct": round(churn_pct_last_30d(), 2),
        "trial_to_paid_pct": round(trial_to_paid_conversion(), 2),
        "mau_30d": mau_last_30d(),
        "revenue_30d": _to_float(recent_revenue()),
        "mrr_by_plan": mrr_by_plan(),
        "signups_30d": signups_by_day(days=30),
    }


def tenants_list(*, search: str = "", limit: int = 50) -> list[dict[str, Any]]:
    qs = Tenant.objects.all().order_by("-created_at")
    if search:
        qs = qs.filter(name__icontains=search) | qs.filter(slug__icontains=search)
    out = []
    for t in qs[:limit]:
        sub = Subscription.objects.filter(tenant=t).select_related("plan").first()
        out.append({
            "id": t.id,
            "public_id": str(t.public_id),
            "name": t.name,
            "slug": t.slug,
            "cnpj": t.cnpj,
            "status": t.status,
            "trial_ends_at": t.trial_ends_at.isoformat() if t.trial_ends_at else None,
            "created_at": t.created_at.isoformat(),
            "subscription": {
                "plan": sub.plan.code if sub else None,
                "status": sub.status if sub else None,
                "current_period_end": (
                    sub.current_period_end.isoformat()
                    if sub and sub.current_period_end else None
                ),
            } if sub else None,
            "users_count": t.memberships.filter(is_active=True).count(),
        })
    return out


def tenant_detail(tenant_id: int) -> dict[str, Any]:
    t = Tenant.objects.get(id=tenant_id)
    sub = Subscription.objects.filter(tenant=t).select_related("plan").first()
    return {
        "tenant": {
            "id": t.id,
            "public_id": str(t.public_id),
            "name": t.name,
            "slug": t.slug,
            "cnpj": t.cnpj,
            "status": t.status,
            "trial_ends_at": t.trial_ends_at.isoformat() if t.trial_ends_at else None,
            "created_at": t.created_at.isoformat(),
        },
        "subscription": {
            "plan": sub.plan.code,
            "status": sub.status,
            "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
            "current_period_end": (
                sub.current_period_end.isoformat() if sub.current_period_end else None
            ),
            "cancel_at_period_end": sub.cancel_at_period_end,
        } if sub else None,
        "users": [
            {
                "id": m.user.id,
                "email": m.user.email,
                "full_name": m.user.full_name,
                "role": m.role,
                "last_login": m.user.last_login.isoformat() if m.user.last_login else None,
            }
            for m in t.memberships.filter(is_active=True).select_related("user")
        ],
        "invoices_count": Invoice.objects.filter(tenant=t).count(),
        "invoices_total": _to_float(
            Invoice.objects.filter(tenant=t, status=Invoice.Status.PAID)
            .aggregate(t=Sum("amount"))["t"]
        ),
    }
