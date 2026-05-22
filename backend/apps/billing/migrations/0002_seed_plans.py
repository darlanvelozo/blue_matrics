"""Seed do catálogo de planos (Starter / Growth / Business)."""
from decimal import Decimal

from django.db import migrations


PLANS = [
    {
        "code": "starter",
        "name": "Starter",
        "description": "Para times pequenos que estão começando.",
        "price_monthly": Decimal("99.00"),
        "max_users": 1,
        "features": [
            "1 usuário",
            "Dashboards essenciais",
            "Sync diário",
            "Suporte por e-mail",
        ],
        "sort_order": 10,
    },
    {
        "code": "growth",
        "name": "Growth",
        "description": "Para empresas em crescimento que querem insights.",
        "price_monthly": Decimal("249.00"),
        "max_users": 5,
        "features": [
            "Até 5 usuários",
            "Todos os dashboards",
            "Sync de hora em hora",
            "Insights por IA",
            "Exportação PDF/Excel",
        ],
        "sort_order": 20,
    },
    {
        "code": "business",
        "name": "Business",
        "description": "Para operações que dependem de dados em tempo real.",
        "price_monthly": Decimal("499.00"),
        "max_users": 999,
        "features": [
            "Usuários ilimitados",
            "Sync em tempo real",
            "Insights premium + assistente IA",
            "API & Webhooks",
            "Suporte prioritário",
        ],
        "sort_order": 30,
    },
]


def seed_plans(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    for p in PLANS:
        Plan.objects.update_or_create(code=p["code"], defaults={**p, "is_active": True})


def unseed_plans(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    Plan.objects.filter(code__in=[p["code"] for p in PLANS]).delete()


class Migration(migrations.Migration):
    dependencies = [("billing", "0001_initial")]
    operations = [migrations.RunPython(seed_plans, reverse_code=unseed_plans)]
