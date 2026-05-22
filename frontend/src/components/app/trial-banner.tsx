"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Clock } from "lucide-react";
import { getSubscription } from "@/lib/billing";
import type { User } from "@/lib/auth";

/**
 * Mostra banner só quando a SUBSCRIPTION está em trial.
 * (Não usa tenant.status — esse campo é separado; se o usuário assina o plano,
 * subscription vira ACTIVE mas o tenant continua "trial" até alguém atualizar.)
 *
 * Aparece nos últimos 7 dias do trial + após expirar.
 */
export function TrialBanner({ user }: { user: User }) {
  const { data } = useQuery({
    queryKey: ["billing", "subscription"],
    queryFn: getSubscription,
    enabled: !!user.tenant,
  });

  const sub = data?.subscription;
  if (!sub) return null;

  // Só mostra se ainda em trial. Se virou active/canceled/past_due, sai daqui.
  if (sub.status !== "trialing" || !sub.trial_ends_at) return null;

  const end = new Date(sub.trial_ends_at);
  const now = new Date();
  const days = Math.ceil((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

  if (days > 7) return null;
  const expired = days <= 0;

  return (
    <div
      className={
        expired
          ? "border-b border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300"
          : "border-b border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-300"
      }
    >
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-6 py-2 text-xs">
        <span className="inline-flex items-center gap-2">
          <Clock className="h-3.5 w-3.5" />
          {expired ? (
            <>Seu trial expirou. Assine para continuar acessando os dashboards.</>
          ) : days === 1 ? (
            <>Seu trial termina <strong>amanhã</strong>.</>
          ) : (
            <>
              Seu trial termina em <strong>{days} dias</strong>.
            </>
          )}
        </span>
        <Link
          href="/app/billing"
          className="rounded-full bg-white/80 px-3 py-1 text-xs font-semibold text-[color:var(--foreground)] shadow-sm transition hover:bg-white dark:bg-black/40 dark:text-white"
        >
          Ver planos
        </Link>
      </div>
    </div>
  );
}
