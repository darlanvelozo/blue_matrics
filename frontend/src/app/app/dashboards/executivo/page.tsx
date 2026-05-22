"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Suspense, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { RevenueChart } from "@/components/dashboards/charts";
import { DrillDownModal } from "@/components/dashboards/drilldown-modal";
import { EmptyDashboardState } from "@/components/dashboards/empty-state";
import { FiltersPanel, type DashboardFilters } from "@/components/dashboards/filters-panel";
import { KpiCard } from "@/components/dashboards/kpi-card";
import { PeriodFilter } from "@/components/dashboards/period-filter";
import { ReportActions } from "@/components/dashboards/report-actions";
import { getExecutive } from "@/lib/dashboards";
import { usePeriod } from "@/lib/use-period";
import { formatCurrencyBRL } from "@/lib/utils";

export default function ExecutiveDashboardPage() {
  return (
    <Suspense fallback={<Skeleton className="h-96" />}>
      <Inner />
    </Suspense>
  );
}

function Inner() {
  const { preset, setPreset } = usePeriod();
  const [filters, setFilters] = useState<DashboardFilters>({});
  const [drillMonth, setDrillMonth] = useState<string | null>(null);

  const customRange = filters.start && filters.end ? { start: filters.start, end: filters.end } : {};
  const { data, isLoading } = useQuery({
    queryKey: ["dashboards", "executive", preset, filters],
    queryFn: () =>
      getExecutive({
        ...(customRange.start ? {} : { preset }),
        ...customRange,
        comparison: filters.comparison,
        salesperson: filters.salesperson,
        customer: filters.customer,
        product: filters.product,
      }),
  });

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard executivo</h1>
          <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
            Visão consolidada do desempenho da empresa.
            {data?.filters_applied && (
              <span className="ml-2 inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-600">
                filtros ativos
              </span>
            )}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PeriodFilter value={preset} onChange={setPreset} />
          <FiltersPanel filters={filters} onChange={setFilters} showCategory={false} />
          <ReportActions dashboard="executive" preset={preset} />
        </div>
      </header>

      {isLoading ? (
        <KpiSkeletons />
      ) : !data?.has_data ? (
        <EmptyDashboardState />
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              label="Faturamento"
              value={data.revenue.current}
              changePct={data.revenue.change_pct}
              sparkline={data.revenue_by_month.map((m) => ({ value: m.revenue }))}
            />
            <KpiCard
              label="Lucro líquido"
              value={data.net_profit.current}
              changePct={data.net_profit.change_pct}
            />
            <KpiCard
              label="Ticket médio"
              value={data.avg_ticket.current}
              changePct={data.avg_ticket.change_pct}
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
              <div className="flex items-center justify-between">
                <CardTitle>Faturamento ao longo do tempo</CardTitle>
                <p className="text-[11px] text-[color:var(--muted-foreground)]">
                  Clique numa barra para detalhes do mês
                </p>
              </div>
            </CardHeader>
            <CardContent>
              <RevenueChart
                data={data.revenue_by_month}
                onMonthClick={(ym) => setDrillMonth(ym)}
              />
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Top clientes</CardTitle>
                  <Link
                    href="/app/customers"
                    className="text-xs font-medium text-[color:var(--primary)] hover:underline"
                  >
                    Ver todos
                  </Link>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <ul className="divide-y divide-[color:var(--border)]">
                  {data.top_customers.map((c, i) => (
                    <li key={c.customer_id} className="flex items-center justify-between px-6 py-3 text-sm">
                      <span className="flex items-center gap-3">
                        <span className="text-xs font-mono text-[color:var(--muted-foreground)]">
                          #{i + 1}
                        </span>
                        <Link
                          href={`/app/sales?customer=${c.customer_id}`}
                          className="font-medium hover:underline"
                        >
                          {c.name}
                        </Link>
                      </span>
                      <span className="font-mono">{formatCurrencyBRL(c.total)}</span>
                    </li>
                  ))}
                  {data.top_customers.length === 0 && (
                    <li className="px-6 py-6 text-center text-sm text-[color:var(--muted-foreground)]">
                      Sem clientes neste período.
                    </li>
                  )}
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Top produtos</CardTitle>
                  <Link
                    href="/app/products"
                    className="text-xs font-medium text-[color:var(--primary)] hover:underline"
                  >
                    Ver todos
                  </Link>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <ul className="divide-y divide-[color:var(--border)]">
                  {data.top_products.map((p, i) => (
                    <li key={p.product_id} className="flex items-center justify-between px-6 py-3 text-sm">
                      <span className="flex items-center gap-3">
                        <span className="text-xs font-mono text-[color:var(--muted-foreground)]">
                          #{i + 1}
                        </span>
                        <span className="font-medium">{p.name}</span>
                      </span>
                      <span className="font-mono">{formatCurrencyBRL(p.total)}</span>
                    </li>
                  ))}
                  {data.top_products.length === 0 && (
                    <li className="px-6 py-6 text-center text-sm text-[color:var(--muted-foreground)]">
                      Sem produtos neste período.
                    </li>
                  )}
                </ul>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      <DrillDownModal
        month={drillMonth}
        filters={{
          salesperson: filters.salesperson,
          customer: filters.customer,
          product: filters.product,
        }}
        onClose={() => setDrillMonth(null)}
      />
    </div>
  );
}

function KpiSkeletons() {
  return (
    <>
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="space-y-2 p-5">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-8 w-32" />
              <Skeleton className="h-3 w-24" />
            </CardContent>
          </Card>
        ))}
      </section>
      <Card>
        <CardContent className="p-6">
          <Skeleton className="h-64" />
        </CardContent>
      </Card>
    </>
  );
}
