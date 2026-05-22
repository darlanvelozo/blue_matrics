# Roadmap de implementação — BlueMetrics

> Cada bloco entrega valor incremental, é testado e validado. Este documento é atualizado ao final de cada bloco.

## Status global

| Bloco | Descrição | Status | Concluído em |
|---|---|---|---|
| 0 | Foundation (estrutura + docs + docker-compose) | ✅ Concluído | 2026-05-14 |
| 1 | Backend core (Django + multi-tenancy + auth) | ✅ Concluído | 2026-05-14 |
| 2 | Frontend core (Next.js + landing + auth UI + shell) | ✅ Concluído | 2026-05-14 |
| 3 | Integração Conta Azul (OAuth2 + token storage) | ✅ Concluído | 2026-05-14 |
| 4 | ETL & sync incremental (Celery + retry) | ✅ Concluído | 2026-05-14 |
| 5 | Dashboards & KPIs (executivo, financeiro, comercial) | ✅ Concluído | 2026-05-14 |
| 4b | Adapter dev app Conta Azul (exchange-code, manual-token, schema v2 real) | ✅ Concluído | 2026-05-22 |
| 6 | Insights IA + resumo executivo diário | 🚧 Em andamento | — |
| 7 | Billing Stripe + planos + trial | ⏳ Pendente | — |
| 8 | Admin SaaS (MRR, churn, tenants) | ⏳ Pendente | — |
| 9 | Segurança & LGPD (rate limit, audit, headers) | ⏳ Pendente | — |
| 10 | Observabilidade & production-ready | ⏳ Pendente | — |

Legenda: ⏳ pendente · 🚧 em andamento · ✅ concluído · ⚠️ bloqueado

---

## Bloco 0 — Foundation ✅

**Objetivo:** dar fundação ao projeto. Sem código de negócio.

**Entregas:**
- [x] Estrutura de pastas `backend/`, `frontend/`, `docs/`, `infra/`, `scripts/`
- [x] `docs/01_ANALISE.md`, `docs/02_ROADMAP.md`, `docs/03_CONTEXTO.md`
- [x] `README.md` raiz com visão geral
- [x] `infra/docker-compose.yml` (postgres + redis)
- [x] `.env.example`
- [x] `.gitignore`
- [x] `Makefile` com comandos comuns

**Validação:**
- `make help` lista todos os comandos ✅
- `.env` criado a partir do `.env.example` ✅
- Docker-compose escrito e sintaticamente correto (não executado: Docker não disponível no ambiente WSL atual — fallback dev local usa SQLite + Celery eager). ✅

**Nota:** o ambiente de dev atual não tem Docker. Os blocos seguintes suportam **dois modos**:
- **Modo Docker** (recomendado, futuro): `make up` sobe Postgres + Redis.
- **Modo local** (atual): SQLite via `sqlite3` + Celery `task_always_eager=True`. Mesmas migrations, mesmo código.

---

## Bloco 1 — Backend core ✅

**Objetivo:** Django rodando, multi-tenancy enforced, auth JWT funcional.

**Entregas:**
- [x] Projeto Django 5.1 + DRF + SimpleJWT
- [x] Models: `Tenant`, `User` custom, `Membership`
- [x] Middleware `TenantContextMiddleware` que injeta `request.tenant`
- [x] Manager `TenantScopedManager` (fail-closed) + `unsafe_objects`
- [x] Endpoints `/api/auth/register`, `/login`, `/refresh`, `/me`
- [x] Settings: `base.py` / `dev.py` / `test.py` / `prod.py`
- [x] Pytest + fixtures (sem factory_boy ainda — fixtures simples suficientes)
- [x] Exception handler DRF padronizado
- [ ] Migração RLS Postgres → adiada para quando rodarmos sobre Postgres (Bloco 9 / Bloco 4)
- [ ] Dockerfile dev → adiada para Bloco 10

**Validação:**
- `pytest` → **16/16 passando** ✅ em 0.36s
- `ruff check .` → **All checks passed** ✅
- Anti-vazamento entre tenants testado (`test_filters_by_current_tenant`)
- `curl POST /api/auth/register` retorna 201 com user/tenant/tokens ✅
- `GET /healthz` retorna 200 ✅

**Cobertura por arquivo:**

| Arquivo | Função |
|---|---|
| `apps/tenants/models.py` | `Tenant`, `TenantScopedModel` (base abstrata) |
| `apps/tenants/context.py` | ContextVar `current_tenant_id` |
| `apps/tenants/managers.py` | `TenantScopedManager` fail-closed |
| `apps/tenants/middleware.py` | Injeta tenant a partir do user autenticado |
| `apps/accounts/models.py` | `User`, `Membership` |
| `apps/accounts/serializers.py` | `RegisterSerializer`, `LoginSerializer`, `UserSerializer` |
| `apps/accounts/views.py` | `RegisterView`, `LoginView`, `MeView` |
| `apps/accounts/exceptions.py` | Handler JSON padronizado |
| `tests/test_auth_flow.py` | 9 testes do fluxo de auth |
| `tests/test_tenancy.py` | 7 testes de isolamento |

---

## Bloco 2 — Frontend core ✅

**Objetivo:** Next.js rodando, landing page + auth UI + shell autenticado.

**Entregas:**
- [x] Next.js 16 (App Router) + TS + Tailwind v4 (design tokens custom no `globals.css`)
- [x] Stack instalada: TanStack Query, next-themes, lucide, framer-motion, recharts, zustand, react-hook-form, zod, class-variance-authority
- [x] Componentes UI base: `Button`, `Input`, `Label`, `Card`, `Skeleton`, `Logo`, `ThemeToggle`
- [x] Landing `/` premium: Hero, Social Proof, Benefícios (4), Dashboard Preview (mockup), Como funciona (3 passos), Planos (3 tiers), FAQ (4 perguntas), CTA final, Footer
- [x] `/login` e `/register` (com side hero) integrados ao backend via `apiFetch` + JWT
- [x] Shell `/app` com sidebar (8 itens) + header (tenant + logout + theme) + guard (carrega /me, redireciona em 401)
- [x] `apiFetch` com refresh automático em 401 e parser do envelope de erro do backend
- [x] Vitest configurado + 7 testes passando

**Validação:**
- `vitest run` → **7/7 passando** ✅
- `tsc --noEmit` → **0 erros** ✅
- `next build` → **5 rotas static** geradas ✅
- `next dev` → landing/login/register devolvem 200 com conteúdo correto ✅
- E2E: POST /register no backend a partir do frontend → recebe JWT → GET /me → retorna usuário+tenant ✅
- CORS preflight OK ✅

**Pendências reconhecidas (não bloqueiam):**
- Lighthouse formal não rodado (sem Chrome no ambiente).
- Playwright e2e completo adiado para Bloco 9 (junto com hardening).
- Dashboards `/app/dashboards/*` e `/app/insights` ainda mostram skeletons — implementados nos Blocos 5/6.

**Arquivos principais:**

| Arquivo | Função |
|---|---|
| `src/app/page.tsx` | Landing premium completa |
| `src/app/layout.tsx` | Root layout + ThemeProvider + QueryClient |
| `src/app/login/page.tsx` | Login |
| `src/app/register/page.tsx` | Cadastro (split layout) |
| `src/app/app/layout.tsx` | Shell autenticado + guard |
| `src/app/app/page.tsx` | Dashboard home (estado vazio convidando a conectar) |
| `src/components/app/sidebar.tsx` | Navegação lateral |
| `src/components/app/header.tsx` | Header com tenant + logout |
| `src/components/ui/*` | Design system (Button, Card, Input, ...) |
| `src/lib/api.ts` | Cliente HTTP + refresh JWT |
| `src/lib/auth.ts` | Helpers de auth |

---

## Bloco 3 — Integração Conta Azul (OAuth2) ✅

**Objetivo:** tenant consegue conectar sua Conta Azul.

**Entregas:**
- [x] App `apps.integrations` registrada
- [x] Models: `ContaAzulConnection` (1:1 com Tenant, status, tokens cifrados, expires_at, scope, last_error, last_synced_at) e `OAuthState` (anti-CSRF, TTL 10min)
- [x] Camada `crypto.py` com `encrypt`/`decrypt` (Fernet) — chave em `settings.FERNET_KEY`
- [x] Endpoints:
  - `GET /api/integrations/contaazul/status` (auth) — devolve estado da conexão (sem expor tokens)
  - `GET /api/integrations/contaazul/authorize` (auth) — gera state, devolve `{url, state}` para o front redirecionar
  - `GET /api/integrations/contaazul/callback` (público) — troca code→tokens, redireciona pro frontend com query string `?status=...&reason=...`
  - `POST /api/integrations/contaazul/disconnect` (auth) — apaga tokens e marca desconectado
- [x] Serviço `ContaAzulOAuthService` (httpx) com `build_authorize_url`, `exchange_code`, `refresh`. Aceita `http_client` injetado para testes (MockTransport).
- [x] Task Celery `integrations.refresh_expiring_tokens(window_minutes=10)`
- [x] Helper `apps.tenants.utils.get_request_tenant(request)` para DRF views (resolve a partir de `request.user` quando middleware ainda não rodou)
- [x] UI `/app/integrations` premium com card, status badge, banners de callback, botões Conectar/Desconectar
- [x] Lib frontend `lib/integrations.ts`

**Validação:**
- `pytest` → **50/50 passando** ✅ (4 crypto, 3 model, 7 service, 14 view, 5 task + 17 dos blocos anteriores)
- `ruff check` → **All checks passed** ✅
- `tsc --noEmit` → 0 erros, `next build` → 6 rotas geradas ✅
- E2E manual:
  - `GET /status` (autenticado) → 200 com `{status: disconnected, ...}`
  - `GET /authorize` (sem CLIENT_ID) → **503** com `{error.code: "oauth_misconfigured"}`
  - `GET /callback` (sem code) → **302** para `http://localhost:3000/app/integrations?status=error&reason=missing_code_or_state`
  - `POST /disconnect` → 200
- **Test de não-vazamento de token:** `test_does_not_leak_tokens` valida que GET /status nunca expõe os campos `access_token_enc`/`refresh_token_enc` no JSON.

**Pendências e notas:**
- Smoke E2E **real** contra a Conta Azul exige criar app em `https://portaldevs.contaazul.com/` e preencher `CONTA_AZUL_CLIENT_ID`/`CONTA_AZUL_CLIENT_SECRET` em `.env`. Quando preencher, o fluxo Conectar → autoriza no provedor → callback → tokens salvos → redirect funciona sem mudar uma linha.
- Celery beat schedule para `refresh_expiring_tokens` será adicionado no Bloco 10 (em dev roda em eager mode quando chamado manualmente).
- Refresh de chave Fernet (rotação) ficará no Bloco 9.

**Arquivos:**
| Arquivo | Função |
|---|---|
| `apps/integrations/models.py` | `ContaAzulConnection`, `OAuthState` |
| `apps/integrations/crypto.py` | Fernet wrapper |
| `apps/integrations/services.py` | `ContaAzulOAuthService` |
| `apps/integrations/views.py` | 4 endpoints |
| `apps/integrations/tasks.py` | `refresh_expiring_tokens` |
| `apps/integrations/tests/` | 33 testes |
| `apps/tenants/utils.py` | `get_request_tenant(request)` |
| `frontend/src/lib/integrations.ts` | Client TS dos endpoints |
| `frontend/src/app/app/integrations/page.tsx` | UI premium |

---

## Bloco 4 — ETL & sync ✅

**Objetivo:** dados da Conta Azul fluem para nosso banco.

**Entregas:**

**Backend (`apps/sync`):**
- [x] **BYO credentials por tenant:** adicionados campos `client_id` + `client_secret_enc` em `ContaAzulConnection` (criptografado com Fernet). Endpoints `GET/PUT/DELETE /api/integrations/contaazul/credentials`. UI atualizada com formulário inline na página de Integrações
- [x] Models **Bronze:** `RawPayload` (JSON raw versionado por `(tenant, resource, external_id, fetched_at)`)
- [x] Models **Silver:** `Customer`, `Product`, `Category`, `Salesperson`, `Sale`, `SaleItem`, `FinancialEntry` — todos `TenantScopedModel`
- [x] `SyncLog` (status, fetched, upserted, errors, message) indexado por `(tenant, -started_at)`
- [x] `ContaAzulClient`:
  - Auto-refresh em 401 (1ª tentativa)
  - Retry exponencial em 5xx (1s, 2s, 4s…, cap 30s)
  - Respeita `Retry-After` em 429
  - Paginação com 3 heurísticas de parada (vazio / totalPages / página menor que page_size)
- [x] **Mappers** tolerantes a PT-BR + EN (id/uuid, nome/name, valorVenda/price, situacao/status, …)
- [x] **Orquestrador** `sync_tenant(tenant_id)` em ordem: categorias → vendedores → clientes → produtos → vendas (com itens) → financeiro receivable → payable
- [x] Falha em 1 recurso não derruba os demais; status master fica `partial`
- [x] Sync **idempotente** via `(tenant, external_id)` constraint + `update_or_create`
- [x] **Janela inicial:** 365 dias (12 meses, conforme escolhido)
- [x] Task Celery `sync.sync_tenant` com retry x2
- [x] Endpoints `GET /api/sync/logs`, `POST /api/sync/run`

**Frontend:**
- [x] Página `/app/sync` com Card "Última sincronização" + histórico por recurso (auto-refresh a cada 3s se algo estiver rodando)
- [x] Botão "Sincronizar agora" (desabilitado se já estiver rodando)
- [x] Status badges coloridos (sucesso/em execução/parcial/falhou)
- [x] Item no sidebar
- [x] Lib `frontend/src/lib/sync.ts`

**Validação:**
- **93/93 testes passando** ✅ (17 base + 33 integrations + 12 sync + 31 sync orchestrator/client/mappers/views/credentials)
- `ruff check` → **All checks passed** ✅
- `tsc --noEmit` → 0 erros
- `next build` → **7 rotas** static ✅
- Smoke E2E:
  - `GET /api/sync/logs` (vazio) → `{"logs": []}` ✅
  - `POST /api/sync/run` sem conectar → 400 `not_connected` ✅
  - `/app/sync` no frontend → 200 ✅
- **Test de sync end-to-end**: `test_full_sync_populates_silver` valida pipeline completo: mock httpx → 7 endpoints → Bronze guarda raw → Silver tem FK resolvida (Sale.customer, SaleItem.product) → SyncLog master
- **Test idempotência**: `test_sync_is_idempotent` — rodar duas vezes não duplica
- **Test resiliência**: `test_one_resource_failing_does_not_kill_others` — 500 em `/vendas` não impede customers

**Pendências:**
- Beat schedule de sync periódico → Bloco 10
- VCR.py descartado em favor de `httpx.MockTransport` (mais determinístico, sem fixture files)
- Sync incremental por timestamp ainda não implementado para todos os recursos — o `since` (dataInicial) já é passado para `/vendas` e `/financeiro/*`

---

## Bloco 5 — Dashboards & KPIs ✅

**Objetivo:** o usuário vê valor: dashboards bonitos com dados reais.

**Entregas:**

**Backend (`apps/analytics`):**
- [x] Helpers `periods.py` — presets (`last_30d`, `this_month`, `last_month`, `ytd`, `last_12m`, etc), ranges explícitos, comparação (prev_period / yoy), `month_buckets()`
- [x] KPIs primitivos em `kpis.py`: `revenue`, `num_sales`, `avg_ticket`, `cash_in`, `cash_out`, `net_profit`, `overdue_rate`
- [x] Séries: `revenue_by_month`, `cashflow_by_month`, `dre_monthly`
- [x] Top N: `top_customers`, `top_products`, `sales_by_salesperson`
- [x] `executive_summary` / `financial_summary` / `commercial_summary` com `kpi_with_change`
- [x] `has_any_data(tenant)` — sinaliza estado vazio para UI
- [x] Endpoints: `GET /api/dashboards/executive|financial|commercial` com filtros `?preset=&start=&end=&comparison=`
- [x] **Seed sintético** via `manage.py seed_demo --tenant <slug>` (12 meses, sazonalidade dez=1.6x, crescimento 1.5%/mês, expense base configurável). Idempotente (limpa antes).

**Frontend:**
- [x] `lib/dashboards.ts` com tipos TS espelhando o backend
- [x] Componentes shared: `KpiCard` (com indicador up/down), `PeriodFilter` (chips), `EmptyDashboardState`, charts (`RevenueChart`, `CashflowChart`, `NetProfitChart`) usando Recharts
- [x] 3 páginas:
  - `/app/dashboards/executivo` — 4 KPIs + faturamento mensal + top clientes + top produtos
  - `/app/dashboards/financeiro` — 4 KPIs + fluxo de caixa + lucro líquido mensal
  - `/app/dashboards/comercial` — 3 KPIs + faturamento + ranking clientes/produtos/vendedores
- [x] Estado vazio com CTA para conectar/sincronizar
- [x] Filtros globais (presets) reativos via TanStack Query (cache por preset)

**Materialized views:** **adiadas** — performance OK em SQLite com seed de 2k vendas. Migram para MVs quando rodarmos em Postgres com volume real (Bloco 10 ou conforme demanda).

**Validação:**
- `pytest` → **124/124 passando** ✅ (31 novos em analytics: períodos, KPIs, views)
- `ruff` → All checks passed ✅
- `tsc + next build` → **10 rotas** ✅
- Smoke E2E: tenant `dev-dieyson` populado com seed (2142 vendas, 104 lançamentos financeiros, 14 clientes, 8 produtos, 3 vendedores). Endpoints retornam:
  - `/executive` last_12m → R$ **173.211,50** faturamento, lucro líquido R$ **102.369,39**, ticket médio R$ **80,86**, inadimplência **1,72%**
  - `/financial` last_12m → cash_in/out/net mensais
  - `/commercial` last_12m → top 10 clientes, top 10 produtos, 3 vendedores
- Frontend: todas as 9 rotas autenticadas/públicas respondem 200 ✅
- **Test de isolamento**: `test_revenue_does_not_leak_between_tenants` valida que KPIs de um tenant nunca contam dados de outro

**Pendências (deslocadas):**
- Exportação PDF/Excel → Bloco 6 ou posterior
- Metas (`Goal` model) → Bloco 6
- Materialized views → quando volume justificar
- Filtros explícitos por categoria/vendedor (drill-down) → posterior

---

## Bloco 4b — Adapter dev app Conta Azul ✅

**Por que existiu:** ao integrar pela primeira vez contra a Conta Azul real, descobrimos:
- Apps em **modo desenvolvimento** têm `redirect_uri` **fixo em `https://contaazul.com`** (não dá pra apontar pro nosso backend)
- Auth endpoint do dev é `/login` (não `/oauth2/authorize`)
- Schema real da v2 usa `itens`/`itens_totais` (PT-BR), mas `/produtos` usa `items`/`totalItems` (EN)
- Endpoints reais: `/categorias`, `/pessoa` (singular), `/produtos` (plural), `/servicos`
- `/vendedor`, `/venda`, `/financeiro/*` exigem POST/path diferente — não suportados na conta dev (falham graceful)
- `tamanho_pagina` precisa ser ∈ {10, 20, 50, 100, 200, 500, 1000}

**Entregas:**
- [x] `ContaAzulConnection` ganhou `redirect_uri_override` e `auth_url_override`
- [x] `ContaAzulOAuthService.for_connection(conn)` aplica overrides automaticamente
- [x] Endpoint **`POST /api/integrations/contaazul/exchange-code`** — usuário cola `code` recebido e o backend troca por tokens
- [x] Endpoint **`POST /api/integrations/contaazul/manual-token`** — injeta access_token direto (atalho para teste imediato com token entregue pelo portal)
- [x] `ContaAzulClient.paginate` usa `pagina`/`tamanho_pagina` (v2 BR) e extrai `itens`, `data`, `items` ou `content`
- [x] Orchestrator: endpoints atualizados (`/pessoa`, `/produtos`, `/categorias`) + flag `RESOURCES_WITHOUT_PAGINATION` para `/categorias`
- [x] UI: form de credenciais com toggle "App em modo desenvolvimento" + 2 cards "Modo dev" colapsáveis (paste do code, paste do access_token)
- [x] 11 novos testes em `test_dev_endpoints.py`

**Validação:**
- pytest: **135/135** ✅, ruff limpo
- E2E REAL contra `api-v2.contaazul.com` com conta dev do usuário:
  - `GET /v1/categorias` → **123 categorias importadas** ✅
  - `GET /v1/pessoa`, `/v1/produtos` → 200 (conta dev vazia, mas adapter funciona)
  - `GET /v1/vendedor`, `/v1/venda`, `/v1/financeiro/*` → 404/405 (não disponível em dev, falha graceful)
- Status do tenant `dev-dieyson`: `connected`, `dev_mode=True`, último sync trouxe 123 categorias reais

## Bloco 6 — Insights IA

**Objetivo:** plataforma "fala" com o usuário.

**Entregas:**
- App `insights` com engine de regras (anomalia, sazonalidade, top movers)
- Service `InsightNarrator` que usa Claude (`claude-sonnet-4-6`) com prompt cache em parâmetros estáveis
- Model `Insight` (tipo, severidade, mensagem, dados de apoio, lido/não lido)
- Job diário `generate_daily_insights(tenant_id)` + e-mail resumo (Resend ou SES)
- UI `/app/insights` (feed + filtros) + widget no dashboard
- Chat assistant (`/app/assistant`) com contexto do tenant via RAG simples
- Testes: regra → insight; mock LLM para narrativa

**Validação:**
- Tenant com queda de faturamento recebe insight correto
- E-mail diário sai
- LLM cache hit rate medido

---

## Bloco 7 — Billing Stripe + planos

**Objetivo:** monetização real.

**Entregas:**
- App `billing` com models `Plan`, `Subscription`, `Invoice`
- Stripe Checkout para upgrade trial→paid
- Webhooks Stripe (`checkout.session.completed`, `invoice.paid`, `customer.subscription.updated/deleted`)
- Middleware `SubscriptionGuard` (read-only após vencer trial sem pagamento)
- UI `/app/billing` (plano atual, faturas, alterar plano, cancelar)
- Trial 7 dias automático no signup
- Planos seedados via migration

**Validação:**
- Trial expira → bloqueio gracioso
- Pagamento ativa assinatura (Stripe test mode)
- Cancelamento + downgrade funcionam

---

## Bloco 8 — Admin SaaS

**Objetivo:** operar o SaaS.

**Entregas:**
- `/admin-saas` (Next.js) protegido por role `SUPERADMIN`
- Endpoints `/api/admin/metrics/saas` (MRR, ARR, churn, conversão trial, MAU, DAU)
- Listagem tenants com search, filtros, drill-down
- Logs de auditoria visíveis (django-auditlog)
- Impersonação (com warning + audit) — opcional

**Validação:**
- Métricas batem com cálculos manuais sobre dados seed
- Não-admin não acessa

---

## Bloco 9 — Segurança & LGPD

**Objetivo:** pronto para auditoria.

**Entregas:**
- django-ratelimit em endpoints sensíveis
- Audit log para ações financeiras / mudança de plano / acesso admin
- Security headers via django-csp + middleware customizado
- Endpoints LGPD: `/api/me/export`, `/api/me/anonymize`, `/api/me/delete`
- Política de retenção configurável
- Cookies banner
- Pentest checklist documentado em `docs/04_SECURITY.md`

**Validação:**
- `bandit -r backend/` zero high
- OWASP ZAP rodado contra dev sem findings críticos
- Teste e2e: usuário consegue exportar e deletar conta

---

## Bloco 10 — Observabilidade & production-ready

**Objetivo:** deploy seguro.

**Entregas:**
- Logs estruturados (`structlog`) com `tenant_id`, `request_id`
- `/healthz` (liveness), `/readyz` (readiness checando DB + Redis)
- Sentry integrado backend + frontend
- Dockerfiles prod multi-stage (slim)
- GitHub Actions: lint + tests + build
- `docs/05_DEPLOY.md` com runbook
- Backup automático Postgres documentado

**Validação:**
- CI verde
- `docker compose -f docker-compose.prod.yml up` sobe stack completa
- Sentry recebe erro de teste

---

## Política de testes

| Camada | Ferramenta | Cobertura mínima |
|---|---|---|
| Backend unit | pytest + pytest-django | 80% |
| Backend integração | pytest + factories + VCR | rotas críticas |
| Frontend componentes | Vitest + Testing Library | componentes shared |
| E2E | Playwright | fluxos críticos: signup, conectar Conta Azul, dashboard |
| Lint | ruff, black, eslint, prettier | strict |
| Type | mypy (strict mode em apps de domínio), tsc strict | strict |
| Security | bandit, pip-audit, npm audit | 0 high |

## Definição de "pronto" por bloco

1. Código implementado.
2. Testes escritos e passando.
3. Linters e type-checkers passando.
4. Documentação atualizada (este arquivo + `03_CONTEXTO.md`).
5. README atualizado se afetar setup.
6. Smoke manual do fluxo principal feito.
