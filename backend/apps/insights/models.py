"""Insights gerados a partir dos dados Silver + histórico de chat IA."""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.tenants.models import TenantScopedModel


class Insight(TenantScopedModel):
    """
    Um insight é uma observação automática sobre os dados do tenant,
    com severidade e narrativa (pode ser gerada por regra determinística
    ou enriquecida via LLM).
    """

    class Kind(models.TextChoices):
        REVENUE_DROP = "revenue_drop", "Queda de faturamento"
        REVENUE_SURGE = "revenue_surge", "Pico de faturamento"
        EXPENSE_SURGE = "expense_surge", "Despesa fora do padrão"
        TOP_CUSTOMER = "top_customer", "Cliente que mais comprou"
        TOP_PRODUCT = "top_product", "Produto mais vendido"
        INACTIVE_CUSTOMER = "inactive_customer", "Cliente inativo"
        OVERDUE_HIGH = "overdue_high", "Inadimplência alta"
        CASH_NEGATIVE = "cash_negative", "Caixa negativo"
        TICKET_DROP = "ticket_drop", "Ticket médio caindo"
        SEASONALITY = "seasonality", "Sazonalidade detectada"
        # Regras baseadas em FinancialEntry (tenants sem Sale, ex.: varejo/restaurante)
        TOP_EXPENSE_CATEGORY = "top_expense_category", "Categoria de maior despesa"
        TOP_REVENUE_CATEGORY = "top_revenue_category", "Categoria de maior receita"
        UPCOMING_PAYABLES = "upcoming_payables", "Compromissos próximos"
        SUPPLIER_CONCENTRATION = "supplier_concentration", "Concentração em fornecedor"
        CASH_IN_TREND = "cash_in_trend", "Tendência de recebimentos"

    class Severity(models.TextChoices):
        INFO = "info", "Informação"
        SUCCESS = "success", "Positivo"
        WARNING = "warning", "Atenção"
        CRITICAL = "critical", "Crítico"

    kind = models.CharField(max_length=32, choices=Kind.choices, db_index=True)
    severity = models.CharField(
        max_length=16, choices=Severity.choices, default=Severity.INFO, db_index=True
    )
    title = models.CharField(max_length=200)
    narrative = models.TextField()
    # Dados estruturados que originaram o insight (valores, períodos, ids)
    data = models.JSONField(default=dict, blank=True)
    # Período coberto pelo insight
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    # LLM (futuro): origem narrativa
    generated_by = models.CharField(max_length=32, default="rules")  # rules | llm

    read_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "-created_at"]),
            models.Index(fields=["tenant", "kind", "-created_at"]),
        ]
        constraints = [
            # evita duplicar o mesmo insight no mesmo dia (idempotente)
            models.UniqueConstraint(
                fields=["tenant", "kind", "period_start", "period_end"],
                name="uniq_insight_per_period",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.severity}] {self.title}"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None


# ---------------------------------------------------------------------------
# Histórico do chat IA — uma "conversa" agrupa pergunta+resposta+pergunta...
# Escopo: por (tenant, user) — cada usuário do tenant tem suas conversas.
# ---------------------------------------------------------------------------
class ChatSession(TenantScopedModel):
    """Uma conversa do chat IA. Auto-titulada a partir da primeira pergunta."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
    )
    title = models.CharField(max_length=200, blank=True, default="Nova conversa")

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["tenant", "user", "-updated_at"]),
        ]

    def __str__(self) -> str:
        return f"ChatSession({self.user_id}, {self.title[:30]})"


class ChatMessage(models.Model):
    """Mensagem individual dentro de uma ChatSession."""

    class Role(models.TextChoices):
        USER = "user", "Usuário"
        ASSISTANT = "assistant", "Assistente"

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages",
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    # Metadados da resposta do assistente (vazio em mensagens do usuário)
    blueprint = models.JSONField(null=True, blank=True)
    tools_called = models.JSONField(null=True, blank=True)
    used_llm = models.BooleanField(default=False)
    llm_provider = models.CharField(max_length=32, blank=True, default="")
    llm_error = models.CharField(max_length=64, blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:50]}"
