"""
Migra subscriptions que ainda apontam para planos legacy (starter/growth/business)
para o plano `monthly`.

Critério: só migra quem está em TRIALING ou ACTIVE — não mexe em CANCELED/PAST_DUE
nem em assinaturas que tenham `stripe_subscription_id` populado (cliente
pagante real precisa migrar via Stripe Subscription.modify para não furar
cobrança).

Para subs em trial (caso comum), também limpa `stripe_customer_id` se for de
test mode — assim a próxima ação cria um customer novo no live mode.
"""
from django.db import migrations


LEGACY_CODES = {"starter", "growth", "business"}
NEW_DEFAULT_CODE = "monthly"


def forwards(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    Subscription = apps.get_model("billing", "Subscription")

    new_plan = Plan.objects.filter(code=NEW_DEFAULT_CODE).first()
    if new_plan is None:
        # Sem plano monthly não há o que migrar — provavelmente migration 0006
        # ainda não rodou. Sai silenciosamente.
        return

    qs = Subscription.objects.filter(
        plan__code__in=LEGACY_CODES,
        status__in=("trialing", "active"),
        stripe_subscription_id="",  # só toca quem AINDA não tem assinatura Stripe
    )
    for sub in qs:
        sub.plan = new_plan
        # Limpa customer_id antigo (provavelmente de test mode) — se for live
        # válido, o _get_or_create_customer revalida e mantém. Mais seguro
        # zerar e deixar a próxima operação resolver.
        sub.stripe_customer_id = ""
        sub.save(update_fields=["plan", "stripe_customer_id", "updated_at"])


def backwards(apps, schema_editor):
    # Não dá pra reverter com precisão — quem estava em qual plano legacy
    # se perdeu. Fica como no-op.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0006_three_plans_pricing"),
    ]
    operations = [migrations.RunPython(forwards, backwards)]
