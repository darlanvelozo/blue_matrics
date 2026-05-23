# BI AZUL

> Copiloto financeiro e analítico com **IA** para PMEs brasileiras que usam o ERP **Conta Azul**.
> Sincroniza vendas, financeiro, produtos e clientes, e entrega dashboards executivos,
> cards inteligentes, chat conversacional e dashboards adaptáveis sob demanda.

🇧🇷 PT-BR · Multi-tenant · Stripe · Conta Azul v2 · LLM (OpenAI / Anthropic)

> Antigamente chamado **BlueMetrics**. Pasta do repositório continua `blue_matrics/`
> para manter o histórico; o nome de produto é **BI AZUL**.

---

## Documentação

| Documento | Descrição |
|---|---|
| [`docs/01_ANALISE.md`](docs/01_ANALISE.md) | Análise do escopo, personas, requisitos, melhorias propostas |
| [`docs/02_ROADMAP.md`](docs/02_ROADMAP.md) | Roadmap por blocos + fases de redesign (BI AZUL) |
| [`docs/03_CONTEXTO.md`](docs/03_CONTEXTO.md) | Stack, estrutura, ADRs, convenções |
| [`docs/04_AI_COPILOT.md`](docs/04_AI_COPILOT.md) | **NOVO** Arquitetura do módulo IA, endpoints, prompt engineering |
| [`docs/05_DEPLOY.md`](docs/05_DEPLOY.md) | Deploy local (Docker + Cloudflare Tunnel) |
| [`docs/06_CONTA_AZUL_API.md`](docs/06_CONTA_AZUL_API.md) | **NOVO** Mapa de endpoints v2, gotchas e schema descobertos |

---

## Stack

- **Backend:** Django 5 + DRF · PostgreSQL 16 · Redis · Celery · Python 3.12
- **Frontend:** Next.js 16 (App Router) · React 19 · TypeScript · Tailwind v4 · shadcn/ui · TanStack Query · Recharts
- **Integrações:** Conta Azul v2 OAuth2 · Stripe · OpenAI · Anthropic · Resend
- **IA:** OpenAI (`gpt-4o-mini` default) ou Anthropic (`claude-sonnet-4-6`), provider configurável
- **Infra:** Docker · Docker Compose · GitHub Actions · Cloudflare Tunnel (dev público)

---

## Rodando localmente

> Requisitos: Docker 24+, Python 3.12, Node 20+, pnpm 10+, GNU Make.

```bash
# 1. Variáveis
cp .env.example .env
# editar .env: gerar FERNET_KEY, SECRET_KEY; opcional OPENAI_API_KEY

# 2. Infra (Postgres + Redis)
make up      # se docker compose v2 disponível
# OU manualmente:
docker run -d --name bluemetrics-postgres -p 5433:5432 \
  -e POSTGRES_DB=bluemetrics -e POSTGRES_USER=bluemetrics -e POSTGRES_PASSWORD=bluemetrics \
  postgres:16-alpine
# Redis nativo ou docker run redis:7-alpine -p 6379:6379

# 3. Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pip install gunicorn whitenoise openpyxl    # extras necessários
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 8000

# 4. Frontend (em outro terminal)
cd frontend
pnpm install
pnpm dev          # http://localhost:3000
```

URLs locais:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Django Admin: http://localhost:8000/admin

### Variáveis essenciais do .env

```bash
# Django
SECRET_KEY=<gerado>
FERNET_KEY=<gerado: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://bluemetrics:bluemetrics@localhost:5433/bluemetrics
REDIS_URL=redis://localhost:6379/0

# Conta Azul (cadastrar em portaldevs.contaazul.com)
CONTA_AZUL_CLIENT_ID=...
CONTA_AZUL_CLIENT_SECRET=...
CONTA_AZUL_REDIRECT_URI=http://localhost:8000/api/integrations/contaazul/callback

# IA — opcional, mas habilita chat real + enriquecimento de insights
INSIGHT_LLM_PROVIDER=openai   # openai | anthropic | disabled
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

---

## Estado atual

**Arquitetura BI AZUL — Fase 1 entregue (Visão Geral premium)** · Fases 2-5 no [`docs/02_ROADMAP.md`](docs/02_ROADMAP.md).

| Módulo | Status |
|---|---|
| **Visão Geral** (`/app`) | ✅ Premium com Score saúde, cards inteligentes, KPIs financeiros novos (EBITDA, margem líquida, ponto de equilíbrio, burn rate, capital de giro, forecast 30d) |
| **Analista IA** (`/app/ai`) | ✅ Chat livre + dashboard adaptável + modo demo (sem chave) + OpenAI/Anthropic real |
| **Insights** (`/app/insights`) | ✅ 13 regras (5 baseadas em FinancialEntry) + enriquecimento via LLM |
| **Dashboards** Executivo/Financeiro/Comercial | ✅ Funcional (v1) · 🚧 Redesign Fase 2 pendente |
| **Vendas/Clientes/Produtos** | ✅ Reformulados com dados financeiros reais (Customer com RFV/segmentação, Product com estoque, Sales com banner) |
| **Sync Conta Azul v2** | ✅ Endpoints corretos: `/venda/busca`, `/venda/vendedores`, `/financeiro/eventos-financeiros/contas-a-{pagar,receber}/buscar` |
| **Metas, Billing, Sistema** | ✅ Funcional (herdado dos blocos 0-10) |

**Cobertura de testes:** 246/247 (backend), 7/7 (frontend Vitest).

---

## Estrutura

```
blue_matrics/
├── backend/          Django 5 + DRF (15 apps)
│   ├── apps/
│   │   ├── analytics/    KPIs v1 + v2, smart_cards, overview endpoint
│   │   ├── insights/     Regras + LLM adapter (OpenAI/Anthropic) + chat
│   │   ├── sync/         Sync Conta Azul (mappers para v2)
│   │   ├── explorer/     Listagens (customers/products/sales/financial)
│   │   └── ...
│   └── bluemetrics/
├── frontend/         Next.js 16 + React 19
│   ├── src/app/app/      Rotas autenticadas (visão geral, IA, dashboards, dados)
│   ├── src/components/
│   │   ├── overview/     ScoreGauge, SmartCard (novos)
│   │   ├── ai/           BlueprintRender (dashboard dinâmico)
│   │   └── dashboards/   KpiCard, RankingList, charts (reutilizados)
│   └── src/lib/
├── docs/             Documentação técnica + roadmap
├── infra/            docker-compose.yml
└── Makefile          Atalhos make up/backend/frontend/test
```

---

## Login admin (dev)

| Campo | Valor |
|---|---|
| Email | `admin@bluemetrics.local` |
| Senha | `admin123` |

(Criado via `manage.py createsuperuser --noinput` na primeira execução)

---

## Licença

Proprietário — todos os direitos reservados.
