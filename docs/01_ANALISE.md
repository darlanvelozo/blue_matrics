# Análise do Prompt — BlueMetrics

## 1. Resumo executivo

Plataforma SaaS multi-tenant de **BI as a Service** focada em empresas que usam o ERP **Conta Azul**. Conecta via OAuth2, sincroniza dados financeiros/comerciais, armazena em banco próprio e entrega dashboards + insights gerados por IA. Inclui landing page, billing recorrente (Stripe), painel admin SaaS, modo demo, exportações e onboarding guiado.

Nome provisório: **BlueMetrics**.

## 2. Personas

- **PME (cliente final):** dono / gestor financeiro / comercial de PMEs que já usam Conta Azul. Não-técnico. Quer ver indicadores sem mexer em Power BI.
- **Admin SaaS (nós):** acompanha MRR, churn, tenants ativos, suporte.
- **Visitante:** acessa landing page, vê demo, contrata trial.

## 3. Casos de uso prioritários (MVP)

1. Visitante chega na landing, contrata trial de 7 dias.
2. Cadastro → onboarding guiado → conexão Conta Azul (OAuth2).
3. Sync inicial dispara em background; usuário vê progresso.
4. Dashboard executivo carrega com faturamento, lucro, despesas, crescimento.
5. Dashboards financeiro/comercial detalhados.
6. Insight IA: "Faturamento caiu 12% vs mês passado. Clientes X, Y, Z não compraram."
7. Resumo executivo diário por e-mail.
8. Trial expira → cobrança Stripe → assinatura ativa.

## 4. Requisitos funcionais

### 4.1 Identidade & Multi-tenancy
- Cadastro com e-mail/senha + Google (futuro).
- Cada empresa = 1 **tenant** isolado.
- Cada tenant tem N usuários com papéis (owner, admin, viewer).
- Middleware aplica filtro automático por tenant em TODA query.
- Row-Level Security (RLS) no Postgres como defesa em profundidade.

### 4.2 Integração Conta Azul
- OAuth2 Authorization Code (`https://auth.contaazul.com/oauth2/authorize` + `/token`).
- Base: `https://api-v2.contaazul.com/v1/`.
- Scope fixo: `openid+profile+aws.cognito.signin.user.admin`.
- Token criptografado em repouso (Fernet com chave do env).
- Refresh automático antes do `expires_in`.
- Worker Celery com retry exponencial e tratamento de 429.
- Logs de sincronização (início/fim/erros por recurso).
- Recursos a sincronizar: pessoas (clientes), vendas, produtos, financeiro (contas a pagar/receber), categorias, vendedores.

### 4.3 ETL & Modelagem
- **Bronze:** raw JSON exatamente como veio da API (auditável).
- **Silver:** tabelas normalizadas tipadas (Sale, Customer, Product, FinancialEntry…).
- **Gold:** agregações para dashboards (materialized views) — faturamento mensal, top clientes, top produtos, DRE, ticket médio etc.
- Sync incremental por timestamp/cursor onde a API suporta.

### 4.4 Dashboards
- **Executivo:** faturamento, lucro, despesas, crescimento MoM/YoY, metas.
- **Financeiro:** fluxo de caixa, AP, AR, inadimplência, projeções, DRE visual, despesas por categoria.
- **Comercial:** vendas por vendedor, por período, ranking, ticket médio, top produtos.
- **Filtros:** período, comparação (MoM, YoY), categoria, vendedor.
- **Exportação:** PDF / Excel.

### 4.5 Insights IA
- Engine de regras (anomalias estatísticas: z-score, queda %, sazonalidade).
- LLM (Claude Sonnet 4.6) gera narrativa em linguagem natural a partir dos números.
- E-mail diário com resumo executivo (assíncrono).
- Assistant in-app: chat com contexto do tenant para perguntas livres.

### 4.6 Billing
- Stripe Checkout + Webhooks.
- Trial 7 dias sem cartão (configurável).
- Planos: Starter / Growth / Business (diferenciar por nº de usuários, frequência de sync, recursos avançados como IA premium).
- Upgrade/downgrade pró-rateado.
- Bloqueio gracioso após vencimento (banner + acesso read-only 7 dias).

### 4.7 Admin SaaS
- Painel separado (`/admin-saas`) só para superuser.
- KPIs: MRR, ARR, churn, MAU, conversão trial→paid, tenants ativos.
- Listagem de tenants com drill-down.
- Logs de auditoria.

### 4.8 Landing Page
- Hero com headline + CTA "Conecte sua Conta Azul em minutos".
- Demo visual (vídeo curto/mockup animado).
- Seções: benefícios, dashboards (screenshots), integrações, depoimentos, FAQ, pricing.
- Modo demo: dashboard preenchido com dados fake públicos.

### 4.9 Segurança & LGPD
- HTTPS only, HSTS, CSP, X-Frame-Options, etc.
- Rate limiting (django-ratelimit / nginx).
- Audit log (django-auditlog) para ações sensíveis.
- Criptografia em repouso de tokens OAuth.
- Endpoints LGPD: exportar dados, anonimizar, excluir conta.
- Política de retenção configurável.
- Cookies banner (consentimento).

### 4.10 Observabilidade
- Logs estruturados JSON.
- Health checks (`/healthz`, `/readyz`).
- Métricas Prometheus (opcional).
- Sentry para errors.
- Celery beat heartbeat.

## 5. Melhorias propostas ao prompt original

| # | Original | Proposta | Motivo |
|---|---|---|---|
| 1 | "estoque (se disponível)" | Mantemos como opcional — só sincroniza se o tenant tiver módulo de estoque na Conta Azul | API v2 não garante estoque para todos os planos |
| 2 | Stripe direto | Adicionar **Stripe + Asaas/Pagar.me como fallback BRL** num bloco futuro | Mercado BR usa muito boleto/PIX; Stripe BR ainda é limitado em alguns casos. Para MVP, ficamos com Stripe (BRL suportado) |
| 3 | "envio de insights por e-mail" | Padronizar e-mail transacional via **Resend** (ou SendGrid) e templates MJML | Profissionalismo + deliverability |
| 4 | Onboarding guiado | Usar lib **driver.js** (frontend) + checklist persistido | UX premium |
| 5 | Multi-tenant "isolamento lógico" | Combinar `tenant_id` em todas as tabelas **+ RLS Postgres** | Defesa em profundidade, evita bug humano vazar tenant |
| 6 | "dashboard fake para visitantes" | Implementar como **tenant_id="demo"** seedado com dados sintéticos | Reusa todo o stack, sem código paralelo |
| 7 | "exportação PDF/Excel" | PDF via WeasyPrint (server-side renderiza dashboard como HTML→PDF); Excel via openpyxl | Reusa templates HTML |
| 8 | Cobertura de testes não mencionada | Definir alvo: **>=80% backend, smoke + e2e críticos no front** | Qualidade enterprise |
| 9 | Refresh de token Conta Azul | Job dedicado roda 5min antes de expirar; fallback re-auth via e-mail ao owner | Resiliência |
| 10 | Falta versionamento de schema dos dados Conta Azul | Adicionar tabela `raw_payloads` (Bronze) com versão de schema | Permite reprocessar quando lógica mudar |
| 11 | "metas" | Modelar como entidade `Goal` (tipo, período, valor, dimensão) com check automático | Reusável em vários dashboards |
| 12 | Naming "BlueMetrics" | Mantemos como provisório. Validar antes de marketing final (domínio, marca registrada) | Risco legal |

## 6. Riscos e mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Mudança na API v2 da Conta Azul | Quebra de sync | Camada Bronze guarda raw; adapter isolado em `services/contaazul/` |
| Rate limit não documentado | Sync trava | Token-bucket cliente + retry exponencial + backoff respeitando `Retry-After` |
| Vazamento entre tenants | Crítico LGPD | RLS Postgres + middleware + testes específicos por tenant |
| Custo LLM cresce | Margem caída | Cache de insights + limites por plano + fallback para regras determinísticas |
| Trial fraude (múltiplos cadastros) | Custo | Validação por CNPJ único + e-mail confirmado |

## 7. Premissas

- Cliente já tem conta na Conta Azul ativa.
- Plataforma é PT-BR primeiro (i18n preparado mas só pt-BR no MVP).
- Hospedagem futura: AWS/Render/Fly.io (não escopado neste momento — Docker-ready).
- Tenant tem 1 conexão Conta Azul. Múltiplas conexões = bloco futuro.

## 8. Não-escopo do MVP

- App mobile nativo (web responsivo cobre).
- Conectores para outros ERPs (Omie, Bling, Tiny).
- White-label.
- Marketplace de dashboards.
