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
        blueprint = run_analysis(tenant.id, intent, days=days)
        snapshot = llm.build_kpis_snapshot(tenant.id)

        provider = (getattr(settings, "INSIGHT_LLM_PROVIDER", "disabled") or "disabled").lower()
        answer = ""
        used_llm = False
        try:
            if provider == "openai" and settings.OPENAI_API_KEY:
                answer = _chat_openai(question, snapshot, history)
                used_llm = True
            elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
                answer = _chat_anthropic(question, snapshot, history)
                used_llm = True
        except LLMQuotaExceeded as e:
            logger.warning("LLM sem créditos: %s", e)
            llm_error = "quota_exceeded"
        except LLMRateLimited as e:
            logger.warning("LLM rate limited: %s", e)
            llm_error = "rate_limited"
        except Exception as e:  # noqa: BLE001
            logger.warning("chat LLM falhou (%s): %s", provider, e)
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
            "provider": provider if used_llm else "demo",
            "llm_error": locals().get("llm_error"),
            "suggestions": suggestions,
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
