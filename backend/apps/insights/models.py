"""Insights gerados a partir dos dados Silver."""
from __future__ import annotations

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
