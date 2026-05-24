"""
Sincroniza o catálogo de planos (modelo `Plan`) com o Stripe.

- Cria UM produto "BI AZUL" (reutiliza pelo nome).
- Para cada Plan ativo cria/reusa um Price via lookup_key (`biazul_<code>_brl`).
  Preço/intervalo divergente → desativa o antigo e cria um novo.
- Grava `stripe_price_id` no Plan local.
- Arquiva produtos legados (Starter/Growth/Business) que sobraram no Stripe.

Idempotente: pode rodar quantas vezes quiser.
Suporta intervalos compostos: usa `interval_count` direto do model
(ex: month + count=6 → plano semestral).

Uso:
    python manage.py sync_stripe_plans            # cria/sincroniza
    python manage.py sync_stripe_plans --dry-run  # mostra o que faria
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.billing.models import Plan

logger = logging.getLogger(__name__)


PRODUCT_NAME = "BI AZUL"
PRODUCT_DESCRIPTION = (
    "Copiloto financeiro com IA para PMEs brasileiras integrado à Conta Azul."
)

# lookup_keys legados que devem ser desativados em qualquer sync
LEGACY_LOOKUPS = ["biazul_starter", "biazul_growth", "biazul_business"]


def _lookup_key(code: str) -> str:
    return f"biazul_{code}_brl"


class Command(BaseCommand):
    help = "Sincroniza planos do catálogo (Plan) com Stripe."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="Mostra ações sem executar."
        )

    def handle(self, *args, **opts):
        dry = bool(opts.get("dry_run"))
        key = (getattr(settings, "STRIPE_SECRET_KEY", "") or "").strip()
        if not key or key.startswith("change-me"):
            raise CommandError(
                "STRIPE_SECRET_KEY não está setada. Configure em .env antes de rodar."
            )
        try:
            import stripe  # type: ignore[import-untyped]
        except ImportError as e:
            raise CommandError("stripe SDK não instalado. Rode: pip install stripe") from e
        stripe.api_key = key

        mode = "LIVE" if key.startswith("sk_live") else "TEST"
        self.stdout.write(self.style.NOTICE(
            f"Stripe mode: {key[:10]}… ({mode})  dry_run={dry}"
        ))

        # 1) Produto único
        product = self._find_or_create_product(stripe, dry=dry)

        # 2) Para cada Plan ativo, garante o Price no Stripe e grava o id
        active_plans = list(Plan.objects.filter(is_active=True).order_by("sort_order"))
        if not active_plans:
            self.stdout.write(self.style.WARNING(
                "Nenhum Plan ativo encontrado. Rode as data migrations antes."
            ))
            return

        for plan in active_plans:
            price_id = self._upsert_price_for_plan(
                stripe,
                plan=plan,
                product_id=product.id if product else "(pending)",
                dry=dry,
            )
            if not dry and price_id:
                Plan.objects.filter(pk=plan.pk).update(stripe_price_id=price_id)
                self.stdout.write(self.style.SUCCESS(
                    f"  → Plan.{plan.code}.stripe_price_id = {price_id}"
                ))

        # 3) Arquiva produtos legados
        self._archive_legacy_products(
            stripe, keep_product_id=product.id if product else None, dry=dry,
        )

        self.stdout.write(self.style.SUCCESS("Pronto."))

    # ----------------------------------------------------------------------
    def _find_or_create_product(self, stripe, *, dry: bool):
        prods = stripe.Product.list(active=True, limit=100).data
        existing = next((p for p in prods if p.name == PRODUCT_NAME), None)
        if existing:
            self.stdout.write(f"  produto: reuso {existing.id} ({existing.name})")
            return existing
        if dry:
            self.stdout.write(self.style.WARNING(
                f"  [dry] criaria produto {PRODUCT_NAME!r}"
            ))
            return None
        prod = stripe.Product.create(name=PRODUCT_NAME, description=PRODUCT_DESCRIPTION)
        self.stdout.write(self.style.SUCCESS(f"  produto criado: {prod.id}"))
        return prod

    def _upsert_price_for_plan(
        self, stripe, *, plan: Plan, product_id: str, dry: bool,
    ) -> str | None:
        lookup_key = _lookup_key(plan.code)
        # Stripe trabalha em centavos
        unit_amount = int(round(float(plan.billing_amount) * 100))
        interval = plan.billing_interval
        interval_count = plan.billing_interval_count or 1
        nickname = f"BI AZUL — {plan.name}"

        existing = stripe.Price.list(lookup_keys=[lookup_key], active=True, limit=1).data
        if existing:
            price = existing[0]
            same = (
                price.unit_amount == unit_amount
                and price.currency == "brl"
                and price.recurring
                and price.recurring.interval == interval
                and (price.recurring.interval_count or 1) == interval_count
            )
            if same:
                self.stdout.write(
                    f"  preço[{lookup_key}]: reuso {price.id} "
                    f"({unit_amount/100:.2f} BRL/{interval_count}x{interval})"
                )
                return price.id
            self.stdout.write(self.style.WARNING(
                f"  preço[{lookup_key}]: divergente — desativa e cria novo"
            ))
            if not dry:
                # Stripe não aceita lookup_key=None; renomeia pra liberar a chave
                import time as _t
                stripe.Price.modify(
                    price.id,
                    active=False,
                    lookup_key=f"{lookup_key}_archived_{int(_t.time())}",
                )

        if dry:
            self.stdout.write(self.style.WARNING(
                f"  [dry] criaria price {lookup_key}: "
                f"{unit_amount/100:.2f} BRL/{interval_count}x{interval}"
            ))
            return None

        price = stripe.Price.create(
            product=product_id,
            unit_amount=unit_amount,
            currency="brl",
            recurring={"interval": interval, "interval_count": interval_count},
            lookup_key=lookup_key,
            nickname=nickname,
        )
        self.stdout.write(self.style.SUCCESS(
            f"  preço criado: {price.id} [{lookup_key}] "
            f"{unit_amount/100:.2f} BRL/{interval_count}x{interval}"
        ))
        return price.id

    def _archive_legacy_products(self, stripe, *, keep_product_id: str | None, dry: bool):
        legacy = stripe.Price.list(lookup_keys=LEGACY_LOOKUPS, active=True, limit=10).data
        if not legacy:
            self.stdout.write("  legados: nenhum Price ativo com lookup_keys antigos")
        for price in legacy:
            self.stdout.write(self.style.WARNING(
                f"  legado: desativando price {price.id} ({price.lookup_key})"
            ))
            if not dry:
                import time as _t
                stripe.Price.modify(
                    price.id,
                    active=False,
                    lookup_key=f"{price.lookup_key}_archived_{int(_t.time())}",
                )
            if price.product and price.product != keep_product_id:
                if not dry:
                    try:
                        stripe.Product.modify(price.product, active=False)
                        self.stdout.write(f"    → produto {price.product} arquivado")
                    except Exception as e:  # noqa: BLE001
                        self.stdout.write(self.style.WARNING(
                            f"    ! não foi possível arquivar {price.product}: {e}"
                        ))

        for name in ("Starter", "Growth", "Business"):
            for p in stripe.Product.search(query=f'name:"{name}" AND active:"true"', limit=5).data:
                if p.id == keep_product_id:
                    continue
                self.stdout.write(self.style.WARNING(
                    f"  legado: arquivando produto {p.id} ({p.name})"
                ))
                if not dry:
                    try:
                        stripe.Product.modify(p.id, active=False)
                    except Exception as e:  # noqa: BLE001
                        self.stdout.write(self.style.WARNING(
                            f"    ! falha ao arquivar {p.id}: {e}"
                        ))
