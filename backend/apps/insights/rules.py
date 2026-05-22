"""
Engine de regras determinísticas para gerar insights.

Cada regra recebe `tenant_id` + referência de data e retorna uma lista de
dicts no formato do Insight (kind, severity, title, narrative, data, period).

Regras puras — não tocam no banco. O `generate_insights_for_tenant()` é quem
materializa em Insight (upsert idempotente por kind+period).
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from apps.analytics import kpis
from apps.analytics.periods import Period
from apps.sync.models import Customer, FinancialEntry, Sale

# Tolerâncias / thresholds — podem virar configuráveis por tenant no futuro
REVENUE_DROP_THRESHOLD = -10.0  # %
REVENUE_SURGE_THRESHOLD = 15.0  # %
EXPENSE_SURGE_THRESHOLD = 20.0  # %
TICKET_DROP_THRESHOLD = -10.0  # %
OVERDUE_HIGH_THRESHOLD = 10.0  # %
INACTIVE_CUSTOMER_DAYS = 90  # cliente que comprava e parou
MIN_PURCHASES_TO_BE_REGULAR = 3


def _brl(v: float | Decimal) -> str:
    """Formata BRL: 12345.6 → 'R$ 12.345,60'."""
    s = f"{float(v):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v: float) -> str:
    s = f"{abs(v):.1f}"
    return s.replace(".", ",") + "%"


# ---------------------------------------------------------------------------
def rule_revenue_change(tenant_id: int, *, ref: date) -> list[dict]:
    """Compara faturamento do mês anterior com o mês retrasado."""
    last = _last_month(ref)
    prev = _prev_month_of(last)
    last_rev = float(kpis.revenue(tenant_id, last))
    prev_rev = float(kpis.revenue(tenant_id, prev))
    if last_rev == 0 or prev_rev == 0:
        return []
    change = (last_rev - prev_rev) / prev_rev * 100

    if change <= REVENUE_DROP_THRESHOLD:
        return [{
            "kind": "revenue_drop",
            "severity": "warning" if change > -25 else "critical",
            "title": f"Faturamento caiu {_pct(change)} em {_month_pt(last.start)}",
            "narrative": (
                f"Em {_month_pt(last.start)} você faturou {_brl(last_rev)} — "
                f"{_pct(change)} a menos que em {_month_pt(prev.start)} ({_brl(prev_rev)}). "
                "Vale investigar quais clientes ou produtos performaram pior."
            ),
            "data": {"current": last_rev, "previous": prev_rev, "change_pct": change},
            "period_start": last.start,
            "period_end": last.end,
        }]
    if change >= REVENUE_SURGE_THRESHOLD:
        return [{
            "kind": "revenue_surge",
            "severity": "success",
            "title": f"Faturamento subiu {_pct(change)} em {_month_pt(last.start)}",
            "narrative": (
                f"Excelente! {_month_pt(last.start)} fechou em {_brl(last_rev)}, "
                f"{_pct(change)} acima de {_month_pt(prev.start)} ({_brl(prev_rev)})."
            ),
            "data": {"current": last_rev, "previous": prev_rev, "change_pct": change},
            "period_start": last.start,
            "period_end": last.end,
        }]
    return []


def rule_expense_surge(tenant_id: int, *, ref: date) -> list[dict]:
    last = _last_month(ref)
    prev = _prev_month_of(last)
    last_out = float(kpis.cash_out(tenant_id, last))
    prev_out = float(kpis.cash_out(tenant_id, prev))
    if last_out == 0 or prev_out == 0:
        return []
    change = (last_out - prev_out) / prev_out * 100
    if change < EXPENSE_SURGE_THRESHOLD:
        return []
    return [{
        "kind": "expense_surge",
        "severity": "warning",
        "title": f"Despesas subiram {_pct(change)} em {_month_pt(last.start)}",
        "narrative": (
            f"Suas saídas em {_month_pt(last.start)} totalizaram {_brl(last_out)}, "
            f"{_pct(change)} acima de {_month_pt(prev.start)} ({_brl(prev_out)}). "
            "Confira as categorias com maior variação no Financeiro."
        ),
        "data": {"current": last_out, "previous": prev_out, "change_pct": change},
        "period_start": last.start,
        "period_end": last.end,
    }]


def rule_ticket_drop(tenant_id: int, *, ref: date) -> list[dict]:
    last = _last_month(ref)
    prev = _prev_month_of(last)
    last_ticket = float(kpis.avg_ticket(tenant_id, last))
    prev_ticket = float(kpis.avg_ticket(tenant_id, prev))
    if last_ticket == 0 or prev_ticket == 0:
        return []
    change = (last_ticket - prev_ticket) / prev_ticket * 100
    if change > TICKET_DROP_THRESHOLD:
        return []
    return [{
        "kind": "ticket_drop",
        "severity": "warning",
        "title": f"Ticket médio caiu {_pct(change)}",
        "narrative": (
            f"O ticket médio de {_month_pt(last.start)} foi {_brl(last_ticket)}, "
            f"{_pct(change)} menor que {_month_pt(prev.start)} ({_brl(prev_ticket)}). "
            "Pode indicar promoções, mudança de mix ou perda de clientes mais valiosos."
        ),
        "data": {"current": last_ticket, "previous": prev_ticket, "change_pct": change},
        "period_start": last.start,
        "period_end": last.end,
    }]


def rule_overdue_high(tenant_id: int, *, ref: date) -> list[dict]:
    rate = kpis.overdue_rate(tenant_id, ref_date=ref)
    if rate < OVERDUE_HIGH_THRESHOLD:
        return []
    return [{
        "kind": "overdue_high",
        "severity": "critical" if rate > 25 else "warning",
        "title": f"Inadimplência em {_pct(rate)}",
        "narrative": (
            f"Você tem {_pct(rate)} do total a receber em atraso. "
            "Considere acionar a régua de cobrança e revisar prazos com novos clientes."
        ),
        "data": {"rate": rate},
        "period_start": ref,
        "period_end": ref,
    }]


def rule_top_customer_last_month(tenant_id: int, *, ref: date) -> list[dict]:
    last = _last_month(ref)
    top = kpis.top_customers(tenant_id, last, limit=1)
    if not top:
        return []
    c = top[0]
    return [{
        "kind": "top_customer",
        "severity": "info",
        "title": f"{c['name']} foi seu cliente top em {_month_pt(last.start)}",
        "narrative": (
            f"Em {_month_pt(last.start)}, {c['name']} comprou {_brl(c['total'])} "
            f"em {int(c['sales'])} venda(s) — o cliente que mais movimentou no período. "
            "Vale manter um relacionamento próximo."
        ),
        "data": c,
        "period_start": last.start,
        "period_end": last.end,
    }]


def rule_top_product_last_month(tenant_id: int, *, ref: date) -> list[dict]:
    last = _last_month(ref)
    top = kpis.top_products(tenant_id, last, limit=1)
    if not top:
        return []
    p = top[0]
    return [{
        "kind": "top_product",
        "severity": "info",
        "title": f"{p['name']} liderou as vendas em {_month_pt(last.start)}",
        "narrative": (
            f"{p['name']} faturou {_brl(p['total'])} em {_month_pt(last.start)}, "
            "ficando no topo do ranking de produtos. "
            "Garanta que esteja em destaque e com estoque saudável."
        ),
        "data": p,
        "period_start": last.start,
        "period_end": last.end,
    }]


def rule_inactive_customers(tenant_id: int, *, ref: date) -> list[dict]:
    """Clientes que tinham >=3 compras nos últimos 12m mas não compram há 90d."""
    cutoff = ref - timedelta(days=INACTIVE_CUSTOMER_DAYS)
    one_year_ago = ref - timedelta(days=365)

    # Tudo via ORM com unsafe_objects (rule é chamado fora de request)
    from django.db.models import Count, Max
    qs = (
        Customer.unsafe_objects.filter(
            tenant_id=tenant_id,
            sales__status=Sale.Status.CLOSED,
            sales__issued_at__date__gte=one_year_ago,
        )
        .annotate(n=Count("sales"), last=Max("sales__issued_at"))
        .filter(n__gte=MIN_PURCHASES_TO_BE_REGULAR)
        .filter(last__date__lt=cutoff)
        .order_by("-n")[:5]
    )
    inactive = list(qs.values("id", "name", "n", "last"))
    if not inactive:
        return []

    names = ", ".join(c["name"] for c in inactive[:3])
    extra = f" e mais {len(inactive) - 3}" if len(inactive) > 3 else ""
    return [{
        "kind": "inactive_customer",
        "severity": "warning",
        "title": f"{len(inactive)} clientes ativos pararam de comprar",
        "narrative": (
            f"{names}{extra} costumavam comprar regularmente mas não fizeram "
            f"nenhuma compra nos últimos {INACTIVE_CUSTOMER_DAYS} dias. "
            "Vale um contato comercial para entender o que aconteceu."
        ),
        "data": {
            "count": len(inactive),
            "customers": [
                {"id": c["id"], "name": c["name"], "purchases_12m": c["n"]}
                for c in inactive
            ],
        },
        "period_start": cutoff,
        "period_end": ref,
    }]


def rule_cash_negative(tenant_id: int, *, ref: date) -> list[dict]:
    last = _last_month(ref)
    net = float(kpis.net_profit(tenant_id, last))
    ci = float(kpis.cash_in(tenant_id, last))
    co = float(kpis.cash_out(tenant_id, last))
    if net >= 0 or ci == 0:
        return []
    return [{
        "kind": "cash_negative",
        "severity": "critical",
        "title": f"Caixa negativo em {_month_pt(last.start)}",
        "narrative": (
            f"Em {_month_pt(last.start)} saíram {_brl(co)} contra "
            f"{_brl(ci)} de entradas — saldo de {_brl(net)}. "
            "Reveja despesas variáveis e priorize a régua de cobrança."
        ),
        "data": {"net": net, "cash_in": ci, "cash_out": co},
        "period_start": last.start,
        "period_end": last.end,
    }]


# ---------------------------------------------------------------------------
ALL_RULES = [
    rule_revenue_change,
    rule_expense_surge,
    rule_ticket_drop,
    rule_overdue_high,
    rule_top_customer_last_month,
    rule_top_product_last_month,
    rule_inactive_customers,
    rule_cash_negative,
]


def run_all_rules(tenant_id: int, *, ref: date | None = None) -> list[dict]:
    """Executa todas as regras e devolve insights candidatos."""
    import logging
    log = logging.getLogger(__name__)
    ref = ref or timezone.now().date()
    out: list[dict] = []
    for rule in ALL_RULES:
        try:
            out.extend(rule(tenant_id, ref=ref))
        except Exception as e:  # noqa: BLE001 — regra ruim não derruba as outras
            log.warning("regra %s falhou: %s", rule.__name__, e)
            continue
    return out


# ---------------------------------------------------------------------------
# Persistência (upsert idempotente por kind+period)
# ---------------------------------------------------------------------------
def materialize_insights(tenant_id: int, candidates: Iterable[dict]) -> tuple[int, int]:
    """Persiste insights candidatos. Retorna (created, updated)."""
    from .models import Insight

    created, updated = 0, 0
    for c in candidates:
        obj, was_created = Insight.unsafe_objects.update_or_create(
            tenant_id=tenant_id,
            kind=c["kind"],
            period_start=c.get("period_start"),
            period_end=c.get("period_end"),
            defaults={
                "severity": c.get("severity", "info"),
                "title": c["title"],
                "narrative": c["narrative"],
                "data": c.get("data", {}),
                "generated_by": c.get("generated_by", "rules"),
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1
    return created, updated


def generate_insights_for_tenant(tenant_id: int, *, ref: date | None = None) -> dict[str, Any]:
    """Roda todas as regras e persiste os insights. Retorna estatísticas."""
    candidates = run_all_rules(tenant_id, ref=ref)
    created, updated = materialize_insights(tenant_id, candidates)
    return {
        "candidates": len(candidates),
        "created": created,
        "updated": updated,
    }


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
PT_MONTHS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _month_pt(d: date) -> str:
    return f"{PT_MONTHS[d.month - 1]}/{d.year}"


def _last_month(ref: date) -> Period:
    first_this = ref.replace(day=1)
    last_prev = first_this - timedelta(days=1)
    return Period(start=last_prev.replace(day=1), end=last_prev)


def _prev_month_of(p: Period) -> Period:
    start = p.start - relativedelta(months=1)
    end = (start + relativedelta(months=1)) - timedelta(days=1)
    return Period(start=start, end=end)


# Re-export tipos relevantes ao reusar de fora
__all__ = [
    "ALL_RULES",
    "FinancialEntry",  # mantém import disponível
    "generate_insights_for_tenant",
    "materialize_insights",
    "run_all_rules",
]
