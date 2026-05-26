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
# Regras adicionais (FinancialEntry — tenants com fluxo direto no financeiro)
# ---------------------------------------------------------------------------
EXPENSE_CATEGORY_DOMINANCE_PCT = 25.0  # uma cat. acima disso é destaque
SUPPLIER_CONCENTRATION_PCT = 25.0
CASH_IN_TREND_THRESHOLD = 15.0  # % de variação para alertar tendência
UPCOMING_PAYABLES_ALERT_FACTOR = 0.30  # alerta se >30% do mês passado


def rule_top_expense_category(tenant_id: int, *, ref: date) -> list[dict]:
    """Destaca a categoria de despesa com maior valor no mês passado."""
    last = _last_month(ref)
    rows = kpis.top_categories(tenant_id, last, direction="payable", limit=5)
    if not rows:
        return []
    # IMPORTANTE: divisor é o TOTAL DE DESPESAS do mês (não a soma das top 5).
    # Antes (bug): sum(r['total'] for r in rows) — inflava o %, ex: Leasing
    # virava 44,8% (sobre top 5 R$ 224k) em vez de 37,9% (sobre total R$ 265k).
    from apps.analytics import kpis_v2
    total = kpis_v2.cash_out_period(tenant_id, last)
    top = rows[0]
    pct = (top["total"] / total * 100) if total else 0
    if top["total"] == 0:
        return []
    severity = "warning" if pct >= EXPENSE_CATEGORY_DOMINANCE_PCT else "info"
    return [{
        "kind": "top_expense_category",
        "severity": severity,
        "title": f"\"{top['name']}\" lidera as despesas de {_month_pt(last.start)}",
        "narrative": (
            f"Em {_month_pt(last.start)} você gastou {_brl(top['total'])} com "
            f"\"{top['name']}\", o equivalente a {_pct(pct)} do total de despesas "
            f"do mês ({_brl(total)}). Revise se há espaço para renegociar ou "
            f"consolidar fornecedores nessa categoria."
        ),
        "data": {
            "category": top["name"],
            "category_id": top.get("category_id"),
            "total": top["total"],
            "month_total": total,
            "share_pct": pct,
            "transactions": top.get("count"),
            "top5": rows,
        },
        "period_start": last.start,
        "period_end": last.end,
    }]


def rule_top_revenue_category(tenant_id: int, *, ref: date) -> list[dict]:
    """Destaca a categoria de receita com maior valor no mês passado."""
    last = _last_month(ref)
    rows = kpis.top_categories(tenant_id, last, direction="receivable", limit=5)
    if not rows or rows[0]["total"] == 0:
        return []
    # Divisor: TOTAL de receitas do mês (não soma das top 5)
    from apps.analytics import kpis_v2
    total = kpis_v2.cash_in_period(tenant_id, last)
    top = rows[0]
    pct = (top["total"] / total * 100) if total else 0
    return [{
        "kind": "top_revenue_category",
        "severity": "success",
        "title": f"\"{top['name']}\" é a maior fonte de receita em {_month_pt(last.start)}",
        "narrative": (
            f"Em {_month_pt(last.start)} \"{top['name']}\" trouxe {_brl(top['total'])} "
            f"— {_pct(pct)} do que entrou no mês ({_brl(total)}). "
            "Vale aprofundar a análise de margem e expansão dessa linha."
        ),
        "data": {
            "category": top["name"],
            "category_id": top.get("category_id"),
            "total": top["total"],
            "share_pct": pct,
            "transactions": top.get("count"),
            "top5": rows,
        },
        "period_start": last.start,
        "period_end": last.end,
    }]


def rule_upcoming_payables(tenant_id: int, *, ref: date) -> list[dict]:
    """Alerta sobre o total a pagar nos próximos 30 dias."""
    upcoming = kpis.upcoming_payables(tenant_id, days=30, ref_date=ref)
    if upcoming["count"] == 0 or upcoming["total"] == 0:
        return []
    # Comparativo: total pago no mês passado (proxy de fluxo médio)
    last = _last_month(ref)
    last_out = float(kpis.cash_out(tenant_id, last))
    ratio = upcoming["total"] / last_out if last_out > 0 else None
    severity = "info"
    extra = ""
    if ratio is not None and ratio > 1.2:
        severity = "warning"
        extra = (
            f" Isso representa {ratio*100:.0f}% das despesas pagas em "
            f"{_month_pt(last.start)} ({_brl(last_out)})."
        )
    return [{
        "kind": "upcoming_payables",
        "severity": severity,
        "title": (
            f"{upcoming['count']} compromissos somando "
            f"{_brl(upcoming['total'])} vencem nos próximos 30 dias"
        ),
        "narrative": (
            f"Você tem {upcoming['count']} contas a pagar com vencimento até "
            f"{(ref + timedelta(days=30)).strftime('%d/%m/%Y')}, somando "
            f"{_brl(upcoming['total'])}.{extra} Priorize a régua e garanta caixa."
        ),
        "data": {
            "total": upcoming["total"],
            "count": upcoming["count"],
            "comparison_pct": (ratio * 100) if ratio is not None else None,
            "ref_month_cash_out": last_out,
        },
        "period_start": ref,
        "period_end": ref + timedelta(days=30),
    }]


def rule_supplier_concentration(tenant_id: int, *, ref: date) -> list[dict]:
    """Destaca fornecedor que concentra grande parte do pagamento mensal."""
    last = _last_month(ref)
    rows = kpis.top_financial_customers(tenant_id, last, direction="payable", limit=5)
    if not rows or rows[0]["total"] == 0:
        return []
    total = float(kpis.cash_out(tenant_id, last))
    top = rows[0]
    if total == 0:
        return []
    pct = top["total"] / total * 100
    if pct < SUPPLIER_CONCENTRATION_PCT:
        return []
    return [{
        "kind": "supplier_concentration",
        "severity": "warning",
        "title": f"\"{top['name']}\" representa {_pct(pct)} dos pagamentos",
        "narrative": (
            f"Em {_month_pt(last.start)} você pagou {_brl(top['total'])} a "
            f"\"{top['name']}\" — {_pct(pct)} de todas as saídas do mês. "
            "Concentração alta em um fornecedor aumenta risco operacional. "
            "Considere diversificar ou renegociar."
        ),
        "data": {
            "supplier": top["name"],
            "customer_id": top.get("customer_id"),
            "total": top["total"],
            "share_pct": pct,
            "transactions": top.get("count"),
            "top5": rows,
        },
        "period_start": last.start,
        "period_end": last.end,
    }]


def rule_cash_in_trend(tenant_id: int, *, ref: date) -> list[dict]:
    """Compara recebimentos do mês passado com o anterior. Sinaliza tendência."""
    last = _last_month(ref)
    prev = _prev_month_of(last)
    last_in = float(kpis.cash_in(tenant_id, last))
    prev_in = float(kpis.cash_in(tenant_id, prev))
    if last_in == 0 or prev_in == 0:
        return []
    change = (last_in - prev_in) / prev_in * 100
    if abs(change) < CASH_IN_TREND_THRESHOLD:
        return []
    if change < 0:
        severity = "warning" if change > -25 else "critical"
        title = f"Recebimentos caíram {_pct(change)} em {_month_pt(last.start)}"
        narrative = (
            f"Você recebeu {_brl(last_in)} em {_month_pt(last.start)}, "
            f"{_pct(change)} a menos que em {_month_pt(prev.start)} ({_brl(prev_in)}). "
            "Verifique a régua de cobrança e o pipeline de vendas."
        )
    else:
        severity = "success"
        title = f"Recebimentos subiram {_pct(change)} em {_month_pt(last.start)}"
        narrative = (
            f"Excelente — {_month_pt(last.start)} fechou em {_brl(last_in)}, "
            f"{_pct(change)} acima de {_month_pt(prev.start)} ({_brl(prev_in)})."
        )
    return [{
        "kind": "cash_in_trend",
        "severity": severity,
        "title": title,
        "narrative": narrative,
        "data": {"current": last_in, "previous": prev_in, "change_pct": change},
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
    # Financeiro (FinancialEntry)
    rule_top_expense_category,
    rule_top_revenue_category,
    rule_upcoming_payables,
    rule_supplier_concentration,
    rule_cash_in_trend,
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
