"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Building2, Search, Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { listAdminTenants } from "@/lib/admin-saas";

export default function AdminTenantsPage() {
  const [q, setQ] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["admin-saas", "tenants", q],
    queryFn: () => listAdminTenants(q || undefined),
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <Building2 className="h-6 w-6" />
          Tenants ({data?.total ?? "…"})
        </h1>
        <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
          Todas as empresas cadastradas no BI AZUL.
        </p>
      </header>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[color:var(--muted-foreground)]" />
        <Input
          placeholder="Buscar por nome ou slug..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="pl-9"
        />
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : !data ? null : data.tenants.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-[color:var(--muted-foreground)]">
            Nenhum tenant encontrado.
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <ul className="divide-y divide-[color:var(--border)]">
              {data.tenants.map((t) => (
                <li key={t.id}>
                  <Link
                    href={`/admin-saas/tenants/${t.id}`}
                    className="flex items-center justify-between gap-4 px-6 py-4 transition-colors hover:bg-[color:var(--muted)]/40"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="flex items-center gap-2 font-medium">
                        {t.name}
                        <span className="rounded-full border border-[color:var(--border)] bg-[color:var(--muted)] px-2 py-0.5 font-mono text-[10px] text-[color:var(--muted-foreground)]">
                          {t.slug}
                        </span>
                      </p>
                      <p className="mt-1 text-xs text-[color:var(--muted-foreground)]">
                        Criado em {new Date(t.created_at).toLocaleDateString("pt-BR")}
                        {t.cnpj && ` · CNPJ ${t.cnpj}`}
                      </p>
                    </div>
                    <div className="flex items-center gap-4 text-xs">
                      <span className="inline-flex items-center gap-1 text-[color:var(--muted-foreground)]">
                        <Users className="h-3 w-3" />
                        {t.users_count}
                      </span>
                      <StatusBadge status={t.status} />
                      {t.subscription && <SubscriptionBadge sub={t.subscription} />}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    trial: "bg-blue-500/10 text-blue-600 border-blue-500/30",
    active: "bg-green-500/10 text-green-600 border-green-500/30",
    past_due: "bg-amber-500/10 text-amber-600 border-amber-500/30",
    canceled: "bg-zinc-500/10 text-zinc-500 border-zinc-500/30",
    suspended: "bg-red-500/10 text-red-600 border-red-500/30",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${
        map[status] ?? "bg-zinc-500/10 text-zinc-500 border-zinc-500/30"
      }`}
    >
      {status}
    </span>
  );
}

function SubscriptionBadge({ sub }: { sub: { plan: string | null; status: string | null } }) {
  if (!sub.plan) return null;
  return (
    <span className="rounded-full border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 text-[10px] font-medium text-violet-600">
      {sub.plan}
    </span>
  );
}
