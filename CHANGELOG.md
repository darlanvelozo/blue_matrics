# Changelog

Mudanças visíveis por sprint/onda. Detalhes técnicos em [`docs/02_ROADMAP.md`](docs/02_ROADMAP.md).

## [Unreleased] — Onda 4 (Redesign BI AZUL com IA)

### Adicionado
- **Rebrand**: BlueMetrics → **BI AZUL** com nova logo (hexágono azul) e cor primária `#1e5cff`.
- **`/api/dashboards/overview`** — endpoint único que alimenta a Visão Geral com 25+ campos.
- **`apps/analytics/kpis_v2.py`** — 11 KPIs novos: net_margin_pct, EBITDA simplificado, breakeven_point, contribution_margin_pct, cash_balance, working_capital, burn_rate, cash_forecast, financial_health_score (0–100), rfv_segments, abc_curve.
- **`apps/analytics/smart_cards.py`** — 8 geradores de cards inteligentes (lucro caiu, ponto de equilíbrio, caixa em risco, despesas em alta, fornecedor concentrado, vendas desaceleraram, etc.).
- **Analista IA conversacional** (`/app/ai`) — chat livre + dashboard adaptável (`POST /api/insights/ask`, `POST /api/insights/analyze`).
- **`apps/insights/llm.py`** — adapter OpenAI/Anthropic com fallback gracioso e snapshot do tenant.
- **5 novas regras de Insights** baseadas em FinancialEntry (top_expense_category, top_revenue_category, upcoming_payables, supplier_concentration, cash_in_trend).
- **Visão Geral premium** (`/app`) com ScoreGauge, SmartCards, BEP, Forecast 30d, 4 rankings, footer de sistema.
- Página **Customers** reformulada com tipos (Cliente/Fornecedor), recebido, pago, transações, última atividade.
- Página **Products** com KPIs de estoque (Valor R$, Unidades, SKUs) + colunas Custo médio/Preço/Margem/Estoque/Valor.
- Página **Sales** com banner amigável quando tenant não usa o módulo de vendas.
- Página **AI** com chat + sugestões + dashboard dinâmico.
- Componente reutilizável `RankingList`, `BlueprintRender`, `ScoreGauge`, `SmartCardItem`.
- Documentação nova: [`docs/04_AI_COPILOT.md`](docs/04_AI_COPILOT.md), [`docs/06_CONTA_AZUL_API.md`](docs/06_CONTA_AZUL_API.md).

### Corrigido
- **Conta Azul v2 endpoints corretos** descobertos: `/venda/busca`, `/venda/vendedores`, `/financeiro/eventos-financeiros/contas-a-{pagar,receber}/buscar`.
- **Mappers atualizados** para schema v2 snake_case: `valor_venda`, `custo_medio`, `saldo`, `data_vencimento`, `data_alteracao`, `categorias[]`, `situacao.nome`.
- **`paid_at`** agora extraído de `data_alteracao` quando status=ACQUITTED (paid).
- **Auto-criação de Category** a partir dos payloads financeiros (`/categorias` retorna só 10 itens).
- **URLs Django** migradas para `re_path(r"^api/.../?")` para tolerar trailing slash removido pelo Next.js proxy.
- Cliente HTTP (`_extract_items`) aceita array no top-level (para `/venda/vendedores`).
- Bug do botão "Gerar insights" não atualizar a lista (`await refetchQueries({type:'active'})`).
- Custo de produto vinha R$ 0 — agora lê `custo_medio` da v2 (R$ 1,04M em estoque na TABUAS).

### Schema (migrations novas)
- `sync.0002_product_stock_balance` — campo `Product.stock_balance` (DecimalField 14,3).
- `insights.0002_alter_insight_kind` — 5 novos kinds: `top_expense_category`, `top_revenue_category`, `upcoming_payables`, `supplier_concentration`, `cash_in_trend`.

### Configuração
- Novos env vars: `INSIGHT_LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`.

### Deps adicionadas
- Backend: `gunicorn`, `whitenoise`, `openpyxl` (este último faltava no `pyproject.toml` mas é usado em `apps/reports/exporters.py`).

---

## Anteriores

Veja [`docs/02_ROADMAP.md`](docs/02_ROADMAP.md) seção "Blocos 0–10" para o histórico completo de:

- Bloco 0: Foundation
- Bloco 1: Backend core (Django + multi-tenancy + JWT)
- Bloco 2: Frontend core (Next.js + landing + auth)
- Bloco 3: Integração Conta Azul (OAuth2 + Fernet)
- Bloco 4: ETL & Sync
- Bloco 5: Dashboards & KPIs (v1)
- Bloco 6: Insights IA (8 regras determinísticas)
- Bloco 7: Billing Stripe
- Bloco 8: Admin SaaS
- Bloco 9: Segurança & LGPD
- Bloco 10: Observabilidade & Production-ready
- Ondas 1-3: Polish, drill-down, Goals + exports + link público
