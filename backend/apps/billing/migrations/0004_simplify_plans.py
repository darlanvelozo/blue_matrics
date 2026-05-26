"""
Simplifica para 2 planos: Mensal (R$ 499) e Anual (R$ 4.499).
Desativa Starter/Growth/Business (mantidos pra histórico de assinaturas).
"""
from decimal import Decimal
from django.db import migrations


MONTHLY_FEATURES = [
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

ANNUAL_FEATURES = MONTHLY_FEATURES + [
    "Economia de R$ 1.489/ano (~25% off)",
    "Pagamento único anual — sem preocupação mensal",
]


def forwards(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")

    # Desativa legacy
    Plan.objects.filter(code__in=["starter", "growth", "business"]).update(
        is_active=False,
        sort_order=999,
    )

    # Cria/atualiza Mensal
    Plan.objects.update_or_create(
        code="monthly",
        defaults={
            "name": "Mensal",
            "description": (
                "Acesso completo ao BI AZUL com IA, dashboards premium e "
                "sincronização Conta Azul. Cobrança mensal."
            ),
            "price_monthly": Decimal("499.00"),
            "billing_amount": Decimal("499.00"),
            "billing_interval": "month",
            "currency": "BRL",
            "max_users": 999,
            "features": MONTHLY_FEATURES,
            "is_active": True,
            "sort_order": 10,
        },
    )

    # Cria/atualiza Anual
    Plan.objects.update_or_create(
        code="annual",
        defaults={
            "name": "Anual",
            "description": (
                "Mesmo acesso completo do plano Mensal, com 25% de economia. "
                "Cobrança anual única."
            ),
            "price_monthly": Decimal("374.92"),  # 4499/12
            "billing_amount": Decimal("4499.00"),
            "billing_interval": "year",
            "currency": "BRL",
            "max_users": 999,
            "features": ANNUAL_FEATURES,
            "is_active": True,
            "sort_order": 20,
        },
    )


def backwards(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    Plan.objects.filter(code__in=["monthly", "annual"]).delete()
    Plan.objects.filter(code__in=["starter", "growth", "business"]).update(
        is_active=True, sort_order=0,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0003_plan_billing_amount_plan_billing_interval_and_more"),
    ]
    operations = [migrations.RunPython(forwards, backwards)]
