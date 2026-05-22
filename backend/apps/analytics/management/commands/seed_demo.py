"""
Popula um tenant com dados sintéticos realistas para demonstrar dashboards.

Uso:
    manage.py seed_demo --tenant <slug>   # popula tenant existente
    manage.py seed_demo --new "Padaria Demo"   # cria tenant + dados
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify

from apps.sync.models import (
    Category,
    Customer,
    FinancialEntry,
    Product,
    Sale,
    SaleItem,
    Salesperson,
)
from apps.tenants.context import set_current_tenant
from apps.tenants.models import Tenant

PRODUCTS = [
    ("Pão Francês kg", "PAO-FRA", 18.00, 6.00),
    ("Pão de Queijo unid", "PAO-Q", 3.50, 1.20),
    ("Bolo de Chocolate", "BOL-CHO", 45.00, 18.00),
    ("Croissant", "CRO-01", 8.00, 3.00),
    ("Café espresso", "CAF-ESP", 6.00, 1.50),
    ("Suco natural 300ml", "SUC-300", 12.00, 4.00),
    ("Sanduíche presunto", "SAN-PRE", 14.00, 5.00),
    ("Torta de frango fatia", "TOR-FRA", 16.00, 6.00),
]

CUSTOMERS = [
    "João Silva", "Maria Santos", "Pedro Oliveira", "Ana Costa",
    "Carlos Souza", "Beatriz Lima", "Rafael Pereira", "Fernanda Alves",
    "Lucas Mendes", "Patricia Rocha", "Mercearia do Zé", "Café da Esquina",
    "Bufê Sabor & Arte", "Padaria Concorrente Ltda",
]

SALESPEOPLE = ["Mariana", "Diego", "Patrícia"]

EXPENSE_CATS = [
    ("Aluguel", "expense"),
    ("Energia", "expense"),
    ("Folha de pagamento", "expense"),
    ("Insumos", "expense"),
    ("Manutenção", "expense"),
]
REVENUE_CATS = [
    ("Vendas", "revenue"),
    ("Serviços", "revenue"),
]


class Command(BaseCommand):
    help = "Popula um tenant com dados sintéticos realistas (12 meses)."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument("--tenant", help="Slug do tenant existente")
        parser.add_argument("--new", help="Nome de um novo tenant a criar")
        parser.add_argument("--seed", type=int, default=42, help="Random seed (reprodutível)")
        parser.add_argument("--months", type=int, default=12)

    def handle(self, *args, **opts):  # type: ignore[no-untyped-def]
        random.seed(opts["seed"])

        if opts["tenant"]:
            try:
                tenant = Tenant.objects.get(slug=opts["tenant"])
            except Tenant.DoesNotExist as e:
                raise CommandError(f"Tenant '{opts['tenant']}' não existe.") from e
        elif opts["new"]:
            name = opts["new"]
            tenant = Tenant.objects.create(name=name, slug=slugify(name))
        else:
            raise CommandError("Use --tenant <slug> ou --new <nome>")

        months = int(opts["months"])
        self.stdout.write(self.style.NOTICE(f"Seeding tenant '{tenant.slug}' ({months}m)..."))

        with set_current_tenant(tenant.id):
            self._wipe(tenant)
            self._seed(tenant, months=months)

        self.stdout.write(self.style.SUCCESS(f"✅ Tenant '{tenant.slug}' populado."))

    # ---------------------------------------------------------------
    def _wipe(self, tenant: Tenant) -> None:
        """Limpa dados de domínio (não toca em config/auth) para idempotência."""
        SaleItem.unsafe_objects.filter(tenant_id=tenant.id).delete()
        Sale.unsafe_objects.filter(tenant_id=tenant.id).delete()
        FinancialEntry.unsafe_objects.filter(tenant_id=tenant.id).delete()
        Customer.unsafe_objects.filter(tenant_id=tenant.id).delete()
        Product.unsafe_objects.filter(tenant_id=tenant.id).delete()
        Salesperson.unsafe_objects.filter(tenant_id=tenant.id).delete()
        Category.unsafe_objects.filter(tenant_id=tenant.id).delete()

    def _seed(self, tenant: Tenant, *, months: int) -> None:
        # Categorias
        cats = {}
        for name, kind in REVENUE_CATS + EXPENSE_CATS:
            cat = Category.unsafe_objects.create(
                tenant_id=tenant.id,
                external_id=f"cat-{slugify(name)}",
                name=name,
                kind=kind,
            )
            cats[name] = cat

        # Vendedores
        salespeople = []
        for i, name in enumerate(SALESPEOPLE):
            sp = Salesperson.unsafe_objects.create(
                tenant_id=tenant.id, external_id=f"sp-{i}", name=name
            )
            salespeople.append(sp)

        # Produtos
        products = []
        for sku_idx, (name, sku, price, cost) in enumerate(PRODUCTS):
            p = Product.unsafe_objects.create(
                tenant_id=tenant.id,
                external_id=f"prod-{sku_idx}",
                sku=sku,
                name=name,
                price=Decimal(str(price)),
                cost=Decimal(str(cost)),
            )
            products.append(p)

        # Clientes
        customers = []
        for i, name in enumerate(CUSTOMERS):
            c = Customer.unsafe_objects.create(
                tenant_id=tenant.id,
                external_id=f"cli-{i}",
                name=name,
                document=f"{10000000000 + i:011d}",
                email=f"{slugify(name)}@example.com",
            )
            customers.append(c)

        # Vendas — 12 meses, com sazonalidade e crescimento leve
        today = timezone.now().date()
        first_month = today.replace(day=1) - relativedelta(months=months - 1)

        for m in range(months):
            month_start = first_month + relativedelta(months=m)
            # crescimento de 1.5%/mês com ruído
            base_growth = (1.015) ** m
            # sazonalidade: dezembro 1.6x, janeiro 0.7x
            month_idx = month_start.month
            seasonal = {12: 1.6, 1: 0.7, 6: 1.15}.get(month_idx, 1.0)
            # Ruído aleatório p/ variação MoM realista (insights precisam de >10/15%)
            noise = random.uniform(0.65, 1.35)
            target_revenue = Decimal(str(45000 * base_growth * seasonal * noise))

            # FORÇA queda no mês passado vs retrasado pra demonstrar o insight de
            # revenue_drop em dev. Sem isso, é roleta se o seed gera variação >10%.
            today_real = timezone.now().date()
            first_last_month = (today_real.replace(day=1) - relativedelta(months=1))
            if month_start == first_last_month:
                target_revenue = Decimal(str(float(target_revenue) * 0.78))  # -22%

            self._seed_month_sales(tenant, month_start, target_revenue, products, customers, salespeople)
            self._seed_month_financial(tenant, month_start, cats, customers)

    def _seed_month_sales(self, tenant, month_start, target_revenue, products, customers, salespeople):  # type: ignore[no-untyped-def]
        accumulated = Decimal("0")
        sale_idx = 0
        last_day = (month_start + relativedelta(months=1)) - timedelta(days=1)
        # cap pra não estourar (1500 suficiente pra realistically atingir target)
        while accumulated < target_revenue and sale_idx < 1500:
            sale_idx += 1
            day_offset = random.randint(0, (last_day - month_start).days)
            sale_date = datetime.combine(
                month_start + timedelta(days=day_offset),
                datetime.min.time().replace(hour=random.randint(8, 19)),
            )
            sale_date = timezone.make_aware(sale_date)

            cust = random.choice(customers)
            sp = random.choice(salespeople)
            item_count = random.choices([1, 2, 3, 4], weights=[5, 4, 3, 1])[0]
            chosen = random.sample(products, k=min(item_count, len(products)))

            sale_total = Decimal("0")
            sale = Sale.unsafe_objects.create(
                tenant_id=tenant.id,
                external_id=f"sale-{tenant.id}-{month_start.month:02d}-{sale_idx}",
                number=f"{month_start.strftime('%y%m')}{sale_idx:04d}",
                customer=cust,
                salesperson=sp,
                status=Sale.Status.CLOSED,
                issued_at=sale_date,
                total=Decimal("0"),
                discount=Decimal("0"),
            )
            for prod in chosen:
                qty = Decimal(str(random.choices([1, 2, 3, 5, 10], weights=[5, 3, 2, 1, 1])[0]))
                total = (prod.price * qty).quantize(Decimal("0.01"))
                SaleItem.unsafe_objects.create(
                    tenant_id=tenant.id,
                    sale=sale,
                    product=prod,
                    external_id=f"si-{sale.id}-{prod.id}",
                    description=prod.name,
                    quantity=qty,
                    unit_price=prod.price,
                    total=total,
                )
                sale_total += total
            sale.total = sale_total
            sale.save(update_fields=["total"])
            accumulated += sale_total

    def _seed_month_financial(self, tenant, month_start, cats, customers):  # type: ignore[no-untyped-def]
        last_day = (month_start + relativedelta(months=1)) - timedelta(days=1)
        today = timezone.now().date()

        # Receitas (pagas)
        # cria 5 receitas distribuídas no mês, refletindo o caixa entrando
        for i in range(5):
            day = month_start + timedelta(days=random.randint(0, (last_day - month_start).days))
            FinancialEntry.unsafe_objects.create(
                tenant_id=tenant.id,
                external_id=f"ar-{tenant.id}-{month_start.month:02d}-{i}",
                direction=FinancialEntry.Direction.RECEIVABLE,
                status=FinancialEntry.Status.PAID,
                description=f"Recebimento {month_start.strftime('%b')}",
                amount=Decimal(str(random.uniform(4000, 12000))).quantize(Decimal("0.01")),
                due_date=day,
                paid_at=day,
                category=cats["Vendas"],
                customer=random.choice(customers),
            )

        # Alguns receivables ainda em aberto / overdue para gerar inadimplência
        if month_start >= (today - relativedelta(months=3)).replace(day=1):
            for i in range(2):
                day = month_start + timedelta(days=random.randint(0, (last_day - month_start).days))
                FinancialEntry.unsafe_objects.create(
                    tenant_id=tenant.id,
                    external_id=f"ar-pend-{tenant.id}-{month_start.month:02d}-{i}",
                    direction=FinancialEntry.Direction.RECEIVABLE,
                    status=FinancialEntry.Status.PENDING,
                    description="A receber",
                    amount=Decimal(str(random.uniform(800, 2500))).quantize(Decimal("0.01")),
                    due_date=day,
                    category=cats["Vendas"],
                    customer=random.choice(customers),
                )

        # Despesas pagas
        expense_base = {
            "Aluguel": 6000,
            "Energia": 1200,
            "Folha de pagamento": 15000,
            "Insumos": 8000,
            "Manutenção": 800,
        }
        for cat_name, base in expense_base.items():
            day = month_start + timedelta(days=random.randint(0, (last_day - month_start).days))
            FinancialEntry.unsafe_objects.create(
                tenant_id=tenant.id,
                external_id=f"ap-{tenant.id}-{month_start.month:02d}-{cat_name}",
                direction=FinancialEntry.Direction.PAYABLE,
                status=FinancialEntry.Status.PAID,
                description=cat_name,
                amount=Decimal(str(random.uniform(base * 0.9, base * 1.1))).quantize(Decimal("0.01")),
                due_date=day,
                paid_at=day,
                category=cats[cat_name],
            )
