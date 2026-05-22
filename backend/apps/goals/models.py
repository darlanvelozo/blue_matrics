"""
Metas (Goals) — objetivos numéricos que o tenant quer atingir num período.

Suporta 4 tipos de meta:
- revenue (faturamento)
- net_profit (lucro líquido)
- num_sales (quantidade de vendas)
- avg_ticket (ticket médio)

Granularidade:
- month  → target avaliado mês a mês (próximo mês corrente)
- quarter → trimestre
- year → ano

`current_progress()` consulta o KPI correspondente sob demanda.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db import models
from django.utils import timezone

from apps.tenants.models import TenantScopedModel


class Goal(TenantScopedModel):
    class Kind(models.TextChoices):
        REVENUE = "revenue", "Faturamento"
        NET_PROFIT = "net_profit", "Lucro líquido"
        NUM_SALES = "num_sales", "Nº de vendas"
        AVG_TICKET = "avg_ticket", "Ticket médio"

    class Period(models.TextChoices):
        MONTH = "month", "Mensal"
        QUARTER = "quarter", "Trimestral"
        YEAR = "year", "Anual"

    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    period = models.CharField(max_length=10, choices=Period.choices, default=Period.MONTH)
    target_value = models.DecimalField(max_digits=14, decimal_places=2)
    starts_on = models.DateField(default=date.today, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "is_active"]),
            models.Index(fields=["tenant", "kind"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.kind}, {self.period})"

    def current_period_range(self, *, ref: date | None = None) -> tuple[date, date]:
        """Retorna (start, end) do período corrente para a granularidade da meta."""
        ref = ref or timezone.now().date()
        if self.period == self.Period.MONTH:
            start = ref.replace(day=1)
            end = (start + relativedelta(months=1)) - relativedelta(days=1)
        elif self.period == self.Period.QUARTER:
            q_start_month = ((ref.month - 1) // 3) * 3 + 1
            start = ref.replace(month=q_start_month, day=1)
            end = (start + relativedelta(months=3)) - relativedelta(days=1)
        else:  # year
            start = ref.replace(month=1, day=1)
            end = ref.replace(month=12, day=31)
        return start, end

    def current_progress(self, *, ref: date | None = None) -> dict:
        """Calcula valor atual + % de progresso vs target."""
        from apps.analytics.kpis import (
            avg_ticket,
            net_profit,
            num_sales,
            revenue,
        )
        from apps.analytics.periods import Period as AnalyticsPeriod

        start, end = self.current_period_range(ref=ref)
        p = AnalyticsPeriod(start=start, end=end)

        if self.kind == self.Kind.REVENUE:
            current = float(revenue(self.tenant_id, p))
        elif self.kind == self.Kind.NET_PROFIT:
            current = float(net_profit(self.tenant_id, p))
        elif self.kind == self.Kind.NUM_SALES:
            current = float(num_sales(self.tenant_id, p))
        elif self.kind == self.Kind.AVG_TICKET:
            current = float(avg_ticket(self.tenant_id, p))
        else:
            current = 0.0

        target = float(self.target_value or Decimal("0"))
        progress_pct = (current / target * 100) if target > 0 else 0.0
        return {
            "current": current,
            "target": target,
            "progress_pct": min(progress_pct, 999.99),  # cap pra evitar 99999%
            "achieved": progress_pct >= 100,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
        }
