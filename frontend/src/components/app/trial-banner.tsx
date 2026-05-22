"use client";
import Link from "next/link";
import { Clock } from "lucide-react";
import type { User } from "@/lib/auth";

export function TrialBanner({ user }: { user: User }) {
  const tenant = user.tenant;
  if (!tenant || tenant.status !== "trial" || !tenant.trial_ends_at) return null;

  const end = new Date(tenant.trial_ends_at);
  const now = new Date();
  const days = Math.ceil((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

  if (days > 7) return null; // só mostra na última semana
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
