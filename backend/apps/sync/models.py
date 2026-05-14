"""
Modelos de sincronização — camadas Bronze (raw) e Silver (normalizada).

Convenções:
- Todos os modelos de domínio são `TenantScopedModel` (isolamento por tenant)
- `external_id` é o id na Conta Azul; (tenant, external_id) é único
- Datas vindas da API ficam em campos tipados; raw payload é guardado em Bronze
- Soft-delete não aplicamos por enquanto; usamos `archived_at` quando precisar
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.tenants.models import Tenant, TenantScopedModel


# ============================================================================
# BRONZE — payloads raw da API (auditável, permite reprocessar Silver/Gold)
# ============================================================================
class RawPayload(TenantScopedModel):
    """Payload bruto que veio da API, antes de qualquer transformação."""

    class Resource(models.TextChoices):
        CUSTOMERS = "customers", "Customers (pessoas)"
        SALES = "sales", "Sales"
        PRODUCTS = "products", "Products"
        FINANCIAL_RECEIVABLES = "financial_receivables", "Contas a receber"
        FINANCIAL_PAYABLES = "financial_payables", "Contas a pagar"
        CATEGORIES = "categories", "Categorias"
        SALESPEOPLE = "salespeople", "Vendedores"

    resource = models.CharField(max_length=32, choices=Resource.choices, db_index=True)
    external_id = models.CharField(max_length=128, db_index=True)
    payload = models.JSONField()
    schema_version = models.SmallIntegerField(default=1)
    fetched_at = models.DateTimeField(default=timezone.now)
    sync_log = models.ForeignKey(
        "sync.SyncLog",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payloads",
    )

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "resource", "external_id"]),
            models.Index(fields=["tenant", "resource", "fetched_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "resource", "external_id", "fetched_at"],
                name="uniq_bronze_payload",
            ),
        ]

    def __str__(self) -> str:
        return f"Raw({self.resource}#{self.external_id} @ {self.fetched_at:%Y-%m-%d})"


# ============================================================================
# SILVER — tabelas tipadas
# ============================================================================
class Customer(TenantScopedModel):
    external_id = models.CharField(max_length=128, db_index=True)
    name = models.CharField(max_length=255)
    document = models.CharField(max_length=20, blank=True, default="")  # CNPJ/CPF
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=40, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at_external = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "external_id"], name="uniq_customer_per_tenant"
            ),
        ]
        indexes = [models.Index(fields=["tenant", "name"])]

    def __str__(self) -> str:
        return self.name


class Product(TenantScopedModel):
    external_id = models.CharField(max_length=128, db_index=True)
    sku = models.CharField(max_length=64, blank=True, default="")
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "external_id"], name="uniq_product_per_tenant"
            ),
        ]
        indexes = [models.Index(fields=["tenant", "name"])]

    def __str__(self) -> str:
        return self.name


class Category(TenantScopedModel):
    class Kind(models.TextChoices):
        REVENUE = "revenue", "Receita"
        EXPENSE = "expense", "Despesa"
        OTHER = "other", "Outro"

    external_id = models.CharField(max_length=128, db_index=True)
    name = models.CharField(max_length=255)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.OTHER)
    parent_external_id = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "external_id"], name="uniq_category_per_tenant"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Salesperson(TenantScopedModel):
    external_id = models.CharField(max_length=128, db_index=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "external_id"], name="uniq_salesperson_per_tenant"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Sale(TenantScopedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        OPEN = "open", "Aberta"
        CLOSED = "closed", "Fechada"
        CANCELED = "canceled", "Cancelada"

    external_id = models.CharField(max_length=128, db_index=True)
    number = models.CharField(max_length=40, blank=True, default="")
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name="sales"
    )
    salesperson = models.ForeignKey(
        Salesperson, on_delete=models.SET_NULL, null=True, blank=True, related_name="sales"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    issued_at = models.DateTimeField(null=True, blank=True, db_index=True)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "external_id"], name="uniq_sale_per_tenant"
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "issued_at"]),
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self) -> str:
        return f"Sale #{self.number or self.external_id} R${self.total}"


class SaleItem(TenantScopedModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="sale_items"
    )
    external_id = models.CharField(max_length=128, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    class Meta:
        indexes = [models.Index(fields=["tenant", "sale"])]

    def __str__(self) -> str:
        return f"{self.description or self.product_id} x{self.quantity}"


class FinancialEntry(TenantScopedModel):
    """Lançamento financeiro (conta a pagar/receber)."""

    class Direction(models.TextChoices):
        RECEIVABLE = "receivable", "A receber"
        PAYABLE = "payable", "A pagar"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PAID = "paid", "Pago/Recebido"
        OVERDUE = "overdue", "Atrasado"
        CANCELED = "canceled", "Cancelado"

    external_id = models.CharField(max_length=128, db_index=True)
    direction = models.CharField(max_length=16, choices=Direction.choices, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    description = models.CharField(max_length=255, blank=True, default="")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    due_date = models.DateField(null=True, blank=True, db_index=True)
    paid_at = models.DateField(null=True, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="financial_entries"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name="financial_entries"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "external_id"],
                name="uniq_financial_entry_per_tenant",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "direction", "due_date"]),
            models.Index(fields=["tenant", "status", "due_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.direction} {self.amount} ({self.status})"


# ============================================================================
# SYNC LOG — auditoria de cada execução
# ============================================================================
class SyncLog(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        PARTIAL = "partial", "Partial"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="sync_logs")
    resource = models.CharField(max_length=32, blank=True, default="")  # "" = orquestrador
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    fetched = models.IntegerField(default=0)
    upserted = models.IntegerField(default=0)
    errors = models.IntegerField(default=0)
    cursor = models.CharField(max_length=128, blank=True, default="")
    message = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "-started_at"]),
            models.Index(fields=["tenant", "resource", "-started_at"]),
        ]

    def __str__(self) -> str:
        return f"SyncLog(t={self.tenant_id}, {self.resource or 'all'}, {self.status})"

    def mark_finished(self, status: str, *, message: str = "") -> None:
        self.status = status
        self.finished_at = timezone.now()
        if message:
            self.message = (message or "")[:5000]
