"""
Adapter de LLM para enriquecer insights.

Recebe um insight candidato (gerado por regra) + um snapshot dos KPIs do
tenant e devolve uma narrativa enriquecida + recomendações práticas.

Provider configurável via settings:
- INSIGHT_LLM_PROVIDER = "openai" | "anthropic" | "disabled"
- OPENAI_API_KEY / OPENAI_MODEL / OPENAI_BASE_URL
- ANTHROPIC_API_KEY / ANTHROPIC_MODEL

A chamada de rede é via httpx (já no projeto). Falhas não propagam: se a
LLM não responder ou houver erro de parsing, o insight original (regras)
é retornado sem alteração.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class LLMNotConfigured(Exception):
    """Provider configurado como disabled, ou chave/configuração ausente."""


@dataclass
class EnrichmentResult:
    """Resultado da chamada LLM. `enriched` é False quando caímos no fallback."""

    title: str
    narrative: str
    recommendations: list[str]
    enriched: bool


# ---------------------------------------------------------------------------
SYSTEM_PROMPT_PT_BR = (
    "Você é um analista financeiro sênior em uma plataforma de BI para PMEs "
    "brasileiras. Sua função é transformar um insight bruto (gerado por regra "
    "determinística) em uma narrativa clara, em português brasileiro, com "
    "tom profissional e direto, voltada para o dono do negócio.\n"
    "Você recebe: (a) o insight candidato (kind, title, narrative, data) e "
    "(b) um snapshot agregado do tenant (KPIs principais).\n"
    "Você devolve um JSON válido com 3 campos:\n"
    "  - title (string, máx 90 chars): manchete clara e específica.\n"
    "  - narrative (string, 2-4 frases): análise contextualizada usando os "
    "números — sem repetir literalmente o insight bruto.\n"
    "  - recommendations (array de 2-3 strings): ações práticas e acionáveis.\n"
    "Use os valores monetários no formato brasileiro (R$ 1.234,56). "
    "Não invente dados que não estejam no payload. "
    "Não use emojis. Resposta SOMENTE com o JSON, sem markdown."
)


def _format_user_prompt(insight: dict, kpis_snapshot: dict) -> str:
    return (
        "## Insight candidato\n"
        f"```json\n{json.dumps(insight, ensure_ascii=False, indent=2, default=str)}\n```\n\n"
        "## Snapshot do tenant (últimos meses)\n"
        f"```json\n{json.dumps(kpis_snapshot, ensure_ascii=False, indent=2, default=str)}\n```\n\n"
        "Devolva o JSON final."
    )


# ---------------------------------------------------------------------------
def _provider() -> str:
    return (getattr(settings, "INSIGHT_LLM_PROVIDER", "disabled") or "disabled").lower()


def is_enabled() -> bool:
    p = _provider()
    if p == "openai":
        return bool(getattr(settings, "OPENAI_API_KEY", ""))
    if p == "anthropic":
        return bool(getattr(settings, "ANTHROPIC_API_KEY", ""))
    return False


# ---------------------------------------------------------------------------
def _call_openai(insight: dict, snapshot: dict) -> dict[str, Any]:
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise LLMNotConfigured("OPENAI_API_KEY ausente")
    url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.OPENAI_MODEL,
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_PT_BR},
            {"role": "user", "content": _format_user_prompt(insight, snapshot)},
        ],
    }
    with httpx.Client(timeout=45.0) as http:
        resp = http.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        body = resp.json()
    content = body["choices"][0]["message"]["content"]
    return json.loads(content)


def _call_anthropic(insight: dict, snapshot: dict) -> dict[str, Any]:
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise LLMNotConfigured("ANTHROPIC_API_KEY ausente")
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": settings.ANTHROPIC_MODEL,
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT_PT_BR,
        "messages": [
            {"role": "user", "content": _format_user_prompt(insight, snapshot)},
        ],
    }
    with httpx.Client(timeout=45.0) as http:
        resp = http.post(
            url,
            json=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        body = resp.json()
    text = body["content"][0]["text"]
    # Anthropic não força JSON; pegamos o primeiro bloco { … } encontrado
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Resposta sem JSON identificável")
    return json.loads(text[start : end + 1])


# ---------------------------------------------------------------------------
def enrich(insight: dict, kpis_snapshot: dict) -> EnrichmentResult:
    """Enriquece um insight via LLM. Cai em fallback se LLM falhar."""
    provider = _provider()
    if not is_enabled():
        return EnrichmentResult(
            title=insight.get("title", ""),
            narrative=insight.get("narrative", ""),
            recommendations=[],
            enriched=False,
        )

    try:
        if provider == "openai":
            data = _call_openai(insight, kpis_snapshot)
        elif provider == "anthropic":
            data = _call_anthropic(insight, kpis_snapshot)
        else:
            raise LLMNotConfigured(f"provider desconhecido: {provider}")

        title = str(data.get("title") or insight.get("title", ""))[:200]
        narrative = str(data.get("narrative") or insight.get("narrative", ""))
        recs_raw = data.get("recommendations") or []
        recommendations = [
            str(x) for x in recs_raw if isinstance(x, (str, int, float))
        ][:5]
        return EnrichmentResult(
            title=title,
            narrative=narrative,
            recommendations=recommendations,
            enriched=True,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("LLM enrich falhou (%s): %s", provider, e)
        return EnrichmentResult(
            title=insight.get("title", ""),
            narrative=insight.get("narrative", ""),
            recommendations=[],
            enriched=False,
        )


# ---------------------------------------------------------------------------
def build_kpis_snapshot(tenant_id: int) -> dict[str, Any]:
    """Snapshot compacto e legível dos KPIs do tenant para alimentar a LLM."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.analytics import kpis as kpi_mod
    from apps.analytics.periods import Period

    today = timezone.now().date()
    last_30 = Period(start=today - timedelta(days=30), end=today)
    last_90 = Period(start=today - timedelta(days=90), end=today)
    last_12m = Period(start=today - timedelta(days=365), end=today)

    return {
        "today": today.isoformat(),
        "last_30d": {
            "cash_in": float(kpi_mod.cash_in(tenant_id, last_30)),
            "cash_out": float(kpi_mod.cash_out(tenant_id, last_30)),
            "net_profit": float(kpi_mod.net_profit(tenant_id, last_30)),
            "revenue_sale": float(kpi_mod.revenue(tenant_id, last_30)),
            "num_sales": kpi_mod.num_sales(tenant_id, last_30),
        },
        "last_90d": {
            "cash_in": float(kpi_mod.cash_in(tenant_id, last_90)),
            "cash_out": float(kpi_mod.cash_out(tenant_id, last_90)),
            "net_profit": float(kpi_mod.net_profit(tenant_id, last_90)),
        },
        "last_12m": {
            "cash_in": float(kpi_mod.cash_in(tenant_id, last_12m)),
            "cash_out": float(kpi_mod.cash_out(tenant_id, last_12m)),
            "net_profit": float(kpi_mod.net_profit(tenant_id, last_12m)),
            "top_revenue_categories": kpi_mod.top_categories(
                tenant_id, last_12m, direction="receivable", limit=5,
            ),
            "top_expense_categories": kpi_mod.top_categories(
                tenant_id, last_12m, direction="payable", limit=5,
            ),
            "top_suppliers": kpi_mod.top_financial_customers(
                tenant_id, last_12m, direction="payable", limit=5,
            ),
        },
        "today_balance": {
            "overdue_rate_pct": kpi_mod.overdue_rate(tenant_id),
            "overdue_receivables": kpi_mod.overdue_receivables_summary(tenant_id),
            "overdue_payables": kpi_mod.overdue_payables_summary(tenant_id),
            "upcoming_payables_30d": kpi_mod.upcoming_payables(tenant_id, days=30),
            "upcoming_payables_60d": kpi_mod.upcoming_payables(tenant_id, days=60),
            "upcoming_receivables_30d": kpi_mod.upcoming_receivables(tenant_id, days=30),
        },
    }
