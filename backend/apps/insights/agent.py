"""
Agente IA com function calling.

Loop:
1. Envia pergunta + tools schema para OpenAI
2. LLM decide chamar 0+ tools (em paralelo)
3. Backend executa cada tool com tenant_id injetado
4. Resultados voltam para LLM
5. LLM ou chama mais tools OU produz resposta final

Diferente do modo intent-based, NÃO precisamos prever todas as perguntas.
O LLM escolhe ferramentas dinamicamente. Limite de iterações pra evitar loops.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from django.conf import settings

from . import tools as tools_module

logger = logging.getLogger(__name__)


def build_agent_system_prompt() -> str:
    """Gera o system prompt do agente com a data atual injetada (anchor temporal)."""
    from django.utils import timezone as _tz

    today = _tz.localdate()
    return (
        "Você é o copiloto financeiro do BI AZUL — analista sênior para PMEs "
        "brasileiras que usam Conta Azul.\n"
        "\n"
        f"⏰ DATA DE HOJE: {today.isoformat()} (use SEMPRE essa data como referência "
        "ao interpretar 'recente', 'mês passado', 'ano passado', 'futuro', etc.).\n"
        "\n"
        "🛠 FERRAMENTAS: você TEM acesso a tools que consultam o banco real do "
        "cliente. USE-AS SEMPRE que precisar de números — NUNCA invente valores, "
        "nunca extrapole de um período pra outro. Pode chamar várias em paralelo.\n"
        "\n"
        "🚫 REGRAS ANTI-INVENÇÃO (CRÍTICAS):\n"
        "• Se uma tool retornar 'has_data: false' OU valores zerados, RESPONDA "
        "  EXPLICITAMENTE 'não há dados sincronizados para esse período'. "
        "  NÃO use valores de outro período como substituto.\n"
        "• Se a pergunta menciona uma data FUTURA (após a data de hoje), diga "
        "  'essa data ainda não chegou' e ofereça previsão via get_forecast.\n"
        "• Se a tool não conseguir extrair o dado pedido, diga isso. NÃO chute.\n"
        "• Sempre cite o intervalo de datas usado ao responder (ex: 'em "
        "  dezembro/2025' OU 'nos últimos 30 dias (de X a Y)').\n"
        "\n"
        "📅 ROTEAMENTO POR TIPO DE PERÍODO:\n"
        "• 'Últimos N dias/meses' (relativo a hoje) → get_kpis_period(days=N)\n"
        "• 'Mês/trimestre/ano específico' (ex: 'dezembro 2025', 'Q3 2024', '2025') "
        "  → get_kpis_for_period(start_date, end_date) com datas ISO 8601 exatas\n"
        "• 'Comparar mês A vs mês B' → 2× get_kpis_for_period em paralelo\n"
        "• 'Mês com maior/menor faturamento' → get_cashflow_monthly(months=12+) "
        "  e analisar; OU se for sobre um ano específico, get_cashflow_monthly "
        "  retorna os 12 meses recentes.\n"
        "• 'Previsão/projeção futura' → get_forecast (NUNCA confundir com histórico).\n"
        "\n"
        "🎯 ACONSELHAMENTO: para 'o que devo fazer?', 'onde investir?', 'como "
        "melhorar?' → SEMPRE chame ferramentas relevantes ANTES de responder. "
        "Ex: 'onde investir 10k?' → get_overdue_summary + get_reorder_suggestions "
        "+ get_cash_balance ANTES de aconselhar.\n"
        "\n"
        "🗣 FORMATO DA RESPOSTA:\n"
        "• Moeda: R$ 1.234,56 (vírgula decimal, ponto milhar)\n"
        "• Markdown leve: **negrito** em números-chave, listas com '- '\n"
        "• Estrutura: 1 parágrafo de diagnóstico + bullets de fatos + 2-3 recomendações\n"
        "• Tom: direto, prático, sem jargão — fale com o dono do negócio\n"
        "• 4-6 frases na análise, máx 4 recomendações\n"
        "• Se a pergunta for ambígua, escolha a interpretação mais provável e responda\n"
        "\n"
        "📦 OUTRAS TOOLS POR CASO DE USO:\n"
        "• Contagens ('quantos X tenho') → get_entity_counts\n"
        "• Clientes campeões/em risco → get_rfv_segments, get_customers_at_risk, "
        "  get_ltv, get_repurchase_rate\n"
        "• Top N receita/despesa → get_top_categories, get_top_financial_customers\n"
        "• Saldo atual + burn → get_cash_balance\n"
        "• A pagar/receber em aberto vencendo → get_upcoming, get_overdue_summary\n"
        "• DRE estruturada → get_dre\n"
        "• Saúde financeira → get_health_score\n"
        "• Produtos parados/Curva ABC/recompra → get_stagnant_products, "
        "  get_abc_curve, get_reorder_suggestions\n"
        "• Busca por nome → search_customers, search_products, "
        "  search_financial_entries, search_sales\n"
        "\n"
        "Não use emojis no texto da resposta. Não termine com 'qualquer dúvida...'."
    )


# Pré-computado no import pra evitar timezone calls toda chamada.
# Atualizado por turno na chamada de run_agent — ver build_agent_system_prompt().
AGENT_SYSTEM_PROMPT = build_agent_system_prompt()


@dataclass
class AgentResult:
    answer: str
    tools_called: list[dict] = field(default_factory=list)
    iterations: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    error: str | None = None


def _openai_call(messages: list[dict], tools: list[dict], temperature: float = 0.2) -> dict:
    """Chamada OpenAI com tool use habilitado, com retry exponencial básico."""
    payload = {
        "model": settings.OPENAI_MODEL,
        "temperature": temperature,
        "max_tokens": 1500,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
    }
    url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    delays = [0, 1.5, 4.0]
    last_exc: Exception | None = None
    for attempt, delay in enumerate(delays):
        if delay:
            time.sleep(delay)
        try:
            with httpx.Client(timeout=60.0) as http:
                resp = http.post(url, json=payload, headers=headers)
            if resp.status_code == 429:
                body = resp.json() if "json" in resp.headers.get("content-type", "") else {}
                if body.get("error", {}).get("type") == "insufficient_quota":
                    raise QuotaExceededError(body["error"].get("message", "Sem créditos"))
                last_exc = httpx.HTTPStatusError(
                    "429 rate limited", request=resp.request, response=resp,
                )
                continue
            if 500 <= resp.status_code < 600:
                last_exc = httpx.HTTPStatusError(
                    f"OpenAI {resp.status_code}", request=resp.request, response=resp,
                )
                continue
            resp.raise_for_status()
            return resp.json()
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_exc = e
            continue
    if last_exc:
        raise last_exc
    raise RuntimeError("OpenAI: falha sem detalhe")


class QuotaExceededError(Exception):
    pass


def run_agent(
    tenant_id: int,
    question: str,
    history: list[dict] | None = None,
    *,
    max_iterations: int = 5,
) -> AgentResult:
    """
    Executa o loop agentic. Retorna `AgentResult` com texto final + telemetria.
    Erros (quota/network) propagam — a view trata e cai em modo demo.
    """
    history = history or []
    # Recalcula o prompt a cada chamada para que a data de hoje fique atual
    # mesmo quando o processo gunicorn ficou de pé entre dias.
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": build_agent_system_prompt()},
    ]
    # Histórico anterior (max 6 últimas trocas)
    for h in history[-6:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": str(h["content"])[:2000]})
    messages.append({"role": "user", "content": question})

    tools_schema = tools_module.get_openai_tools_schema()
    tools_called: list[dict] = []
    tokens_in = 0
    tokens_out = 0
    iterations = 0

    for i in range(max_iterations):
        iterations = i + 1
        response = _openai_call(messages, tools_schema)
        usage = response.get("usage", {})
        tokens_in += usage.get("prompt_tokens", 0)
        tokens_out += usage.get("completion_tokens", 0)

        msg = response["choices"][0]["message"]
        finish_reason = response["choices"][0].get("finish_reason")

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            # LLM produziu resposta final
            return AgentResult(
                answer=(msg.get("content") or "").strip(),
                tools_called=tools_called,
                iterations=iterations,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )

        # Adiciona a mensagem do assistente com tool_calls (mantendo formato)
        messages.append({
            "role": "assistant",
            "content": msg.get("content"),
            "tool_calls": tool_calls,
        })

        # Executa cada tool
        for tc in tool_calls:
            name = tc["function"]["name"]
            raw_args = tc["function"].get("arguments") or "{}"
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
            result = tools_module.execute_tool(tenant_id, name, args)
            tools_called.append({"name": name, "args": args, "ok": "error" not in result})
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": json.dumps(result, ensure_ascii=False, default=str)[:8000],
            })

        if finish_reason == "length":
            # Limite de tokens — sair
            break

    return AgentResult(
        answer=(
            "Cheguei ao limite de iterações analisando seus dados. "
            "Tente refinar a pergunta ou divida em partes menores."
        ),
        tools_called=tools_called,
        iterations=iterations,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        error="max_iterations",
    )
