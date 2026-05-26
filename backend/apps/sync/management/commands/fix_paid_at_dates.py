"""
Re-deriva `paid_at` de todas as `FinancialEntry` PAGAS a partir dos RawPayloads,
aplicando a heurística corrigida (data_competencia > data_vencimento > NULL).

Necessário após o fix do mapper em 2026-05-26: a versão anterior usava
`data_alteracao` como proxy de `paid_at`, o que concentrava todos os
"pagamentos" na data da sincronização e inflava artificialmente os KPIs
de "faturamento do mês".

Idempotente: pode rodar quantas vezes quiser.

Uso:
    python manage.py fix_paid_at_dates                   # roda em todos tenants
    python manage.py fix_paid_at_dates --tenant slug     # só um tenant
    python manage.py fix_paid_at_dates --dry-run         # só mostra
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.sync.models import FinancialEntry, RawPayload
from apps.tenants.models import Tenant


# Resources usados pelos endpoints financeiros do Conta Azul v2
FINANCIAL_RESOURCES = ("financial_receivables", "financial_payables")


def _to_date(v: Any) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        # ISO 8601 com ou sem hora
        s = v.strip()
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s.split("+")[0].split("Z")[0], fmt).date()
            except ValueError:
                continue
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            return None
    return None


def _derive_paid_at(payload: dict) -> date | None:
    """Aplica a mesma lógica do mapper.contas_a_pagar/receber mapper corrigido."""
    explicit = _to_date(
        payload.get("dataPagamento")
        or payload.get("data_pagamento")
        or payload.get("paidAt")
        or payload.get("pagamento")
    )
    if explicit:
        return explicit
    return _to_date(
        payload.get("data_competencia")
        or payload.get("dataCompetencia")
        or payload.get("data_vencimento")
        or payload.get("dataVencimento")
        or payload.get("dueDate")
        or payload.get("vencimento")
    )


class Command(BaseCommand):
    help = "Re-deriva paid_at de FinancialEntry pagas a partir do RawPayload."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", help="Slug do tenant específico (default: todos)")
        parser.add_argument(
            "--dry-run", action="store_true", help="Mostra mudanças sem aplicar."
        )
        parser.add_argument(
            "--batch", type=int, default=500, help="Tamanho do batch para update."
        )

    def handle(self, *args, **opts):
        dry = bool(opts.get("dry_run"))
        tenant_slug = opts.get("tenant")
        batch = opts["batch"]

        tenants = Tenant.objects.all()
        if tenant_slug:
            tenants = tenants.filter(slug=tenant_slug)

        for tenant in tenants:
            self.stdout.write(self.style.NOTICE(
                f"\n=== Tenant: {tenant.slug} (id={tenant.id}) ==="
            ))
            self._process_tenant(tenant, dry=dry, batch=batch)

    def _process_tenant(self, tenant: Tenant, *, dry: bool, batch: int) -> None:
        # Indexa RawPayloads do tenant por (resource, external_id)
        rp_map: dict[tuple[str, str], dict] = {}
        for rp in RawPayload.unsafe_objects.filter(
            tenant=tenant, resource__in=FINANCIAL_RESOURCES,
        ).iterator(chunk_size=1000):
            payload = rp.payload if isinstance(rp.payload, dict) else json.loads(rp.payload)
            ext_id = payload.get("id") or payload.get("uuid") or rp.external_id
            if ext_id:
                rp_map[(rp.resource, str(ext_id))] = payload

        if not rp_map:
            self.stdout.write("  Sem RawPayloads financeiros pra esse tenant.")
            return

        self.stdout.write(f"  RawPayloads indexados: {len(rp_map)}")

        # Itera nas FinancialEntries pagas e calcula novo paid_at
        qs = FinancialEntry.unsafe_objects.filter(
            tenant=tenant, status=FinancialEntry.Status.PAID,
        )
        total = qs.count()
        self.stdout.write(f"  FinancialEntries paid: {total}")

        to_update: list[FinancialEntry] = []
        unchanged = 0
        missing_payload = 0

        for fe in qs.iterator(chunk_size=1000):
            # Tenta achar o RawPayload em qualquer resource (não sabemos qual)
            payload = None
            for res in FINANCIAL_RESOURCES:
                payload = rp_map.get((res, str(fe.external_id)))
                if payload:
                    break
            if payload is None:
                missing_payload += 1
                # Sem raw: usa due_date se houver, senão deixa como está
                new_paid_at = fe.due_date
            else:
                new_paid_at = _derive_paid_at(payload)
                if new_paid_at is None:
                    # Sem nada usável → mantém due_date
                    new_paid_at = fe.due_date

            if new_paid_at != fe.paid_at:
                fe.paid_at = new_paid_at
                to_update.append(fe)
            else:
                unchanged += 1

        self.stdout.write(f"  → mudanças: {len(to_update)}  unchanged: {unchanged}  missing_payload: {missing_payload}")

        if dry:
            self.stdout.write(self.style.WARNING("  [dry-run] não atualizando."))
            # Mostra alguns exemplos
            for fe in to_update[:5]:
                # busca o valor antigo direto do banco
                old = FinancialEntry.unsafe_objects.get(pk=fe.pk).paid_at
                self.stdout.write(
                    f"    e.g. id={fe.id} due={fe.due_date}  novo_paid={fe.paid_at}  (antes era {old})"
                )
            return

        # Aplica em batches com bulk_update
        applied = 0
        with transaction.atomic():
            for i in range(0, len(to_update), batch):
                chunk = to_update[i:i + batch]
                FinancialEntry.unsafe_objects.bulk_update(chunk, ["paid_at"])
                applied += len(chunk)
        self.stdout.write(self.style.SUCCESS(f"  ✓ aplicado em {applied} registros"))
