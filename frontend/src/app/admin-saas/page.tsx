"use client";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Building2,
  CreditCard,
  Sparkles,
  TrendingUp,
  Users,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { getSaasSummary } from "@/lib/admin-saas";
import { formatCurrencyBRL } from "@/lib/utils";

export default function AdminSaasHome() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-saas", "summary"],
    queryFn: getSaasSummary,
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Visão geral SaaS</h1>
        <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
          Métricas operacionais do BI AZUL.
        </p>
      </header>

      {error instanceof ApiError && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          <AlertTriangle className="mr-1.5 inline h-4 w-4" />
          {error.message}
        </div>
      )}

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : !data ? null : (
        <>
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric
              icon={TrendingUp}
              label="MRR"
              value={formatCurrencyBRL(data.mrr)}
              hint={`ARR ${formatCurrencyBRL(data.arr)}`}
              accent="blue"
            />
            <Metric
              icon={CreditCard}
              label="Assinantes ativos"
              value={String(data.active_subscribers)}
              hint={`${data.trialing} em trial • ${data.expired_trials} expirados`}
              accent="green"
            />
            <Metric
              icon={Building2}
              label="Tenants totais"
              value={String(data.total_tenants)}
              hint={`MAU 30d: ${data.mau_30d}`}
              accent="purple"
            />
            <Metric
              icon={Activity}
              label="Receita 30d"
              value={formatCurrencyBRL(data.revenue_30d)}
              hint={`Conversão trial→pago: ${data.trial_to_paid_pct.toFixed(1)}%`}
              accent="amber"
            />
          </section>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-base">MRR por plano</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {data.mrr_by_plan.length === 0 ? (
                  <p className="px-6 pb-6 text-sm text-[color:var(--muted-foreground)]">
                    Ainda nenhuma assinatura ativa.
                  </p>
                ) : (
                  <ul className="divide-y divide-[color:var(--border)]">
                    {data.mrr_by_plan.map((p) => (
                      <li key={p.plan_code} className="flex items-center justify-between px-6 py-3 text-sm">
                        <div className="flex items-center gap-3">
                          <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
                            <Sparkles className="h-3.5 w-3.5" />
                          </span>
                          <span className="font-medium">{p.plan_name}</span>
                          <span className="text-xs text-[color:var(--muted-foreground)]">
                            {p.subscribers} assinante{p.subscribers > 1 ? "s" : ""}
                          </span>
                        </div>
                        <span className="font-mono font-semibold">{formatCurrencyBRL(p.mrr)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Churn (30d)</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-baseline gap-2">
                  <span
                    className={
                      data.churn_30d_pct < 5
                        ? "text-3xl font-bold text-green-600"
                        : data.churn_30d_pct < 10
                        ? "text-3xl font-bold text-amber-600"
                        : "text-3xl font-bold text-red-600"
                    }
                  >
                    {data.churn_30d_pct.toFixed(2)}%
                  </span>
                  {data.churn_30d_pct === 0 ? (
                    <ArrowDownRight className="h-4 w-4 text-green-600" />
                  ) : (
                    <ArrowUpRight className="h-4 w-4 text-red-600" />
                  )}
                </div>
                <p className="text-xs text-[color:var(--muted-foreground)]">
                  {data.churn_30d_pct < 5
                    ? "Excelente — taxa saudável."
                    : data.churn_30d_pct < 10
                    ? "Atenção — investigue motivos."
                    : "Crítico — risco de receita."}
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Signups últimos 30 dias</CardTitle>
            </CardHeader>
            <CardContent>
              <SignupsBars data={data.signups_30d} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  hint,
  accent,
}: {
  icon: typeof Activity;
  label: string;
  value: string;
  hint: string;
  accent: "blue" | "green" | "purple" | "amber";
}) {
  const accentCls = {
    blue: "bg-blue-500/10 text-blue-500",
    green: "bg-green-500/10 text-green-500",
    purple: "bg-violet-500/10 text-violet-500",
    amber: "bg-amber-500/10 text-amber-500",
  }[accent];
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center gap-3">
          <span className={`inline-flex h-10 w-10 items-center justify-center rounded-lg ${accentCls}`}>
            <Icon className="h-5 w-5" />
          </span>
          <p className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">
            {label}
          </p>
        </div>
        <p className="mt-3 text-2xl font-bold tracking-tight">{value}</p>
        <p className="mt-1 text-xs text-[color:var(--muted-foreground)]">{hint}</p>
      </CardContent>
    </Card>
  );
}

function SignupsBars({ data }: { data: Array<{ date: string; count: number }> }) {
  const max = Math.max(...data.map((d) => d.count), 1);
  const total = data.reduce((acc, d) => acc + d.count, 0);
  return (
    <div className="space-y-3">
      <p className="text-sm text-[color:var(--muted-foreground)]">
        Total no período: <strong className="text-[color:var(--foreground)]">{total}</strong>
      </p>
      <div className="flex items-end gap-0.5" style={{ height: 100 }}>
        {data.map((d) => {
          const h = (d.count / max) * 100;
          return (
            <div
              key={d.date}
              className="group relative flex-1"
              style={{ height: "100%" }}
              title={`${new Date(d.date).toLocaleDateString("pt-BR")}: ${d.count}`}
            >
              <div
                className="absolute bottom-0 left-0 right-0 rounded-t bg-gradient-to-t from-blue-500/40 to-blue-500 transition-opacity hover:opacity-80"
                style={{ height: d.count === 0 ? "2px" : `${h}%`, opacity: d.count === 0 ? 0.3 : 1 }}
              />
            </div>
          );
        })}
      </div>
      <div className="flex justify-between text-xs text-[color:var(--muted-foreground)]">
        <span>{new Date(data[0]?.date).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })}</span>
        <span>hoje</span>
      </div>
    </div>
  );
}
