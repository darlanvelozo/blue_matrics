# Contexto técnico — BlueMetrics

> Estado vivo da arquitetura. Atualizado ao final de cada bloco.

## Stack

### Backend
- **Linguagem:** Python 3.12
- **Framework:** Django 5.x + Django REST Framework
- **Banco:** PostgreSQL 16 (com RLS habilitado nas tabelas tenant-scoped)
- **Cache / Broker:** Redis 7
- **Async:** Celery 5 (workers + beat)
- **Auth:** djangorestframework-simplejwt
- **HTTP client:** httpx
- **Criptografia:** cryptography (Fernet)
- **Testes:** pytest, pytest-django, factory_boy, VCR.py
- **Lint/format:** ruff, black, mypy

### Frontend
- **Framework:** Next.js 15 (App Router) + TypeScript
- **Styling:** Tailwind CSS v4
- **UI kit:** shadcn/ui
- **Data:** TanStack Query v5
- **Charts:** Recharts
- **Animations:** Framer Motion
- **State:** Zustand
- **Testes:** Vitest + Testing Library + Playwright
- **Lint:** ESLint flat config + Prettier

### Infra
- **Containers:** Docker + Docker Compose
- **Orquestração futura:** (TBD — provavelmente AWS ECS / Fly.io)
- **CI:** GitHub Actions
- **Observabilidade:** Sentry + structlog (logs JSON)

## Estrutura de pastas

```
projeto_analise_dados_contazul/
├── docs/
│   ├── 01_ANALISE.md
│   ├── 02_ROADMAP.md
│   ├── 03_CONTEXTO.md       ← este arquivo
│   ├── 04_SECURITY.md       (Bloco 9)
│   └── 05_DEPLOY.md         (Bloco 10)
├── backend/
│   ├── manage.py
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── bluemetrics/         ← projeto Django (settings, urls, wsgi, asgi, celery)
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── dev.py
│   │   │   └── prod.py
│   │   ├── urls.py
│   │   ├── celery.py
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── accounts/        ← users, memberships, auth
│   │   ├── tenants/         ← tenant model + middleware + manager
│   │   ├── integrations/    ← Conta Azul OAuth + service
│   │   ├── sync/            ← ETL + Celery tasks
│   │   ├── analytics/       ← MVs, KPIs, dashboards
│   │   ├── insights/        ← regras + LLM
│   │   ├── billing/         ← Stripe + plans
│   │   └── admin_saas/      ← métricas SaaS
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── Dockerfile
│   ├── src/
│   │   ├── app/             ← rotas (App Router)
│   │   │   ├── (marketing)/ ← landing
│   │   │   ├── (auth)/      ← login, register
│   │   │   ├── app/         ← área autenticada
│   │   │   └── admin-saas/  ← admin
│   │   ├── components/
│   │   │   ├── ui/          ← shadcn
│   │   │   └── shared/
│   │   ├── lib/             ← api client, auth, utils
│   │   └── styles/
│   └── tests/
├── infra/
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── nginx/               ← reverse proxy prod
├── scripts/
│   ├── seed_demo.py
│   └── ...
├── .env.example
├── .gitignore
├── Makefile
└── README.md
```

## Variáveis de ambiente (visão geral — ver `.env.example` para detalhes)

| Var | Onde usada | Descrição |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | backend | `bluemetrics.settings.dev` / `prod` |
| `SECRET_KEY` | backend | Django secret |
| `DATABASE_URL` | backend | Postgres DSN |
| `REDIS_URL` | backend | Redis para cache+Celery |
| `FERNET_KEY` | backend | Criptografia tokens OAuth |
| `CONTA_AZUL_CLIENT_ID` | backend | OAuth |
| `CONTA_AZUL_CLIENT_SECRET` | backend | OAuth |
| `CONTA_AZUL_REDIRECT_URI` | backend | `https://app.bluemetrics.com/api/integrations/contaazul/callback` |
| `STRIPE_SECRET_KEY` | backend | Billing |
| `STRIPE_WEBHOOK_SECRET` | backend | Billing |
| `ANTHROPIC_API_KEY` | backend | Insights LLM |
| `RESEND_API_KEY` | backend | E-mail transacional |
| `SENTRY_DSN` | backend / frontend | Erros |
| `NEXT_PUBLIC_API_URL` | frontend | URL do backend |

## Decisões de arquitetura (ADRs resumidos)

### ADR-001: Multi-tenancy por shared schema + tenant_id + RLS
**Contexto:** queremos isolar dados de N empresas em uma única instância.
**Decisão:** todas as tabelas de domínio têm coluna `tenant_id NOT NULL`. Middleware injeta `request.tenant`. Manager padrão filtra. Postgres RLS é defesa em profundidade.
**Por que não django-tenants (schema por tenant)?** Mais simples operacionalmente em escala (milhares de tenants), backups simples, MVs compartilhadas, migrations mais rápidas.

### ADR-002: Tokens OAuth criptografados em repouso (Fernet)
**Contexto:** tokens de terceiros são chave do reino.
**Decisão:** armazenar criptografado com Fernet; chave fora do banco (env).
**Trade-off:** rotação de chave exige re-criptografar — script previsto em Bloco 9.

### ADR-003: Bronze/Silver/Gold para dados sincronizados
**Contexto:** API de terceiros muda; queremos reprocessar.
**Decisão:** Bronze = raw JSON. Silver = normalizado. Gold = MVs agregadas. Permite reprocessar sem refazer chamada à API.

### ADR-004: Claude Sonnet para insights
**Contexto:** precisamos de narrativa de qualidade, custos controlados.
**Decisão:** `claude-sonnet-4-6` com prompt cache nos blocos estáveis (system prompt + esquema). Fallback determinístico se chave indisponível.

### ADR-005: Frontend Next.js App Router em SSR limitado
**Contexto:** SEO importa na landing, mas a app autenticada é SPA-like.
**Decisão:** landing como server components (SEO); área `/app` como client components com fetch via TanStack Query.

## Convenções de código

### Backend
- 1 app por bounded context (não criar utils.py gigante)
- Models nunca importam de outras apps diretamente — usar serviços
- Endpoints sempre via DRF ViewSets / GenericViews
- Toda query que acessa dado tenant-scoped DEVE passar pelo manager (sem `.objects.filter` manual fora do manager)
- Migrations versionadas, nunca editar uma já aplicada em prod

### Frontend
- 1 rota = 1 page.tsx; componentes específicos da rota ficam em `_components/`
- Componentes shared em `src/components/shared/`
- Server Actions só para mutações idempotentes simples; resto via API REST
- TanStack Query keys padronizadas: `['domain', 'resource', params]`

## Estado por bloco

### Bloco 0 — Foundation ✅
- **Status:** concluído em 2026-05-14
- Estrutura de pastas, docs (`01_ANALISE`, `02_ROADMAP`, `03_CONTEXTO`), `README.md`, `.env.example`, `.gitignore`, `Makefile`, `infra/docker-compose.yml` prontos.
- **Nota ambiental:** o ambiente dev atual (WSL2) não tem Docker. Dev local cai em SQLite + Celery eager via `.env` com `DATABASE_URL=` vazio.

### Bloco 1 — Backend core ✅
- **Status:** concluído em 2026-05-14
- **Apps criadas:** `apps.tenants`, `apps.accounts`
- **Multi-tenancy:**
  - `Tenant` com `slug` único, `status` (trial/active/...), `trial_ends_at`.
  - `TenantScopedModel` base abstrata; manager filtra por `current_tenant_id` (ContextVar).
  - Manager fail-closed: sem tenant → queryset vazio. Para escapes, `Model.unsafe_objects`.
  - Middleware `TenantContextMiddleware` resolve tenant a partir do `Membership` ativo (ou header `X-Tenant-Slug` para superuser).
- **Auth:**
  - `User` custom com e-mail como identificador.
  - `Membership` (user ↔ tenant + role owner/admin/viewer).
  - JWT via SimpleJWT (access 30min, refresh 14d, rotate=True).
  - Endpoints `/api/auth/register|login|refresh|me`.
  - Senha validada por validadores Django + min 8 chars.
- **Padrão de erro JSON:** `{"error": {"code", "message", "details"}}` via `custom_exception_handler`.
- **Testes:** 16/16 passando. Cobre: register (sucesso, senha fraca, duplicata, slug único), login (sucesso, falha, case-insensitive), me (auth required), tenancy (fail-closed, filtro, save sem contexto, unsafe_objects).
- **Linters:** ruff limpo.
- **Pendências conhecidas:** RLS Postgres (no Bloco 4/9), Dockerfile (Bloco 10).

### Bloco 2 — Frontend core ✅
- **Status:** concluído em 2026-05-14
- **Stack:** Next.js 16 (App Router) + Tailwind v4 + design tokens custom (light/dark via CSS vars)
- **Componentes UI:** `Button` (CVA com 6 variantes), `Card`/`CardHeader`/`CardContent`, `Input`, `Label`, `Skeleton`, `Logo`, `ThemeToggle`
- **Páginas:**
  - `/` — landing premium com 8 seções (hero + gradient text, social proof, benefits, dashboard preview, how it works, pricing, FAQ, CTA)
  - `/login` — formulário simples
  - `/register` — split layout com aside visual
  - `/app` — shell autenticado com sidebar + header + guard (`getMe` → 401 redireciona /login)
- **Lib:**
  - `lib/api.ts` — `apiFetch` com refresh JWT automático em 401, parser do envelope `{error:{code,message,details}}`
  - `lib/auth.ts` — `registerUser`, `loginUser`, `getMe`, `logout`
  - `lib/query-client.ts` — singleton do TanStack Query
- **Testes:** Vitest 7/7. Cobre `cn`, `formatCurrencyBRL`, `formatPercent`, `<Button>` (render, click, disabled).
- **Build:** `next build` gera 5 rotas estáticas.
- **Pendências:** Playwright (Bloco 9), dashboards reais (Bloco 5).

### Bloco 3 — Integração Conta Azul (OAuth2) ✅
- **Status:** concluído em 2026-05-14
- **App criada:** `apps.integrations`
- **Modelos:**
  - `ContaAzulConnection` (1:1 com Tenant): `status`, `access_token_enc`, `refresh_token_enc`, `expires_at`, `scope`, `last_error`, `last_synced_at`, `connected_at`
  - `OAuthState`: state opaco (`secrets.token_urlsafe(32)`), tenant, e-mail iniciador, TTL 10min, consumed_at
- **Crypto:** Fernet (`cryptography`) com chave em `settings.FERNET_KEY`. Helpers `encrypt`/`decrypt`. Properties `conn.access_token`/`conn.refresh_token` decifram on-read.
- **Service `ContaAzulOAuthService`:**
  - `build_authorize_url(state)` → URL com `response_type=code`, `client_id`, `redirect_uri`, `scope`, `state`
  - `exchange_code(code)` → POST `/oauth2/token` com `grant_type=authorization_code`, Basic auth `client_id:client_secret`
  - `refresh(refresh_token)` → POST `/oauth2/token` com `grant_type=refresh_token`
  - Aceita `http_client` injetado (testes usam `httpx.MockTransport`)
  - Erros mapeados para `OAuthError`
- **Endpoints:**
  - `GET /api/integrations/contaazul/status` (auth)
  - `GET /api/integrations/contaazul/authorize` (auth) → `{url, state}`
  - `GET /api/integrations/contaazul/callback` (público) → 302 para `{FRONTEND_URL}/app/integrations?status=...`
  - `POST /api/integrations/contaazul/disconnect` (auth)
- **Task Celery:** `integrations.refresh_expiring_tokens(window_minutes=10)` — renova quem expira na janela; trata erros e marca status.
- **Helper crítico:** `apps.tenants.utils.get_request_tenant(request)` — resolve tenant a partir de `request.user.memberships` (necessário em DRF porque o middleware roda antes de DRF autenticar via JWT). Também popula o ContextVar.
- **UI:** `/app/integrations` com card de status, banners de callback (success/error), botões Conectar/Desconectar, loading skeleton. Lib `frontend/src/lib/integrations.ts`.
- **Testes:** 33/33 (crypto 4, model 3, service 7, views 14, task 5). Mock do provider via httpx.MockTransport e `unittest.mock.patch`.

### ADR-006: get_request_tenant em vez de só middleware
**Contexto:** TenantContextMiddleware roda no chain Django, antes de DRF autenticar JWT. Em DRF views autenticadas, `request.tenant` vinha None.
**Decisão:** manter o middleware (cobre fluxo session-auth do admin Django) e adicionar `get_request_tenant(request)` para views DRF. O helper popula `request.tenant` e o ContextVar.
**Trade-off:** views DRF agora explicitamente chamam o helper. Aceitável — ainda mais robusto.

### Bloco 4 — ETL & sync ✅
- **Status:** concluído em 2026-05-14
- **App criada:** `apps.sync`
- **BYO credentials:** `ContaAzulConnection` ganhou `client_id` + `client_secret_enc`. Cada tenant cadastra seu próprio app OAuth via `/api/integrations/contaazul/credentials` (`GET`, `PUT`, `DELETE`). Service `ContaAzulOAuthService.for_connection(conn)` usa as do tenant; se não houver, cai em `settings.CONTA_AZUL`.
- **Bronze → Silver → (Gold no Bloco 5):**
  - `RawPayload`: raw JSON da API, com `schema_version`. Unique `(tenant, resource, external_id, fetched_at)`.
  - Silver: `Customer`, `Product`, `Category`, `Salesperson`, `Sale`, `SaleItem`, `FinancialEntry`. Cada um tem `external_id` único por tenant.
  - `SyncLog`: auditoria de cada run.
- **Client HTTP `apps.sync.client.ContaAzulClient`:**
  - Auto-refresh em 401 (1ª tentativa) e quando `is_expired()`
  - Retry exponencial em 5xx (cap 30s)
  - Respeita `Retry-After` em 429
  - `paginate()` itera com 3 heurísticas de parada
  - Aceita `http_client` injetado (testes via `httpx.MockTransport`)
- **Orquestrador `apps.sync.orchestrator.sync_tenant(tenant_id)`:**
  - Ordem: categorias → vendedores → clientes → produtos → vendas → AR → AP (dependências de FK respeitadas)
  - Falha em 1 recurso → status `partial` no master
  - Cache de lookups por external_id durante a execução
  - Janela 365 dias para `/vendas` e `/financeiro/*` (passa `dataInicial`)
  - Atualiza `ContaAzulConnection.last_synced_at` no fim
- **Task Celery:** `sync.sync_tenant_task(tenant_id)` com retry x2 e default_retry_delay=60s
- **Endpoints:**
  - `GET /api/sync/logs` (auth) → últimos 50 logs do tenant
  - `POST /api/sync/run` (auth) → 202 se Conexão `connected`, senão 400 `not_connected`
- **Mappers** (`apps.sync.mappers`): puros, defensivos, suportam chaves PT-BR e EN. Helper `_first(payload, *keys)` evita repetição.
- **UI `/app/sync`:** Card resumo + histórico com auto-refresh quando há sync rodando.

### ADR-007: BYO credentials por tenant
**Contexto:** o app OAuth na Conta Azul precisa de Client ID/Secret. Ou o SaaS fornece um global (modo "plataforma") ou cada tenant cadastra o seu (modo BYO).
**Decisão:** BYO por tenant, com fallback opcional para settings. Permite operação sem precisar criar um app do BlueMetrics no portal de devs da Conta Azul.
**Trade-off:** UX um pouco mais técnica no onboarding (usuário precisa criar app no portal Conta Azul). Mitigado por instruções inline + botão para copiar Redirect URI.

### ADR-008: Bronze raw + Silver normalizado
**Contexto:** API v2 da Conta Azul pode mudar e queremos reprocessar.
**Decisão:** guardamos raw JSON em `RawPayload` antes de mapear para Silver. Mappers são puros — permite reprocessar Silver lendo Bronze, sem chamar API.
**Trade-off:** dobra storage. Aceitável para auditoria + flexibilidade.

### Bloco 5 — Dashboards & KPIs ✅
- **Status:** concluído em 2026-05-14
- **App criada:** `apps.analytics`
- **`periods.py`:** `Period` (dataclass com `start`/`end` inclusivo), `resolve_period(preset|start|end)`, `month_buckets()`, `shift_for_comparison("prev_period"|"yoy")`
- **`kpis.py`:** funções puras stateless que recebem `(tenant_id, period)`:
  - Primitivos: `revenue`, `num_sales`, `avg_ticket`, `cash_in`, `cash_out`, `net_profit`, `overdue_rate`
  - Séries por mês: `revenue_by_month`, `cashflow_by_month`, `dre_monthly`
  - Top N: `top_customers`, `top_products`, `sales_by_salesperson`
  - Summaries: `executive_summary`, `financial_summary`, `commercial_summary` (incluem comparação automática)
  - `has_any_data(tenant)` para detectar estado vazio na UI
- **Regras de cálculo:**
  - Faturamento = `Sale.total` com `status='closed'` no período por `issued_at`
  - Cash in/out = `FinancialEntry` `status='paid'` filtrado por `paid_at`
  - Inadimplência% = soma de receivables overdue / soma total receivables não cancelados (por valor)
- **Endpoints:** `GET /api/dashboards/{executive,financial,commercial}` aceitam `?preset=&start=&end=&comparison=`. Sempre retornam `has_data` para a UI.
- **Seed `manage.py seed_demo --tenant <slug>`** popula 12 meses com sazonalidade e crescimento; idempotente.
- **Frontend:**
  - `lib/dashboards.ts` define tipos TS sincronizados com o backend
  - Componentes shared: `KpiCard`, `PeriodFilter`, `EmptyDashboardState`, charts Recharts
  - 3 páginas autenticadas em `/app/dashboards/{executivo,financeiro,comercial}`
  - Cache por preset via TanStack Query

### ADR-009: Sem materialized views por enquanto
**Contexto:** queries de KPI vão direto no Silver com agregações Django ORM.
**Decisão:** funções puras em `kpis.py`, sem cache/MVs. Performance adequada até ~100k vendas em Postgres. MVs entram quando aparecer gargalo.
**Trade-off:** queries podem ficar lentas se tenant tiver milhões de linhas. Aceitável para começar; refator em `apps.analytics.materialized` quando necessário.

### Bloco 6 a 10
- Pendentes — preencher ao concluir.
