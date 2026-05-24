"""
Re-precifica catálogo para 3 planos:
- Mensal:    R$ 299,90/mês
- Semestral: R$ 1.649,45 a cada 6 meses (R$ 274,91/mês — 8% off)
- Anual:     R$ 2.999,00/ano (R$ 249,92/mês — 17% off)

Plans antigos (starter/growth/business) já desativados pela 0004 continuam.
O `monthly` e `annual` da 0004 são re-precificados; `semestral` é novo.
"""
from decimal import Decimal
from django.db import migrations


SHARED_FEATURES = [
    "Todos os dashboards (Visão geral, Executivo, Financeiro, Comercial)",
    "Analista IA conversacional (function calling com 22 ferramentas)",
    "Insights automáticos com regras + enriquecimento via OpenAI",
    "Previsões de receita, despesa e caixa",
    "Curva ABC, RFV, segmentação de clientes",
    "Sugestão de recompra de produtos",
    "Sincronização com Conta Azul",
    "Exportação Excel/HTML",
    "Suporte por e-mail",
    "Usuários ilimitados",
]


def forwards(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")

    # Mensal — R$ 299,90/mês
    Plan.objects.update_or_create(
        code="monthly",
        defaults={
            "name": "Mensal",
            "description": (
                "Acesso completo ao BI AZUL com IA, dashboards premium e "
                "sincronização Conta Azul. Cobrança mensal."
            ),
            "price_monthly": Decimal("299.90"),
            "billing_amount": Decimal("299.90"),
            "billing_interval": "month",
            "billing_interval_count": 1,
            "currency": "BRL",
            "max_users": 999,
            "features": SHARED_FEATURES,
            "is_active": True,
            "sort_order": 10,
            # stripe_price_id é preenchido pelo `manage.py sync_stripe_plans`
        },
    )

    # Semestral — R$ 1.649,45 a cada 6 meses (R$ 274,91/mês, 8% off)
    Plan.objects.update_or_create(
        code="semestral",
        defaults={
            "name": "Semestral",
            "description": (
                "Pague a cada 6 meses e economize 8%. Mesmo acesso completo do plano Mensal."
            ),
            "price_monthly": Decimal("274.91"),  # 1649.45 / 6
            "billing_amount": Decimal("1649.45"),
            "billing_interval": "month",
            "billing_interval_count": 6,
            "currency": "BRL",
            "max_users": 999,
            "features": [
                *SHARED_FEATURES,
                "Economia de ~8% vs. plano Mensal",
                "Pagamento único semestral",
            ],
            "is_active": True,
            "sort_order": 20,
        },
    )

    # Anual — R$ 2.999,00/ano (R$ 249,92/mês, 17% off)
    Plan.objects.update_or_create(
        code="annual",
        defaults={
            "name": "Anual",
            "description": (
                "Pague 1x por ano e economize 17%. Mesmo acesso completo, sem preocupação."
            ),
            "price_monthly": Decimal("249.92"),  # 2999.00 / 12
            "billing_amount": Decimal("2999.00"),
            "billing_interval": "year",
            "billing_interval_count": 1,
            "currency": "BRL",
            "max_users": 999,
            "features": [
                *SHARED_FEATURES,
                "Economia de ~17% vs. plano Mensal",
                "Pagamento único anual",
            ],
            "is_active": True,
            "sort_order": 30,
        },
    )


def backwards(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    # Volta pra precificação anterior (0004)
    Plan.objects.filter(code="semestral").delete()
    Plan.objects.filter(code="monthly").update(
        billing_amount=Decimal("499.00"),
        price_monthly=Decimal("499.00"),
        billing_interval_count=1,
    )
    Plan.objects.filter(code="annual").update(
        billing_amount=Decimal("4499.00"),
        price_monthly=Decimal("374.92"),
        billing_interval_count=1,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0005_plan_billing_interval_count_and_more"),
    ]
    operations = [migrations.RunPython(forwards, backwards)]
