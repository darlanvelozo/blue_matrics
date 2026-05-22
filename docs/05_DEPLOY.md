# Deploy Runbook — BlueMetrics

> Guia operacional para subir o BlueMetrics em produção.

## Visão geral da arquitetura prod

```
   Internet
       │
       ▼
  [Load Balancer / CDN]
       │
       ├──→ frontend (Next.js standalone) :3000
       │
       └──→ backend (gunicorn) :8000
              │
              ├──→ Postgres (managed)
              ├──→ Redis (managed)
              └──→ Stripe / Conta Azul / Anthropic (outbound)

  [Celery worker]  ←─── mesmo image do backend, CMD diferente
  [Celery beat]    ←─── opcional, agendamentos
```

## Hospedagem recomendada (ordem de simplicidade)

| Plataforma | Backend | Frontend | DB | Redis | Custo inicial |
|---|---|---|---|---|---|
| **Fly.io** | `fly launch` | `fly launch` | Fly Postgres ou Supabase | Upstash Redis | $5–15/mês |
| **Render** | Web Service | Web Service | Render Postgres | Render Redis | $7–25/mês |
| **Railway** | Service | Service | Plugin Postgres | Plugin Redis | $5–20/mês |
| AWS (ECS+RDS+ElastiCache) | ECS | CloudFront+S3 ou ECS | RDS | ElastiCache | $30–100/mês |

Para validar o produto, **Fly.io ou Render** são suficientes.

## Variáveis de ambiente obrigatórias (produção)

```
DJANGO_SETTINGS_MODULE=bluemetrics.settings.prod
SECRET_KEY=<gerar >=50 chars random>
DEBUG=0
ALLOWED_HOSTS=app.bluemetrics.com.br,api.bluemetrics.com.br
DATABASE_URL=postgres://user:pass@host:5432/bluemetrics
REDIS_URL=redis://default:pass@host:6379/0
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}
FERNET_KEY=<python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">

CORS_ALLOWED_ORIGINS=https://app.bluemetrics.com.br
FRONTEND_URL=https://app.bluemetrics.com.br

# Opcionais (mas recomendados)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
ANTHROPIC_API_KEY=sk-ant-...
SENTRY_DSN=https://...@sentry.io/...
LOG_LEVEL=INFO
LOG_JSON=1

# Por tenant (Conta Azul): preferir BYO credentials via UI em vez de globais
# CONTA_AZUL_CLIENT_ID=
# CONTA_AZUL_CLIENT_SECRET=
CONTA_AZUL_REDIRECT_URI=https://api.bluemetrics.com.br/api/integrations/contaazul/callback
```

## Checklist pré-deploy

- [ ] `pytest` 100% verde no CI
- [ ] `next build` sem erros
- [ ] Postgres provisionado e acessível
- [ ] Redis provisionado
- [ ] DNS A apontando para o load balancer
- [ ] TLS configurado (Let's Encrypt automático nas plataformas listadas)
- [ ] `SECRET_KEY` aleatória (≠ a do dev)
- [ ] `FERNET_KEY` separada (e armazenada em secret manager)
- [ ] Backup automático do Postgres habilitado (mínimo: diário, retenção 7d)
- [ ] Stripe configurado em modo LIVE (não test) com webhook apontando para
      `https://api.bluemetrics.com.br/api/billing/webhook/stripe`
- [ ] Sentry recebendo eventos do backend e do frontend

## Comandos de deploy

### Fly.io (exemplo)

```bash
# Backend
cd backend
fly launch --no-deploy --name bluemetrics-api --region gru
# Configurar volumes e Postgres
fly postgres create --name bluemetrics-db --region gru
fly postgres attach bluemetrics-db -a bluemetrics-api
# Secrets
fly secrets set SECRET_KEY=... FERNET_KEY=... STRIPE_SECRET_KEY=...
fly deploy

# Frontend
cd ../frontend
fly launch --no-deploy --name bluemetrics-app --region gru
fly secrets set NEXT_PUBLIC_API_URL=https://bluemetrics-api.fly.dev
fly deploy
```

### Docker Compose (servidor próprio)

```bash
cd infra
cp ../.env.example .env  # editar
docker compose -f docker-compose.prod.yml up -d
```

## Pós-deploy — smoke

```bash
# liveness
curl https://api.bluemetrics.com.br/healthz

# readiness (DB + Redis)
curl https://api.bluemetrics.com.br/readyz

# status público
curl https://api.bluemetrics.com.br/api/status

# frontend
curl -I https://app.bluemetrics.com.br/
```

## Operação contínua

### Migrations

```bash
fly ssh console -a bluemetrics-api -C "python manage.py migrate"
```

### Criar superuser

```bash
fly ssh console -a bluemetrics-api \
  -C "python manage.py createsuperuser --email admin@bluemetrics.com.br"
```

### Rotação de FERNET_KEY (se necessário)

1. Gerar nova key
2. Atualizar `FERNET_KEY_OLD=<atual>` e `FERNET_KEY=<nova>` (não implementado por
   padrão — exige adaptar `crypto.py` para tentar decrypt com várias chaves)
3. Rodar comando que re-criptografa todas as `ContaAzulConnection.access_token_enc`
4. Remover `FERNET_KEY_OLD`

### Backup Postgres

- Fly/Render/Railway: backup automático ativado por padrão (verificar retenção).
- Manual: `pg_dump $DATABASE_URL | gzip > backup-$(date +%F).sql.gz`

## Observabilidade

- **Logs**: stdout (JSON quando `LOG_JSON=1`); coletar via Fly Log Shipper, Render Logs, ou agregador externo (Datadog, Logtail)
- **Métricas**: `/api/status` agrega health das integrações
- **Erros**: Sentry (configurar DSN, capturar 5xx, alertar via Slack)
- **Uptime**: monitorar `/readyz` (Uptime Robot, Better Stack, Pingdom)

## Em caso de incidente

1. `curl /readyz` — verificar qual dependência está degradada (DB / Redis)
2. Sentry — ver últimos erros agregados
3. Logs estruturados — filtrar por `request_id` para reconstruir uma requisição
4. Admin SaaS (`/admin-saas`) — checar tenants afetados e MRR
5. Stripe Dashboard — confirmar pagamentos / webhooks falhando

## Disaster Recovery

| Cenário | Ação | RTO | RPO |
|---|---|---|---|
| DB corrompido | Restaurar último backup | 1h | 24h |
| Stripe down | Sistema continua, apenas billing pausa | 0 | 0 |
| Conta Azul down | Sync falha graceful; dashboards mostram dados em cache | 0 | última sync |
| Região da nuvem down | Re-deploy em outra região (precisa replicação de DB) | 4h+ | 24h |

## Checklist de segurança contínua

- [ ] `bandit -r backend/` zero high a cada PR
- [ ] `pip-audit` e `npm audit` mensais
- [ ] Rotação trimestral de `SECRET_KEY` (logs out forçado)
- [ ] Revisão semestral de RLS (quando rodar Postgres com row-level security)
- [ ] Backup `audit_log` em S3/cold storage (retenção 5 anos por LGPD)
