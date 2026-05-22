# BlueMetrics

> SaaS de Inteligência de Dados B2B para empresas que usam o ERP **Conta Azul**.
> Conecta automaticamente, sincroniza dados financeiros/comerciais e entrega dashboards + insights gerados por IA.

🇧🇷 PT-BR · Multi-tenant · Stripe · Conta Azul OAuth2 · Insights com Claude

---

## Documentação

| Documento | Descrição |
|---|---|
| [`docs/01_ANALISE.md`](docs/01_ANALISE.md) | Análise do escopo, personas, requisitos, melhorias propostas |
| [`docs/02_ROADMAP.md`](docs/02_ROADMAP.md) | Roadmap por blocos, status atual, política de testes |
| [`docs/03_CONTEXTO.md`](docs/03_CONTEXTO.md) | Stack, estrutura, ADRs, convenções |

---

## Stack rápida

- **Backend:** Django 5 + DRF · PostgreSQL 16 (RLS) · Redis · Celery · Python 3.12
- **Frontend:** Next.js 15 · TypeScript · Tailwind v4 · shadcn/ui · TanStack Query · Recharts
- **Integrações:** Conta Azul OAuth2 · Stripe · Anthropic Claude · Resend
- **Infra:** Docker · Docker Compose · GitHub Actions

---

## Rodando localmente (dev)

> Requisitos: Docker 24+, Docker Compose v2, GNU Make.

```bash
# 1. Configurar variáveis
cp .env.example .env
# editar .env preenchendo segredos

# 2. Subir infra (Postgres + Redis)
make up

# 3. (após Bloco 1) backend
make backend

# 4. (após Bloco 2) frontend
make frontend
```

URLs locais (após blocos correspondentes):

| Serviço | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Frontend | http://localhost:3000 |
| Postgres | localhost:5432 |
| Redis | localhost:6379 |

---

## Status atual

Veja [`docs/02_ROADMAP.md`](docs/02_ROADMAP.md) para o status detalhado.

- ✅ Bloco 0 — Foundation
- ✅ Bloco 1 — Backend core (Django + multi-tenancy + JWT auth, 16/16 testes)
- ✅ Bloco 2 — Frontend core (Next.js 16 + landing + auth + shell, 7/7 testes)
- ✅ Bloco 3 — Integração Conta Azul (OAuth2 + Fernet + UI, 50/50 testes backend)
- ✅ Bloco 4 — ETL & sync (BYO credentials + Bronze/Silver + cliente HTTP resiliente + UI, 93/93 testes)
- ✅ Bloco 5 — Dashboards & KPIs (3 dashboards + Recharts + seed sintético, 124/124 testes)
- ✅ Bloco 4b — Adapter dev app Conta Azul (BYO redirect + exchange-code + manual-token)
- ✅ Bloco 5b — Auditoria + correções (12 rotas verde, sem 404, TrialBanner, last_12m civis)
- ✅ Bloco 6 — Insights IA (8 regras + UI premium + widget na home, 155/155 testes)
- ✅ Bloco 7 — Billing Stripe (3 planos + trial 7d + mock/real adapter + UI, 180/180 testes)
- ✅ Bloco 8 — Admin SaaS (MRR/churn/tenants + drill-down, 189/189 testes)
- ⏳ Bloco 9 a 10 — pendentes

### Seed de demo

Para popular um tenant com dados sintéticos (12 meses, 2000+ vendas):

```bash
cd backend
DJANGO_SETTINGS_MODULE=bluemetrics.settings.dev .venv/bin/python manage.py seed_demo --tenant <slug>
```

### Como rodar localmente (sem Docker)

**Backend:**
```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 8000
.venv/bin/pytest -v
```

**Frontend** (em outro terminal):
```bash
cd frontend
pnpm install
pnpm dev          # http://localhost:3000
pnpm test         # vitest
```

---

## Licença

Proprietário — todos os direitos reservados.
