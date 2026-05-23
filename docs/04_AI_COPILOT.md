# 🤖 Módulo IA — Copiloto Financeiro

> Como funciona a integração com LLM (OpenAI / Anthropic) no BI AZUL,
> endpoints, prompt engineering e modo demo. Atualizado em 2026-05-22.

## Visão geral

O BI AZUL tem **3 superfícies de IA**:

1. **Cards inteligentes na Visão Geral** — gerados por regras determinísticas (`apps/analytics/smart_cards.py`). Não dependem de LLM. Sempre funcionam.
2. **Insights com enriquecimento por IA** — 13 regras em `apps/insights/rules.py` geram candidatos; o LLM (opcional) **reescreve** a narrativa e adiciona `recommendations[]`.
3. **Analista IA conversacional** — chat em `/app/ai` que recebe a pergunta + snapshot do tenant e devolve resposta textual + dashboard dinâmico (KPIs + tabelas + gráficos).

## Provider

Configurado por `INSIGHT_LLM_PROVIDER` no `.env`:

| Valor | Comportamento |
|---|---|
| `disabled` (default) | Modo demo. Tudo funciona com dados reais, mas respostas usam templates determinísticos. |
| `openai` | Usa OpenAI Chat Completions API. Requer `OPENAI_API_KEY`. |
| `anthropic` | Usa Anthropic Messages API. Requer `ANTHROPIC_API_KEY`. |

```bash
INSIGHT_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini          # ou gpt-4o, gpt-4-turbo
OPENAI_BASE_URL=https://api.openai.com/v1   # override para azure/proxy

ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
```

## Arquitetura

```
                    ┌──────────────────────────────┐
                    │ apps/insights/llm.py         │
                    │ ─ enrich(insight, snapshot)  │
                    │ ─ build_kpis_snapshot()      │
                    │ ─ is_enabled() / _provider() │
                    └────────────┬─────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
┌───────▼──────┐         ┌───────▼──────┐          ┌──────▼──────┐
│ POST         │         │ POST         │          │ POST        │
│ /insights/   │         │ /insights/   │          │ /insights/  │
│   generate   │         │   ask (chat) │          │   analyze   │
│ ?enrich=true │         │              │          │ (blueprint  │
│              │         │              │          │  dinâmico)  │
│ rules.py +   │         │ ai_views.py  │          │ ai_views.py │
│ llm.enrich() │         │ _chat_*()    │          │ run_analysis│
└──────────────┘         └──────────────┘          └─────────────┘
```

## Endpoints

### `POST /api/insights/generate?enrich=true|false`

**Body**: vazio ou `{}`.

**Sem enrich**: roda as 13 regras determinísticas e persiste `Insight` com `generated_by="rules"`.

**Com `enrich=true`** e provider ativo:
1. Roda regras → candidatos
2. Para cada candidato, chama `llm.enrich(candidate, snapshot)`
3. LLM devolve `{title, narrative, recommendations[]}`
4. Persiste com `generated_by="llm"` e `data.recommendations`

**Resposta**:
```json
{
  "stats": {"candidates": 7, "created": 0, "updated": 7},
  "llm": {
    "requested": true,
    "enabled": true,
    "enriched": 7,
    "failed": 0
  }
}
```

Se LLM não estiver ativo, cai em rules-only com `llm.reason = "provider_disabled_or_missing_key"`.

### `POST /api/insights/ask` (chat)

**Body**:
```json
{
  "question": "Quais foram minhas 10 maiores despesas nos últimos 90 dias?",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

**Comportamento**:
1. Classifica intenção (`classify_intent`) por regex/keywords em PT-BR
2. Detecta janela temporal (`detect_window_days`) — "30 dias", "trimestre", "12 meses", etc.
3. Executa `run_analysis(tenant_id, intent, days)` → blueprint estruturado
4. Monta snapshot completo do tenant (`build_kpis_snapshot`)
5. Se LLM ativo: chama `_chat_openai/_chat_anthropic` com snapshot + pergunta
6. Se LLM inativo ou falhar: gera resposta via `_demo_answer` (templates)

**Resposta**:
```json
{
  "answer": "texto da resposta",
  "intent": "top_expenses",
  "blueprint": { ... },     // dashboard dinâmico pronto para renderizar
  "used_llm": false,
  "provider": "demo"        // openai | anthropic | demo
}
```

### `POST /api/insights/analyze`

**Body**: `{"question": "..."}`.

Mesma análise determinística do `/ask`, mas **não chama LLM** — retorna apenas o blueprint. Útil quando o cliente já tem o texto e só quer o dashboard.

## Intenções suportadas (modo demo)

A engine classifica a pergunta em uma das categorias abaixo (ordem importa — a primeira que casar vence):

| Intent | Palavras-chave | Retorna |
|---|---|---|
| `top_suppliers` | fornecedor\w*, "para quem.*pag" | Top N fornecedores no período |
| `top_customers` | "cliente.*maior/top/mais/pag" | Top N clientes recebedores |
| `upcoming` | próximo, vencer, "a pagar/receber", forecast | Previsão 30 dias |
| `overdue` | atras\w*, vencid\w*, inadimpl\w* | Recebíveis e pagáveis vencidos |
| `cashflow` | "fluxo de caixa", entrada\s+e\s+sa[íi]da | Cashflow 12 meses |
| `top_expenses` | despes\w*, gast\w*, sa[íi]da\w*, pagament\w* | Top categorias de despesa |
| `top_revenues` | receit\w*, entrada\w*, recebiment\w*, fatur\w* | Top categorias de receita |
| `summary` (fallback) | "resumo", "panorama", "saúde" | Panorama com 4 KPIs + 2 tabelas |

Janela temporal padrão: 30 dias. Detecta "90 dias", "trimestre", "12 meses", "ano", "180 dias", "semestre".

## Blueprint (formato de resposta dinâmica)

```typescript
interface AnalysisBlueprint {
  title: string;             // título do dashboard
  summary: string;            // 1-2 frases
  intent: string;             // categoria detectada
  period_days: number;        // janela
  kpis: Array<{label, value, format?: "currency"|"number"|"percent", suffix?}>;
  tables: Array<{
    title, headers: string[], rows: Array<Array<string|number>>,
    value_columns?: number[]  // índices a formatar como moeda
  }>;
  charts: Array<{
    title, type: "bar"|"cashflow",
    data: Array<{label?, value?, ...}>
  }>;
}
```

Renderizado por `components/ai/blueprint-render.tsx`. KPIs viram cards, tabelas viram tabelas com formatação numérica, charts viram barras horizontais ou recharts.

## Prompts

### Chat (em `apps/insights/ai_views.py`)

```
Você é o assistente financeiro do BI AZUL, especializado em análise de
dados de PMEs brasileiras que usam a Conta Azul. Responda em português
brasileiro, com tom claro e direto.
Você recebe (a) a pergunta do usuário e (b) um JSON com o snapshot atual
dos KPIs e dados agregados do negócio. Sua resposta deve:
  1. Citar apenas números que estejam no snapshot — NÃO invente.
  2. Usar formato monetário brasileiro (R$ 1.234,56).
  3. Ser objetiva (2 a 5 parágrafos curtos).
  4. Terminar com 1-3 recomendações práticas quando fizer sentido.
  5. Quando não houver dados suficientes, dizer isso claramente.
Não use emojis. Não use markdown pesado.
```

### Enriquecimento de Insight (em `apps/insights/llm.py`)

Devolve JSON estruturado com `title`, `narrative` (2-4 frases) e `recommendations` (array de 2-3 strings).

OpenAI usa `response_format: {"type": "json_object"}` para garantir JSON válido.

## Snapshot do tenant

Função `build_kpis_snapshot(tenant_id)` em `apps/insights/llm.py` monta:

```json
{
  "today": "2026-05-23",
  "last_30d": {"cash_in", "cash_out", "net_profit", "revenue_sale", "num_sales"},
  "last_90d": {"cash_in", "cash_out", "net_profit"},
  "last_12m": {
    "cash_in", "cash_out", "net_profit",
    "top_revenue_categories": [...],
    "top_expense_categories": [...],
    "top_suppliers": [...]
  },
  "today_balance": {
    "overdue_rate_pct",
    "overdue_receivables",
    "overdue_payables",
    "upcoming_payables_30d",
    "upcoming_payables_60d",
    "upcoming_receivables_30d"
  }
}
```

Esse JSON é o **único** input financeiro que vai pra LLM — nada mais. Garante que respostas só citem números reais.

## Fallback gracioso

- **LLM timeout/erro 5xx**: o `enrich()` captura `Exception` e devolve `EnrichmentResult(enriched=False)` com o título/narrativa originais das regras
- **JSON inválido**: idem
- **Provider == "disabled"**: nunca chama API. Modo demo retorna template

Frontend mostra badge "IA" só nos insights com `generated_by="llm"`. Modo demo é totalmente transparente para o usuário.

## Custo aproximado

`gpt-4o-mini` (default):
- Input: $0.15 / 1M tokens
- Output: $0.60 / 1M tokens
- Snapshot do tenant ≈ 1.5-3k tokens
- Resposta ≈ 200-500 tokens
- **Custo por pergunta no chat ≈ $0.001-0.003** (centavos)
- **Custo por geração de insights enriquecidos (7 candidatos) ≈ $0.005-0.015**

`claude-sonnet-4-6` (Anthropic):
- ~10× mais caro mas qualidade superior em textos longos
- Não suporta `response_format: json_object`; usa regex para extrair JSON

## Como testar localmente

```bash
# Sem chave (modo demo — sempre funciona)
curl -X POST http://localhost:8000/api/insights/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "Top 5 fornecedores nos últimos 90 dias"}'

# Com OpenAI ativo
export INSIGHT_LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
# reiniciar gunicorn

curl -X POST http://localhost:8000/api/insights/generate?enrich=true \
  -H "Authorization: Bearer $TOKEN"
```

## Roadmap do módulo IA

- ✅ **Hoje**: chat livre, enriquecimento de insights, dashboards dinâmicos
- 🚧 **Fase 3-5**: previsões probabilísticas (caixa futuro, faturamento), resumo executivo diário/semanal, alertas inteligentes proativos (push via email/whatsapp)
- 🔮 **Futuro**: function calling para LLM acionar queries específicas (sem precisar passar snapshot inteiro), embeddings + RAG para responder sobre transações específicas, fine-tuning de modelo pequeno para reduzir custo
