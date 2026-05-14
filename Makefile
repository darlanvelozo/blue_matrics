# BlueMetrics — Makefile
# Atalhos de desenvolvimento. Execute `make help` para ver os comandos.

SHELL := /bin/bash
COMPOSE := docker compose -f infra/docker-compose.yml --env-file .env

.DEFAULT_GOAL := help

# ----------------------------------------------------------------
# Help
# ----------------------------------------------------------------
.PHONY: help
help: ## Mostra esta ajuda
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?##/ {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ----------------------------------------------------------------
# Infra (Bloco 0)
# ----------------------------------------------------------------
.PHONY: up down ps logs psql redis-cli
up: ## Sobe Postgres + Redis em background
	$(COMPOSE) up -d postgres redis

down: ## Derruba todos os containers
	$(COMPOSE) down

ps: ## Lista status dos containers
	$(COMPOSE) ps

logs: ## Tail logs dos containers
	$(COMPOSE) logs -f

psql: ## Abre psql no banco de dev
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-bluemetrics} -d $${POSTGRES_DB:-bluemetrics}

redis-cli: ## Abre redis-cli
	$(COMPOSE) exec redis redis-cli

# ----------------------------------------------------------------
# Backend (a partir do Bloco 1)
# ----------------------------------------------------------------
.PHONY: backend backend-shell backend-test backend-migrate backend-makemigrations backend-lint backend-fmt
backend: ## Sobe o backend Django (dev)
	$(COMPOSE) up backend

backend-shell: ## Abre shell Python no backend
	cd backend && python manage.py shell

backend-test: ## Roda pytest no backend
	cd backend && pytest -v

backend-migrate: ## Aplica migrations
	cd backend && python manage.py migrate

backend-makemigrations: ## Gera migrations
	cd backend && python manage.py makemigrations

backend-lint: ## Lint backend (ruff + mypy)
	cd backend && ruff check . && mypy .

backend-fmt: ## Formata backend (black + ruff --fix)
	cd backend && black . && ruff check . --fix

# ----------------------------------------------------------------
# Frontend (a partir do Bloco 2)
# ----------------------------------------------------------------
.PHONY: frontend frontend-test frontend-lint frontend-fmt frontend-build
frontend: ## Sobe o frontend Next.js (dev)
	cd frontend && pnpm dev

frontend-test: ## Roda testes Vitest
	cd frontend && pnpm test

frontend-lint: ## Lint frontend (eslint + tsc)
	cd frontend && pnpm lint && pnpm typecheck

frontend-fmt: ## Formata (prettier)
	cd frontend && pnpm format

frontend-build: ## Build produção
	cd frontend && pnpm build

# ----------------------------------------------------------------
# Utilitários
# ----------------------------------------------------------------
.PHONY: env-check fernet-key
env-check: ## Verifica se .env existe
	@test -f .env && echo "✅ .env presente" || (echo "❌ .env ausente. Rode: cp .env.example .env"; exit 1)

fernet-key: ## Gera uma FERNET_KEY nova para colar no .env
	@python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null \
		|| docker run --rm python:3.12-slim sh -c "pip install -q cryptography && python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
