"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { use } from "react";
import { ArrowLeft, Building2, Users } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { getAdminTenantDetail } from "@/lib/admin-saas";
import { formatCurrencyBRL } from "@/lib/utils";

export default function TenantDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const numId = Number(id);

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-saas", "tenants", numId],
    queryFn: () => getAdminTenantDetail(numId),
  });

  if (isLoading) return <Skeleton className="h-96" />;
  if (error instanceof ApiError) {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-700 dark:text-red-300">
        {error.message}
      </div>
    );
  }
  if (!data) return null;

  return (
    <div className="space-y-6">
      <Link
        href="/admin-saas/tenants"
        className="inline-flex items-center gap-1 text-sm text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)]"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Voltar
      </Link>

      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <Building2 className="h-6 w-6" />
          {data.tenant.name}
        </h1>
        <p className="mt-1 font-mono text-xs text-[color:var(--muted-foreground)]">
          {data.tenant.slug} · {data.tenant.public_id}
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tenant</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 gap-y-2 text-sm sm:grid-cols-[140px_1fr]">
              <dt className="text-[color:var(--muted-foreground)]">CNPJ</dt>
              <dd>{data.tenant.cnpj || "—"}</dd>
              <dt className="text-[color:var(--muted-foreground)]">Status</dt>
              <dd>{data.tenant.status}</dd>
              <dt className="text-[color:var(--muted-foreground)]">Criado em</dt>
              <dd>{new Date(data.tenant.created_at).toLocaleDateString("pt-BR")}</dd>
              <dt className="text-[color:var(--muted-foreground)]">Trial até</dt>
              <dd>
                {data.tenant.trial_ends_at
                  ? new Date(data.tenant.trial_ends_at).toLocaleDateString("pt-BR")
                  : "—"}
              </dd>
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Assinatura</CardTitle>
          </CardHeader>
          <CardContent>
            {data.subscription ? (
              <dl className="grid grid-cols-1 gap-y-2 text-sm sm:grid-cols-[140px_1fr]">
                <dt className="text-[color:var(--muted-foreground)]">Plano</dt>
                <dd className="font-semibold">{data.subscription.plan}</dd>
                <dt className="text-[color:var(--muted-foreground)]">Status</dt>
                <dd>{data.subscription.status}</dd>
                <dt className="text-[color:var(--muted-foreground)]">Próximo ciclo</dt>
                <dd>
                  {data.subscription.current_period_end
                    ? new Date(data.subscription.current_period_end).toLocaleDateString("pt-BR")
                    : "—"}
                </dd>
                <dt className="text-[color:var(--muted-foreground)]">Cancelamento</dt>
                <dd>{data.subscription.cancel_at_period_end ? "Agendado" : "Não"}</dd>
                <dt className="text-[color:var(--muted-foreground)]">Faturas</dt>
                <dd>
                  {data.invoices_count} · {formatCurrencyBRL(data.invoices_total)} totais pagos
                </dd>
              </dl>
            ) : (
              <p className="text-sm text-[color:var(--muted-foreground)]">Sem assinatura.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Users className="h-4 w-4" />
            Usuários ({data.users.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {data.users.length === 0 ? (
            <p className="px-6 pb-6 text-sm text-[color:var(--muted-foreground)]">
              Sem usuários ativos.
            </p>
          ) : (
            <ul className="divide-y divide-[color:var(--border)]">
              {data.users.map((u) => (
                <li key={u.id} className="flex items-center justify-between px-6 py-3 text-sm">
                  <div>
                    <p className="font-medium">{u.full_name || u.email}</p>
                    <p className="text-xs text-[color:var(--muted-foreground)]">{u.email}</p>
                  </div>
                  <div className="flex items-center gap-4 text-xs">
                    <span className="rounded-full border border-[color:var(--border)] bg-[color:var(--muted)] px-2 py-0.5">
                      {u.role}
                    </span>
                    <span className="text-[color:var(--muted-foreground)]">
                      {u.last_login
                        ? `último: ${new Date(u.last_login).toLocaleDateString("pt-BR")}`
                        : "nunca logou"}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
