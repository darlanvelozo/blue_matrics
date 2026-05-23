"""
Endpoints de IA: chat livre + análise sob demanda (dashboard dinâmico).

Estrutura:
- `AskView` (POST /api/ai/ask) — chat. Recebe {question, history}, retorna {answer, used_data}.
- `AnalyzeView` (POST /api/ai/analyze) — análise + dashboard. Recebe {question}, retorna
  um "blueprint" JSON com KPIs, tabelas e charts que o frontend renderiza.

Quando `INSIGHT_LLM_PROVIDER=disabled` (sem chave configurada), entra em modo
**demo inteligente**: a engine classifica a intenção da pergunta com regras
simples (regex/keywords) e devolve uma resposta usando dados reais do tenant.
Quando ativa, monta um snapshot rico + chama LLM (OpenAI/Anthropic).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import timedelta
from typing import Any

import httpx
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics import kpis
from apps.analytics.periods import Period
from apps.tenants.utils import get_request_tenant

from . import llm

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers de formatação
# ---------------------------------------------------------------------------
def _brl(v: float | int) -> str:
    s = f"{float(v or 0):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v: float | int) -> str:
    return f"{float(v or 0):.1f}%".replace(".", ",")


def _period_last_n_days(days: int) -> Period:
    today = timezone.now().date()
    return Period(start=today - timedelta(days=days), end=today)


# ---------------------------------------------------------------------------
# Classificação de intenção (modo demo + ajuda à LLM)
# ---------------------------------------------------------------------------
# Ordem importa: a primeira intent cujo padrão casar vence.
# Intents mais específicas vêm antes (top_suppliers antes de top_expenses).
INTENT_KEYWORDS: list[tuple[str, list[str]]] = [
    # Contagens básicas — "quantos produtos tenho", "quantos clientes"
    ("entity_count", [
        r"quantos?\s+(produtos?|clientes?|fornecedor\w*|vendas?|lan[çc]amentos?)",
        r"qual\s+(o\s+)?(total|n[úu]mero)\s+de\s+(produtos?|clientes?)",
        r"\btotal\s+de\s+(produtos?|clientes?|vendas?)",
    ]),
    # Diferenciar "preciso recomprar produto" (reorder) ANTES de
    # "taxa de recompra" (repurchase)
    ("reorder", [
        r"(recompr\w*|repor|comprar.*estoque).*(produto|estoque|item)",
        r"(produto|estoque|item).*(recompr\w*|repor|comprar)",
        r"preciso.*comprar.*(produto|estoque)",
        r"sugest[ãa]o.*compra",
        r"\brup?tura\b|ruptura.*estoque",
        r"\bo que.*comprar\b",
    ]),
    ("rfv_segments", [
        r"\brfv\b|champ[ie]o\w*|fi[ée]is|segment\w*.*cliente|cliente.*segment\w*",
        r"clientes? (vip|champ[ie]ões?|champions|fi[eé]is)",
        r"quem.*meus.*melhores.*clientes?",
    ]),
    ("customers_at_risk", [
        r"cliente.*(risco|em risco|inativo|sumi|parou.*comprar)",
        r"quem.*parou.*(comprar|pagar)",
    ]),
    ("abc_products", [
        r"\babc\b|curva.*abc|pareto",
        r"produtos.*(80|principais|representam).*receita",
    ]),
    ("stagnant_products", [
        r"produtos?.*parad\w*|estoque parado|produtos? sem.*venda",
        r"o que.*est[oá]\s*sem girar",
    ]),
    ("reorder", [
        r"recompr\w*.*produto|preciso.*comprar.*produto|repor.*estoque",
        r"o que.*comprar.*estoque|sugest[ãa]o.*compra",
        r"\brup?tura\b|ruptura.*estoque",
    ]),
    ("forecast_revenue", [
        r"previs[ãa]o.*(receita|fatur)",
        r"projet[ãa]?\w+\s.*(receita|fatur)",
        r"quanto.*vou.*(receb|fatur)",
        r"tendência.*(receita|fatur|venda)",
    ]),
    ("ltv", [
        r"\bltv\b|lifetime value|valor.*vit[áa]l",
        r"quanto.*vale.*um.*cliente",
        r"ticket m[ée]dio.*vida",
    ]),
    ("repurchase", [
        r"recompr\w*|retor\w*|volt\w+.*comprar",
        r"taxa.*reten[çc][ãa]o|reten[çc][ãa]o.*cliente",
    ]),
    ("forecast_cash", [
        r"previs[ãa]o.*caixa|forecast.*caixa",
        r"caixa.*negativ\w*|caixa.*ficar",
        r"projet\w+.*caixa",
    ]),
    ("top_suppliers", [
        r"fornecedor\w*",
        r"para quem.*pag",
    ]),
    ("top_customers", [
        r"\bcliente\w*\b.*(maior|top|mais|que.*pag)",
        r"quem.*(paga|comprou).*mais",
    ]),
    ("upcoming", [
        r"pr[óo]xim\w*",
        r"vencer\w*|vencendo",
        r"\ba pagar\b|\ba receber\b",
        r"forecast|previs[ãa]o",
    ]),
    ("overdue", [
        r"atras\w*|atrasad\w*|vencid\w*|inadimpl\w*",
    ]),
    ("cashflow", [
        r"fluxo\s+de\s+caixa",
        r"\b(cash.?flow)\b",
        r"entrada\s+e\s+sa[íi]da",
        r"caixa.*ms?e\w*",
    ]),
    ("top_expenses", [
        r"despes\w*|gast\w*|sa[íi]da\w*|pagament\w*",
        r"onde.*gast",
    ]),
    ("top_revenues", [
        r"receit\w*|entrada\w*|recebiment\w*|fatur\w*",
    ]),
    ("summary", [
        r"resumo|geral|panorama|saúde|saude|negócio|negocio",
        r"como (est|vai)",
    ]),
]


def classify_intent(text: str) -> str:
    """Heurística simples para detectar intenção. Retorna a primeira categoria
    (lista ordenada) cujo set de palavras-chave casa com o texto, ou 'summary'
    como fallback.
    """
    text_lc = text.lower()
    for intent, patterns in INTENT_KEYWORDS:
        if any(re.search(p, text_lc) for p in patterns):
            return intent
    return "summary"


def detect_window_days(text: str) -> int:
    """Detecta janela temporal do texto. Default 30 dias."""
    m = re.search(r"(\d+)\s*(dia|d[ií]as)", text.lower())
    if m:
        return min(int(m.group(1)), 365)
    if re.search(r"\b(ano|12.?meses|últimos.?12)\b", text.lower()):
        return 365
    if re.search(r"\b(trimestre|90.?dias|3.?meses)\b", text.lower()):
        return 90
    if re.search(r"\b(semestre|180.?dias|6.?meses)\b", text.lower()):
        return 180
    return 30


# ---------------------------------------------------------------------------
# Engine de análise (executa queries reais a partir da intenção)
# ---------------------------------------------------------------------------
def run_analysis(tenant_id: int, intent: str, *, days: int, limit: int = 10) -> dict[str, Any]:
    """Roda KPIs reais e retorna um blueprint estruturado para o frontend.

    Schema do retorno:
    {
      title: str, summary: str, intent: str, period_days: int,
      kpis: [{label, value, format}],
      tables: [{title, headers, rows}],
      charts: [{title, type, data}],
    }
    """
    period = _period_last_n_days(days)
    blueprint: dict[str, Any] = {
        "title": "",
        "summary": "",
        "intent": intent,
        "period_days": days,
        "kpis": [],
        "tables": [],
        "charts": [],
    }

    if intent == "top_expenses":
        rows = kpis.top_categories(tenant_id, period, direction="payable", limit=limit)
        total = sum(r["total"] for r in rows)
        blueprint["title"] = f"Maiores despesas — últimos {days} dias"
        blueprint["summary"] = (
            f"Top {len(rows)} categorias de despesa somam {_brl(total)} "
            f"nos últimos {days} dias."
        )
        blueprint["kpis"] = [
            {"label": "Total Top N", "value": total, "format": "currency"},
            {"label": "Categorias", "value": len(rows), "format": "number"},
            {"label": "Janela", "value": days, "format": "number", "suffix": " dias"},
        ]
        blueprint["tables"] = [
            {
                "title": "Categorias de despesa",
                "headers": ["#", "Categoria", "Valor", "Transações"],
                "rows": [
                    [i + 1, r["name"], r["total"], r["count"]] for i, r in enumerate(rows)
                ],
                "value_columns": [2],
            }
        ]
        blueprint["charts"] = [
            {
                "title": "Distribuição",
                "type": "bar",
                "data": [{"label": r["name"], "value": r["total"]} for r in rows[:8]],
            }
        ]

    elif intent == "top_revenues":
        rows = kpis.top_categories(tenant_id, period, direction="receivable", limit=limit)
        total = sum(r["total"] for r in rows)
        blueprint["title"] = f"Maiores receitas — últimos {days} dias"
        blueprint["summary"] = (
            f"Top {len(rows)} categorias de receita somam {_brl(total)} "
            f"nos últimos {days} dias."
        )
        blueprint["kpis"] = [
            {"label": "Total Top N", "value": total, "format": "currency"},
            {"label": "Categorias", "value": len(rows), "format": "number"},
        ]
        blueprint["tables"] = [
            {
                "title": "Categorias de receita",
                "headers": ["#", "Categoria", "Valor", "Transações"],
                "rows": [
                    [i + 1, r["name"], r["total"], r["count"]] for i, r in enumerate(rows)
                ],
                "value_columns": [2],
            }
        ]
        blueprint["charts"] = [
            {
                "title": "Distribuição",
                "type": "bar",
                "data": [{"label": r["name"], "value": r["total"]} for r in rows[:8]],
            }
        ]

    elif intent == "top_suppliers":
        rows = kpis.top_financial_customers(tenant_id, period, direction="payable", limit=limit)
        total = sum(r["total"] for r in rows)
        blueprint["title"] = f"Maiores fornecedores — últimos {days} dias"
        blueprint["summary"] = (
            f"Top {len(rows)} fornecedores somam {_brl(total)} em pagamentos nos últimos {days} dias."
        )
        blueprint["kpis"] = [
            {"label": "Total Top N", "value": total, "format": "currency"},
            {"label": "Fornecedores", "value": len(rows), "format": "number"},
        ]
        blueprint["tables"] = [
            {
                "title": "Fornecedores",
                "headers": ["#", "Fornecedor", "Valor pago", "Transações"],
                "rows": [
                    [i + 1, r["name"], r["total"], r["count"]] for i, r in enumerate(rows)
                ],
                "value_columns": [2],
            }
        ]

    elif intent == "top_customers":
        rows = kpis.top_financial_customers(tenant_id, period, direction="receivable", limit=limit)
        total = sum(r["total"] for r in rows)
        blueprint["title"] = f"Maiores clientes — últimos {days} dias"
        blueprint["summary"] = (
            f"Top {len(rows)} clientes somam {_brl(total)} em recebimentos nos últimos {days} dias."
        )
        blueprint["kpis"] = [
            {"label": "Total Top N", "value": total, "format": "currency"},
            {"label": "Clientes", "value": len(rows), "format": "number"},
        ]
        blueprint["tables"] = [
            {
                "title": "Clientes",
                "headers": ["#", "Cliente", "Valor recebido", "Transações"],
                "rows": [
                    [i + 1, r["name"], r["total"], r["count"]] for i, r in enumerate(rows)
                ],
                "value_columns": [2],
            }
        ]

    elif intent == "cashflow":
        # janela em meses ~ days/30
        cf = kpis.cashflow_by_month(tenant_id, period)
        total_in = sum(m["in"] for m in cf)
        total_out = sum(m["out"] for m in cf)
        net = total_in - total_out
        blueprint["title"] = f"Fluxo de caixa — últimos {days} dias"
        blueprint["summary"] = (
            f"Nos últimos {days} dias entraram {_brl(total_in)} e saíram {_brl(total_out)} "
            f"— saldo líquido de {_brl(net)}."
        )
        blueprint["kpis"] = [
            {"label": "Entradas", "value": total_in, "format": "currency"},
            {"label": "Saídas", "value": total_out, "format": "currency"},
            {"label": "Saldo líquido", "value": net, "format": "currency"},
        ]
        blueprint["charts"] = [
            {
                "title": "Fluxo mensal",
                "type": "cashflow",
                "data": cf,
            }
        ]

    elif intent == "upcoming":
        up_r = kpis.upcoming_receivables(tenant_id, days=days)
        up_p = kpis.upcoming_payables(tenant_id, days=days)
        blueprint["title"] = f"Previsão — próximos {days} dias"
        blueprint["summary"] = (
            f"Você tem {up_r['count']} recebíveis ({_brl(up_r['total'])}) e "
            f"{up_p['count']} contas a pagar ({_brl(up_p['total'])}) "
            f"vencendo nos próximos {days} dias."
        )
        blueprint["kpis"] = [
            {"label": "A receber", "value": up_r["total"], "format": "currency"},
            {"label": "A pagar", "value": up_p["total"], "format": "currency"},
            {
                "label": "Saldo projetado",
                "value": up_r["total"] - up_p["total"],
                "format": "currency",
            },
        ]

    elif intent == "entity_count":
        from apps.sync.models import Customer, FinancialEntry, Product, Sale, Salesperson, Category
        from django.db.models import F, ExpressionWrapper, DecimalField, Sum

        counts = {
            "Produtos": Product.unsafe_objects.filter(tenant_id=tenant_id).count(),
            "Produtos ativos": Product.unsafe_objects.filter(tenant_id=tenant_id, is_active=True).count(),
            "Produtos com estoque": Product.unsafe_objects.filter(tenant_id=tenant_id, stock_balance__gt=0).count(),
            "Clientes/Fornecedores": Customer.unsafe_objects.filter(tenant_id=tenant_id).count(),
            "Vendas formais": Sale.unsafe_objects.filter(tenant_id=tenant_id).count(),
            "Lançamentos financeiros": FinancialEntry.unsafe_objects.filter(tenant_id=tenant_id).count(),
            "Categorias": Category.unsafe_objects.filter(tenant_id=tenant_id).count(),
            "Vendedores": Salesperson.unsafe_objects.filter(tenant_id=tenant_id).count(),
        }
        stock_agg = Product.unsafe_objects.filter(
            tenant_id=tenant_id, stock_balance__gt=0, cost__gt=0,
        ).aggregate(
            qty=Sum("stock_balance"),
            value=Sum(
                ExpressionWrapper(
                    F("stock_balance") * F("cost"),
                    output_field=DecimalField(max_digits=20, decimal_places=2),
                ),
            ),
        )
        blueprint["title"] = "Resumo da base sincronizada"
        blueprint["summary"] = (
            f"Você tem **{counts['Produtos']} produtos** ({counts['Produtos com estoque']} com estoque), "
            f"**{counts['Clientes/Fornecedores']} pessoas** cadastradas e "
            f"**{counts['Lançamentos financeiros']:,} lançamentos financeiros** sincronizados."
        )
        blueprint["kpis"] = [
            {"label": label, "value": count, "format": "number"}
            for label, count in counts.items()
        ]
        blueprint["tables"] = [{
            "title": "Resumo de estoque",
            "headers": ["Métrica", "Valor"],
            "rows": [
                ["Unidades em estoque", float(stock_agg.get("qty") or 0)],
                ["Valor em estoque (R$)", float(stock_agg.get("value") or 0)],
            ],
            "value_columns": [],
        }]

    elif intent == "rfv_segments":
        from apps.analytics import kpis_v2 as kv2
        info = kv2.rfv_segments(tenant_id)
        counts = info.get("counts", {})
        blueprint["title"] = "Segmentação RFV de clientes"
        blueprint["summary"] = (
            f"Total de {info.get('total', 0)} clientes únicos com compras. "
            f"Champions: {counts.get('champions', 0)} · "
            f"High value: {counts.get('high_value', 0)} · "
            f"Loyal: {counts.get('loyal', 0)} · "
            f"At risk: {counts.get('at_risk', 0)} · "
            f"Lost: {counts.get('lost', 0)} · "
            f"New: {counts.get('new', 0)}."
        )
        blueprint["kpis"] = [
            {"label": k.replace("_", " ").title(), "value": v, "format": "number"}
            for k, v in counts.items()
        ]
        # Top 5 champions
        champs = info.get("segments", {}).get("champions", [])
        if champs:
            blueprint["tables"] = [{
                "title": "Champions (top 5)",
                "headers": ["Cliente", "Compras", "Total"],
                "rows": [[c["name"], c["count"], c["total"]] for c in champs[:5]],
                "value_columns": [2],
            }]

    elif intent == "customers_at_risk":
        from apps.analytics import kpis_v2 as kv2
        at_risk = kv2.customer_at_risk(tenant_id, inactive_days=60)
        blueprint["title"] = "Clientes em risco"
        blueprint["summary"] = (
            f"{len(at_risk)} cliente(s) com histórico recorrente que não compram há 60+ dias. "
            f"Total já comprado por esses: {_brl(sum(c['total_purchased'] for c in at_risk))}."
        )
        blueprint["kpis"] = [
            {"label": "Clientes em risco", "value": len(at_risk), "format": "number"},
            {
                "label": "Valor histórico em risco",
                "value": sum(c["total_purchased"] for c in at_risk),
                "format": "currency",
            },
        ]
        if at_risk:
            blueprint["tables"] = [{
                "title": "Top 10 em risco",
                "headers": ["Cliente", "Total comprado", "Compras", "Dias inativo"],
                "rows": [
                    [c["name"], c["total_purchased"], c["purchases"], c["days_inactive"]]
                    for c in at_risk[:10]
                ],
                "value_columns": [1],
            }]

    elif intent == "abc_products":
        from apps.analytics import kpis_v2 as kv2
        abc = kv2.abc_curve(tenant_id, by="sales") if any(
            kv2.abc_curve(tenant_id, by="sales").get("rows") or []
        ) else kv2.abc_curve(tenant_id, by="stock_value")
        counts = abc.get("counts", {})
        blueprint["title"] = f"Curva ABC de produtos (por {abc.get('by', 'valor')})"
        blueprint["summary"] = (
            f"Classe A (80% do valor): {counts.get('A', 0)} produtos · "
            f"B (15%): {counts.get('B', 0)} · "
            f"C (5%): {counts.get('C', 0)}. "
            f"Total analisado: {_brl(abc.get('total', 0))}."
        )
        blueprint["kpis"] = [
            {"label": "Classe A", "value": counts.get("A", 0), "format": "number"},
            {"label": "Classe B", "value": counts.get("B", 0), "format": "number"},
            {"label": "Classe C", "value": counts.get("C", 0), "format": "number"},
        ]
        if abc.get("rows"):
            top = abc["rows"][:15]
            blueprint["tables"] = [{
                "title": "Top 15 produtos",
                "headers": ["#", "Produto", "Classe", "Valor", "% acum"],
                "rows": [
                    [i + 1, r["name"], r["class"], r["value"], r["cumulative_pct"]]
                    for i, r in enumerate(top)
                ],
                "value_columns": [3],
            }]

    elif intent == "stagnant_products":
        from apps.analytics import kpis_v2 as kv2
        rows = kv2.stagnant_products(tenant_id, min_stock=1)
        total_value = sum(r["stuck_value"] for r in rows)
        blueprint["title"] = "Produtos parados em estoque"
        blueprint["summary"] = (
            f"{len(rows)} produtos com estoque mas SEM vendas registradas. "
            f"Capital travado: {_brl(total_value)}."
        )
        blueprint["kpis"] = [
            {"label": "Produtos parados", "value": len(rows), "format": "number"},
            {"label": "Valor travado", "value": total_value, "format": "currency"},
        ]
        if rows:
            blueprint["tables"] = [{
                "title": "Top 15 produtos parados (por valor)",
                "headers": ["SKU", "Produto", "Estoque", "Custo unit.", "Valor parado"],
                "rows": [
                    [r["sku"], r["name"], r["stock"], r["cost"], r["stuck_value"]]
                    for r in sorted(rows, key=lambda x: -x["stuck_value"])[:15]
                ],
                "value_columns": [3, 4],
            }]

    elif intent == "reorder":
        from apps.analytics import kpis_v2 as kv2
        ro = kv2.reorder_suggestions(tenant_id, lookback_days=180)
        suggestions = ro["suggestions"]
        total_cost = sum(s["reorder_cost_estimate"] for s in suggestions)
        blueprint["title"] = "Sugestões de recompra"
        blueprint["summary"] = (
            f"{len(suggestions)} produto(s) abaixo de {ro['target_coverage_days']} dias de cobertura. "
            f"Custo estimado de reposição: {_brl(total_cost)}."
        ) if suggestions else (
            "Nenhum produto precisa de reposição urgente — todos com cobertura > 30 dias "
            "(ou sem vendas suficientes para calcular)."
        )
        blueprint["kpis"] = [
            {"label": "Produtos a repor", "value": len(suggestions), "format": "number"},
            {"label": "Custo estimado", "value": total_cost, "format": "currency"},
        ]
        if suggestions:
            blueprint["tables"] = [{
                "title": "Top 15 prioridades",
                "headers": ["SKU", "Produto", "Estoque", "Cobertura (dias)", "Qtd. sugerida", "Custo"],
                "rows": [
                    [s["sku"], s["name"], s["stock"], s["coverage_days"], s["suggested_qty"], s["reorder_cost_estimate"]]
                    for s in suggestions[:15]
                ],
                "value_columns": [5],
            }]

    elif intent == "forecast_revenue":
        from apps.analytics import kpis_v2 as kv2
        fc = kv2.revenue_forecast(tenant_id, days_ahead=days)
        blueprint["title"] = f"Previsão de receita — próximos {days} dias"
        confidence_pt = {"high": "alta", "medium": "média", "low": "baixa"}.get(fc["confidence"], "—")
        blueprint["summary"] = (
            f"Previsão (regressão linear sobre {len(fc.get('last_months', []))} meses): "
            f"{_brl(fc['forecast_total'])} em {days} dias. "
            f"Confiança {confidence_pt}. Tendência mensal: {fc['trend_pct_monthly']:+.1f}%."
        )
        blueprint["kpis"] = [
            {"label": "Receita prevista", "value": fc["forecast_total"], "format": "currency"},
            {"label": "Média mensal histórica", "value": fc["baseline_avg_monthly"], "format": "currency"},
            {"label": "Tendência/mês", "value": fc["trend_pct_monthly"], "format": "percent"},
        ]
        if fc.get("last_months"):
            blueprint["tables"] = [{
                "title": "Histórico mensal",
                "headers": ["Mês", "Receita"],
                "rows": [[m["month"], m["revenue"]] for m in fc["last_months"]],
                "value_columns": [1],
            }]

    elif intent == "forecast_cash":
        from apps.analytics import kpis_v2 as kv2
        fc = kv2.cash_forecast(tenant_id, days=days)
        risk_str = "EM RISCO" if fc["at_risk"] else "ok"
        blueprint["title"] = f"Projeção de caixa — {days} dias"
        blueprint["summary"] = (
            f"Saldo atual: {_brl(fc['current_balance'])}. "
            f"Entradas previstas: {_brl(fc['expected_in'])}. "
            f"Saídas: {_brl(fc['expected_out'])}. "
            f"Saldo projetado: {_brl(fc['projected_balance'])} ({risk_str})."
        )
        blueprint["kpis"] = [
            {"label": "Saldo hoje", "value": fc["current_balance"], "format": "currency"},
            {"label": "Entradas", "value": fc["expected_in"], "format": "currency"},
            {"label": "Saídas", "value": fc["expected_out"], "format": "currency"},
            {"label": "Saldo projetado", "value": fc["projected_balance"], "format": "currency"},
        ]

    elif intent == "ltv":
        from apps.analytics import kpis_v2 as kv2
        info = kv2.ltv_estimate(tenant_id, months_back=12)
        blueprint["title"] = "LTV — Lifetime Value médio"
        blueprint["summary"] = (
            f"LTV médio estimado em {_brl(info['ltv_avg'])} considerando "
            f"{info['unique_customers']} clientes únicos e {_brl(info['total_revenue'])} "
            f"em receita nos últimos 12 meses."
        )
        blueprint["kpis"] = [
            {"label": "LTV médio", "value": info["ltv_avg"], "format": "currency"},
            {"label": "Clientes únicos", "value": info["unique_customers"], "format": "number"},
            {"label": "Receita 12m", "value": info["total_revenue"], "format": "currency"},
        ]

    elif intent == "repurchase":
        from apps.analytics import kpis_v2 as kv2
        info = kv2.repurchase_rate(tenant_id, window_days=90)
        blueprint["title"] = "Taxa de recompra"
        blueprint["summary"] = (
            f"Nos últimos {info['window_days']} dias: {info['repurchased']} "
            f"de {info['total_customers']} clientes voltaram a comprar — "
            f"taxa de recompra {info['rate_pct']:.1f}%."
        )
        blueprint["kpis"] = [
            {"label": "Taxa de recompra", "value": info["rate_pct"], "format": "percent"},
            {"label": "Clientes que voltaram", "value": info["repurchased"], "format": "number"},
            {"label": "Total clientes ativos", "value": info["total_customers"], "format": "number"},
        ]

    elif intent == "overdue":
        o_r = kpis.overdue_receivables_summary(tenant_id)
        o_p = kpis.overdue_payables_summary(tenant_id)
        rate = kpis.overdue_rate(tenant_id)
        blueprint["title"] = "Inadimplência atual"
        blueprint["summary"] = (
            f"Você tem {_brl(o_r['total'])} em recebíveis vencidos "
            f"({o_r['count']} lançamentos) e {_brl(o_p['total'])} em contas vencidas "
            f"({o_p['count']} lançamentos). Taxa global de inadimplência: {_pct(rate)}."
        )
        blueprint["kpis"] = [
            {"label": "Recebíveis vencidos", "value": o_r["total"], "format": "currency"},
            {"label": "Faturas vencidas", "value": o_p["total"], "format": "currency"},
            {"label": "Inadimplência", "value": rate, "format": "percent"},
        ]

    else:  # summary
        ci = float(kpis.cash_in(tenant_id, period))
        co = float(kpis.cash_out(tenant_id, period))
        net = ci - co
        top_exp = kpis.top_categories(tenant_id, period, direction="payable", limit=3)
        top_rev = kpis.top_categories(tenant_id, period, direction="receivable", limit=3)
        up_p = kpis.upcoming_payables(tenant_id, days=30)
        blueprint["title"] = f"Panorama financeiro — últimos {days} dias"
        blueprint["summary"] = (
            f"Em {days} dias entraram {_brl(ci)} e saíram {_brl(co)}. "
            f"Saldo: {_brl(net)}. "
            f"Próximos 30 dias: {up_p['count']} compromissos ({_brl(up_p['total'])})."
        )
        blueprint["kpis"] = [
            {"label": "Recebimentos", "value": ci, "format": "currency"},
            {"label": "Pagamentos", "value": co, "format": "currency"},
            {"label": "Saldo", "value": net, "format": "currency"},
            {"label": "A pagar 30d", "value": up_p["total"], "format": "currency"},
        ]
        if top_rev:
            blueprint["tables"].append({
                "title": "Top categorias de receita",
                "headers": ["Categoria", "Valor"],
                "rows": [[r["name"], r["total"]] for r in top_rev],
                "value_columns": [1],
            })
        if top_exp:
            blueprint["tables"].append({
                "title": "Top categorias de despesa",
                "headers": ["Categoria", "Valor"],
                "rows": [[r["name"], r["total"]] for r in top_exp],
                "value_columns": [1],
            })

    return blueprint


# ---------------------------------------------------------------------------
# Chamadas LLM (chat livre)
# ---------------------------------------------------------------------------
CHAT_SYSTEM_PROMPT = (
    "Você é o copiloto financeiro do BI AZUL, analista sênior para PMEs "
    "brasileiras que usam a Conta Azul ERP.\n"
    "\n"
    "REGRAS (siga sempre):\n"
    "• Use APENAS números do snapshot — nunca invente valores.\n"
    "• Formato monetário: R$ 1.234,56 (vírgula decimal, ponto milhar).\n"
    "• Tom: direto, prático, sem jargão técnico. Trate o usuário como dono do negócio.\n"
    "• Estrutura: parágrafo de diagnóstico → bullets de fatos → bullets de recomendações.\n"
    "• Use Markdown leve: **negrito** para números-chave, listas com '- '.\n"
    "• Se a pergunta exigir dado fora do snapshot, diga claramente 'não tenho esse dado'.\n"
    "• Quando relevante, contraste valores (mês atual vs anterior, % de variação).\n"
    "• Limite: 4-6 frases na análise, máx 4 recomendações.\n"
    "\n"
    "Não use emojis nem termos de marketing ('incrível', 'fantástico'). Não termine "
    "com convite para perguntas adicionais."
)


class LLMRateLimited(Exception):
    """Provedor LLM retornou 429."""


class LLMQuotaExceeded(Exception):
    """Conta sem créditos (insufficient_quota)."""


# ---------------------------------------------------------------------------
# Sugestões de follow-up contextuais (após cada resposta)
# ---------------------------------------------------------------------------
_FOLLOWUP_BY_INTENT = {
    "entity_count": [
        "Quanto tenho em estoque?",
        "Quais são meus produtos parados?",
        "Quem são meus clientes campeões?",
    ],
    "summary": [
        "Quais foram minhas 10 maiores despesas no último trimestre?",
        "Como está minha inadimplência?",
        "Tenho saldo pra pagar tudo nos próximos 30 dias?",
    ],
    "top_expenses": [
        "Qual fornecedor está concentrando esses pagamentos?",
        "Onde posso cortar despesas?",
        "Comparado ao mês anterior, as despesas subiram ou caíram?",
    ],
    "top_revenues": [
        "Quem são meus principais clientes?",
        "Qual categoria está crescendo mais?",
        "Quanto faturei nos últimos 90 dias?",
    ],
    "top_suppliers": [
        "Quanto pago em juros e impostos?",
        "Quais fornecedores tenho prazo a vencer?",
        "Como reduzir custo com fornecedores?",
    ],
    "top_customers": [
        "Quais clientes estão inadimplentes?",
        "Tenho clientes que pararam de comprar?",
        "Top 10 clientes por valor",
    ],
    "cashflow": [
        "Meu caixa vai ficar negativo?",
        "Qual o saldo projetado para 30 dias?",
        "Tendência de receita vs despesa",
    ],
    "upcoming": [
        "Como reduzir contas a pagar próximos 30 dias?",
        "Tenho recebimentos previstos?",
        "Vou ter caixa pra honrar tudo?",
    ],
    "overdue": [
        "Quanto perco com inadimplência?",
        "Quais clientes estão em risco?",
        "Como melhorar minha cobrança?",
    ],
    "rfv_segments": [
        "Quem são meus clientes campeões?",
        "Quais clientes estão em risco de churn?",
        "Quanto vale meu cliente médio (LTV)?",
    ],
    "customers_at_risk": [
        "Como recuperar clientes inativos?",
        "Qual o LTV desses clientes em risco?",
        "Estratégias de reativação",
    ],
    "abc_products": [
        "Quais produtos estão parados?",
        "Devo recomprar algum produto?",
        "Margem dos produtos classe A",
    ],
    "stagnant_products": [
        "Quanto tenho de capital travado?",
        "Como liquidar produtos parados?",
        "Quais produtos têm maior giro?",
    ],
    "reorder": [
        "Tenho caixa pra fazer essa compra?",
        "Qual fornecedor é mais barato?",
        "Qual a margem desses produtos?",
    ],
    "forecast_revenue": [
        "E o caixa, vai ficar negativo?",
        "Quanto preciso vender pra bater a meta?",
        "Tendência das despesas",
    ],
    "forecast_cash": [
        "Quanto tenho a receber 30 dias?",
        "Quanto tenho a pagar 30 dias?",
        "Como melhorar meu fluxo de caixa?",
    ],
    "ltv": [
        "Quem são meus clientes mais valiosos?",
        "Qual a taxa de recompra?",
        "Como aumentar o LTV?",
    ],
    "repurchase": [
        "Quais clientes pararam de comprar?",
        "Estratégias de retenção",
        "LTV dos meus clientes",
    ],
}


def _build_followups(intent: str, blueprint: dict) -> list[str]:
    """Retorna 3 sugestões contextuais de próxima pergunta."""
    base = _FOLLOWUP_BY_INTENT.get(intent, _FOLLOWUP_BY_INTENT["summary"])
    return list(base[:3])


def _chat_openai(question: str, snapshot: dict, history: list[dict]) -> str:
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise llm.LLMNotConfigured("OPENAI_API_KEY ausente")
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    for h in history[-6:]:  # últimas 6 trocas
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": str(h["content"])[:2000]})
    messages.append({
        "role": "user",
        "content": (
            f"PERGUNTA:\n{question}\n\n"
            f"SNAPSHOT (use APENAS esses números):\n"
            f"{json.dumps(snapshot, ensure_ascii=False, default=str)}"
        ),
    })
    payload = {
        "model": settings.OPENAI_MODEL,
        "temperature": 0.3,
        "max_tokens": 700,
        "messages": messages,
    }
    url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions"

    # Retry com backoff em 429/5xx
    delays = [0, 1.5, 4.0]
    last_exc: Exception | None = None
    for attempt, delay in enumerate(delays):
        if delay:
            import time
            time.sleep(delay)
        try:
            with httpx.Client(timeout=45.0) as http:
                resp = http.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                )
            if resp.status_code == 429:
                err = resp.json().get("error", {}) if resp.headers.get("content-type", "").startswith("application/json") else {}
                if err.get("type") == "insufficient_quota":
                    raise LLMQuotaExceeded(err.get("message", "Sem créditos"))
                last_exc = LLMRateLimited(f"429 (tentativa {attempt + 1})")
                continue
            if 500 <= resp.status_code < 600:
                last_exc = httpx.HTTPStatusError(
                    f"OpenAI {resp.status_code}", request=resp.request, response=resp,
                )
                continue
            resp.raise_for_status()
            body = resp.json()
            return body["choices"][0]["message"]["content"].strip()
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_exc = e
            continue

    if last_exc:
        raise last_exc
    raise RuntimeError("OpenAI: falha sem detalhe após retries")


def _chat_anthropic(question: str, snapshot: dict, history: list[dict]) -> str:
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise llm.LLMNotConfigured("ANTHROPIC_API_KEY ausente")
    messages = []
    for h in history[-6:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": str(h["content"])[:2000]})
    messages.append({
        "role": "user",
        "content": (
            f"## Pergunta\n{question}\n\n"
            f"## Snapshot do tenant\n```json\n"
            f"{json.dumps(snapshot, ensure_ascii=False, indent=2, default=str)}\n```"
        ),
    })
    payload = {
        "model": settings.ANTHROPIC_MODEL,
        "max_tokens": 1024,
        "system": CHAT_SYSTEM_PROMPT,
        "messages": messages,
    }
    with httpx.Client(timeout=60.0) as http:
        resp = http.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        body = resp.json()
    return body["content"][0]["text"].strip()


# ---------------------------------------------------------------------------
# Demo answer (sem LLM): templates a partir do blueprint
# ---------------------------------------------------------------------------
def _demo_answer(question: str, blueprint: dict) -> str:
    lines = [blueprint["summary"]]
    if blueprint.get("kpis"):
        lines.append("")
        lines.append("Resumo:")
        for k in blueprint["kpis"]:
            fmt = k.get("format")
            val = k["value"]
            if fmt == "currency":
                val_s = _brl(val)
            elif fmt == "percent":
                val_s = _pct(val)
            else:
                val_s = str(val) + (k.get("suffix") or "")
            lines.append(f"  • {k['label']}: {val_s}")
    if blueprint.get("tables"):
        for t in blueprint["tables"]:
            lines.append("")
            lines.append(t["title"] + ":")
            value_cols = set(t.get("value_columns") or [])
            for row in t["rows"][:5]:
                cells = []
                for i, cell in enumerate(row):
                    cells.append(_brl(cell) if i in value_cols else str(cell))
                lines.append("  " + " · ".join(cells))
    lines.append("")
    lines.append(
        "(Resposta gerada em modo demo — para análises com IA "
        "configure OPENAI_API_KEY no servidor.)"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
class AskView(APIView):
    """Chat livre. POST {question, history?: [{role, content}]}."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        question = (request.data.get("question") or "").strip()
        if not question:
            return Response(
                {"error": {"code": "invalid", "message": "question é obrigatório."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        history = request.data.get("history") or []
        if not isinstance(history, list):
            history = []

        intent = classify_intent(question)
        days = detect_window_days(question)
        # Blueprint determinístico ainda é gerado — alimenta a UI dinâmica
        # mesmo quando o agente IA não retorna estrutura (resposta livre).
        blueprint = run_analysis(tenant.id, intent, days=days)
        snapshot = llm.build_kpis_snapshot(tenant.id)

        provider = (getattr(settings, "INSIGHT_LLM_PROVIDER", "disabled") or "disabled").lower()
        answer = ""
        used_llm = False
        tools_called: list[dict] = []
        agent_iterations = 0
        llm_error = None

        # Modo PRINCIPAL: agente com function calling (OpenAI)
        if provider == "openai" and settings.OPENAI_API_KEY:
            try:
                from .agent import QuotaExceededError, run_agent

                result = run_agent(tenant.id, question, history)
                answer = result.answer
                tools_called = result.tools_called
                agent_iterations = result.iterations
                used_llm = True
            except QuotaExceededError:
                llm_error = "quota_exceeded"
                logger.warning("Agent: sem créditos OpenAI")
            except Exception as e:  # noqa: BLE001
                logger.warning("Agent falhou, caindo em chat simples: %s", e)
                # Fallback: chat simples com contexto enriquecido
                enriched_context = {
                    **snapshot,
                    "intent_detected": intent,
                    "intent_kpis": {k["label"]: k["value"] for k in blueprint.get("kpis", [])},
                    "intent_summary": blueprint.get("summary", ""),
                }
                try:
                    answer = _chat_openai(question, enriched_context, history)
                    used_llm = True
                    llm_error = "agent_fallback"
                except LLMQuotaExceeded:
                    llm_error = "quota_exceeded"
                except LLMRateLimited:
                    llm_error = "rate_limited"
                except Exception as e2:  # noqa: BLE001
                    logger.warning("Fallback também falhou: %s", e2)
                    llm_error = "unknown"
        elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            # Anthropic ainda usa modo legacy (sem function calling)
            enriched_context = {
                **snapshot,
                "intent_detected": intent,
                "intent_kpis": {k["label"]: k["value"] for k in blueprint.get("kpis", [])},
                "intent_summary": blueprint.get("summary", ""),
            }
            try:
                answer = _chat_anthropic(question, enriched_context, history)
                used_llm = True
            except Exception as e:  # noqa: BLE001
                logger.warning("Anthropic falhou: %s", e)
                llm_error = "unknown"

        if not used_llm:
            answer = _demo_answer(question, blueprint)

        # Sugestões contextuais de follow-up (sempre úteis)
        suggestions = _build_followups(intent, blueprint)

        return Response({
            "answer": answer,
            "intent": intent,
            "blueprint": blueprint,
            "used_llm": used_llm,
            "provider": "openai_agent" if used_llm and provider == "openai" else (provider if used_llm else "demo"),
            "llm_error": llm_error,
            "suggestions": suggestions,
            "agent": {
                "tools_called": tools_called,
                "iterations": agent_iterations,
            } if tools_called else None,
        })


class AnalyzeView(APIView):
    """Análise sob demanda → dashboard JSON. POST {question}."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        question = (request.data.get("question") or "").strip()
        if not question:
            return Response(
                {"error": {"code": "invalid", "message": "question é obrigatório."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        intent = classify_intent(question)
        days = detect_window_days(question)
        # Aumentar limite quando o usuário pediu "top N"
        m = re.search(r"\btop\s*(\d+)\b|\b(\d+)\s*(maiores|principais)\b", question.lower())
        limit = min(int(next(g for g in (m.group(1), m.group(2)) if g)), 50) if m else 10

        blueprint = run_analysis(tenant.id, intent, days=days, limit=limit)
        return Response({
            "blueprint": blueprint,
            "interpretation": {
                "intent": intent,
                "window_days": days,
                "limit": limit,
            },
        })
