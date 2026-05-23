"""
Sincroniza o catálogo de planos com Stripe.

Cria (ou reutiliza pelo lookup_key) os Prices Mensal e Anual em BRL, grava
`stripe_price_id` em cada Plan e arquiva produtos legados (Starter/Growth/Business)
no Stripe.

Idempotente: pode rodar quantas vezes quiser. Sempre usa lookup_key estável.

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
LOOKUP_MONTHLY = "biazul_monthly_brl"
LOOKUP_ANNUAL = "biazul_annual_brl"

LEGACY_LOOKUPS = ["biazul_starter", "biazul_growth", "biazul_business"]


class Command(BaseCommand):
    help = "Sincroniza planos do catálogo com Stripe (cria produto/prices, arquiva legados)."

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

        self.stdout.write(self.style.NOTICE(f"Stripe mode: {key[:8]}…  dry_run={dry}"))

        # ------------------------------------------------------------------
        # 1) Produto único (procura por nome; cria se não existir)
        # ------------------------------------------------------------------
        product = self._find_or_create_product(stripe, dry=dry)

        # ------------------------------------------------------------------
        # 2) Prices Mensal + Anual via lookup_key
        # ------------------------------------------------------------------
        monthly_price = self._upsert_price(
            stripe,
            product_id=product.id if product else "(pending)",
            lookup_key=LOOKUP_MONTHLY,
            nickname="BI AZUL — Mensal",
            unit_amount=49900,  # R$ 499 em centavos
            interval="month",
            dry=dry,
        )
        annual_price = self._upsert_price(
            stripe,
            product_id=product.id if product else "(pending)",
            lookup_key=LOOKUP_ANNUAL,
            nickname="BI AZUL — Anual",
            unit_amount=449900,  # R$ 4.499 em centavos
            interval="year",
            dry=dry,
        )

        # ------------------------------------------------------------------
        # 3) Atualiza Plan.stripe_price_id no DB
        # ------------------------------------------------------------------
        if not dry:
            Plan.objects.filter(code="monthly").update(stripe_price_id=monthly_price.id)
            Plan.objects.filter(code="annual").update(stripe_price_id=annual_price.id)
            self.stdout.write(self.style.SUCCESS(
                f"  → Plan.monthly.stripe_price_id = {monthly_price.id}"
            ))
            self.stdout.write(self.style.SUCCESS(
                f"  → Plan.annual.stripe_price_id  = {annual_price.id}"
            ))

        # ------------------------------------------------------------------
        # 4) Arquiva produtos legados no Stripe
        # ------------------------------------------------------------------
        self._archive_legacy_products(stripe, keep_product_id=product.id if product else None, dry=dry)

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

    def _upsert_price(
        self, stripe, *,
        product_id: str, lookup_key: str, nickname: str,
        unit_amount: int, interval: str, dry: bool,
    ):
        existing = stripe.Price.list(lookup_keys=[lookup_key], active=True, limit=1).data
        if existing:
            price = existing[0]
            ok = (
                price.unit_amount == unit_amount
                and price.currency == "brl"
                and price.recurring and price.recurring.interval == interval
            )
            if ok:
                self.stdout.write(f"  preço[{lookup_key}]: reuso {price.id} ({price.unit_amount/100:.2f} BRL/{interval})")
                return price
            self.stdout.write(self.style.WARNING(
                f"  preço[{lookup_key}]: divergente — vou desativar e criar novo"
            ))
            if not dry:
                # Stripe não permite editar amount/interval; precisa criar novo
                stripe.Price.modify(price.id, active=False, lookup_key=None)

        if dry:
            self.stdout.write(self.style.WARNING(
                f"  [dry] criaria price {lookup_key}: {unit_amount/100:.2f} BRL/{interval}"
            ))
            return type("P", (), {"id": f"(dry-{lookup_key})"})()  # placeholder

        price = stripe.Price.create(
            product=product_id,
            unit_amount=unit_amount,
            currency="brl",
            recurring={"interval": interval},
            lookup_key=lookup_key,
            nickname=nickname,
        )
        self.stdout.write(self.style.SUCCESS(
            f"  preço criado: {price.id} [{lookup_key}] {unit_amount/100:.2f} BRL/{interval}"
        ))
        return price

    def _archive_legacy_products(self, stripe, *, keep_product_id: str | None, dry: bool):
        # Procura Prices com lookup_keys legados → desativa + arquiva produto vinculado
        legacy = stripe.Price.list(lookup_keys=LEGACY_LOOKUPS, active=True, limit=10).data
        if not legacy:
            self.stdout.write("  legados: nenhum Price ativo com lookup_keys antigos")
        for price in legacy:
            self.stdout.write(self.style.WARNING(
                f"  legado: desativando price {price.id} ({price.lookup_key})"
            ))
            if not dry:
                stripe.Price.modify(price.id, active=False, lookup_key=None)
            if price.product and price.product != keep_product_id:
                if not dry:
                    try:
                        stripe.Product.modify(price.product, active=False)
                        self.stdout.write(f"    → produto {price.product} arquivado")
                    except Exception as e:  # noqa: BLE001
                        self.stdout.write(self.style.WARNING(
                            f"    ! não foi possível arquivar {price.product}: {e}"
                        ))

        # Também procura por nome qualquer produto antigo que tenha sobrado
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
