"use client";
import { useQuery } from "@tanstack/react-query";
import { Suspense } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CashflowChart, NetProfitChart } from "@/components/dashboards/charts";
import { EmptyDashboardState } from "@/components/dashboards/empty-state";
import { KpiCard } from "@/components/dashboards/kpi-card";
import { PeriodFilter } from "@/components/dashboards/period-filter";
import { getFinancial } from "@/lib/dashboards";
import { usePeriod } from "@/lib/use-period";

export default function FinancialDashboardPage() {
  return (
    <Suspense fallback={<Skeleton className="h-96" />}>
      <Inner />
    </Suspense>
  );
}

function Inner() {
  const { preset, setPreset } = usePeriod();
  const { data, isLoading } = useQuery({
    queryKey: ["dashboards", "financial", preset],
    queryFn: () => getFinancial({ preset }),
  });

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard financeiro</h1>
          <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
            Fluxo de caixa, recebimentos, pagamentos e inadimplência.
          </p>
        </div>
        <PeriodFilter value={preset} onChange={setPreset} />
      </header>

      {isLoading ? (
        <Skeleton className="h-32" />
      ) : !data?.has_data ? (
        <EmptyDashboardState />
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              label="Entradas"
              value={data.cash_in.current}
              changePct={data.cash_in.change_pct}
              sparkline={data.cashflow_by_month.map((m) => ({ value: m.in }))}
              sparkColor="#16a34a"
            />
            <KpiCard
              label="Saídas"
              value={data.cash_out.current}
              changePct={data.cash_out.change_pct}
              positiveIsGood={false}
              sparkline={data.cashflow_by_month.map((m) => ({ value: m.out }))}
              sparkColor="#dc2626"
            />
            <KpiCard
              label="Lucro líquido"
              value={data.net_profit.current}
              changePct={data.net_profit.change_pct}
              sparkline={data.cashflow_by_month.map((m) => ({ value: m.net }))}
            />
            <KpiCard
              label="Inadimplência"
              value={data.overdue_rate}
              format="percent"
              positiveIsGood={false}
            />
          </section>

          <Card>
            <CardHeader>
              <CardTitle>Fluxo de caixa</CardTitle>
            </CardHeader>
            <CardContent>
              <CashflowChart data={data.cashflow_by_month} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Lucro líquido por mês</CardTitle>
            </CardHeader>
            <CardContent>
              <NetProfitChart data={data.dre_monthly} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
