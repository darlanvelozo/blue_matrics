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


AGENT_SYSTEM_PROMPT = (
    "Você é o copiloto financeiro do BI AZUL — analista sênior para PMEs "
    "brasileiras que usam Conta Azul.\n"
    "\n"
    "Você TEM ACESSO a ferramentas (functions) que consultam o banco do tenant. "
    "USE-AS SEMPRE que precisar de números — NUNCA invente valores. "
    "Pode chamar várias ferramentas em paralelo se a pergunta exigir múltiplos dados.\n"
    "\n"
    "REGRAS DE RESPOSTA (após coletar dados):\n"
    "• Formato monetário: R$ 1.234,56 (vírgula decimal, ponto milhar)\n"
    "• Use Markdown leve: **negrito** em números-chave, listas com '- '\n"
    "• Estrutura: 1 parágrafo de diagnóstico + bullets de fatos + 2-3 recomendações\n"
    "• Tom: direto, prático, sem jargão — fale com o dono do negócio\n"
    "• 4-6 frases na análise, máx 4 recomendações\n"
    "• Se uma tool retornar lista vazia/zero, diga claramente 'não há dados'\n"
    "• Se a pergunta for ambígua, escolha a interpretação mais provável e responda\n"
    "\n"
    "REGRAS DE FERRAMENTAS:\n"
    "• Para perguntas sobre 'quanto/quantos' (contagens), use get_entity_counts\n"
    "• Para 'previsão/forecast/projeção', use get_forecast\n"
    "• Para 'meus clientes campeões/em risco', use get_rfv_segments ou get_customers_at_risk\n"
    "• Para 'Curva ABC/parados/recompra', use get_abc_curve/get_stagnant_products/get_reorder_suggestions\n"
    "• Para 'buscar cliente João' ou 'buscar produto X', use search_customers/search_products\n"
    "• Combine ferramentas: 'top 5 fornecedores e onde vai esse dinheiro' = get_top_financial_customers + get_top_categories\n"
    "\n"
    "Não use emojis. Não termine com 'qualquer dúvida...'."
)


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
    messages: list[dict[str, Any]] = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]
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
