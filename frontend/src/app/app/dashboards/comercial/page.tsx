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
import { getCommercial } from "@/lib/dashboards";
import { usePeriod } from "@/lib/use-period";
import { formatCurrencyBRL } from "@/lib/utils";

export default function CommercialDashboardPage() {
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
    queryKey: ["dashboards", "commercial", preset, filters],
    queryFn: () =>
      getCommercial({
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
          <h1 className="text-2xl font-bold tracking-tight">Dashboard comercial</h1>
          <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
            Vendas, ticket médio, ranking de clientes, produtos e vendedores.
            {data?.filters_applied && (
              <span className="ml-2 inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-600">
                filtros ativos
              </span>
            )}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PeriodFilter value={preset} onChange={setPreset} />
          <FiltersPanel filters={filters} onChange={setFilters} />
        </div>
      </header>

      {isLoading ? (
        <Skeleton className="h-32" />
      ) : !data?.has_data ? (
        <EmptyDashboardState />
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-3">
            <KpiCard
              label="Faturamento"
              value={data.revenue.current}
              changePct={data.revenue.change_pct}
              sparkline={data.revenue_by_month.map((m) => ({ value: m.revenue }))}
            />
            <KpiCard
              label="Nº de vendas"
              value={data.num_sales.current}
              changePct={data.num_sales.change_pct}
              format="number"
              sparkline={data.revenue_by_month.map((m) => ({ value: m.sales_count }))}
            />
            <KpiCard
              label="Ticket médio"
              value={data.avg_ticket.current}
              changePct={data.avg_ticket.change_pct}
            />
          </section>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Faturamento ao longo do tempo</CardTitle>
                <p className="text-[11px] text-[color:var(--muted-foreground)]">
                  Clique numa barra para detalhes
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
                  <CardTitle>Ranking de clientes</CardTitle>
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
                      <span className="flex items-baseline gap-3">
                        <span className="text-xs text-[color:var(--muted-foreground)]">
                          {c.sales} {c.sales === 1 ? "venda" : "vendas"}
                        </span>
                        <span className="font-mono">{formatCurrencyBRL(c.total)}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Ranking de produtos</CardTitle>
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
                      <span className="flex items-baseline gap-3">
                        <span className="text-xs text-[color:var(--muted-foreground)]">
                          {p.quantity.toLocaleString("pt-BR")} und
                        </span>
                        <span className="font-mono">{formatCurrencyBRL(p.total)}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Vendas por vendedor</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <ul className="divide-y divide-[color:var(--border)]">
                {data.by_salesperson.map((s, i) => (
                  <li key={s.salesperson_id} className="flex items-center justify-between px-6 py-3 text-sm">
                    <span className="flex items-center gap-3">
                      <span className="text-xs font-mono text-[color:var(--muted-foreground)]">
                        #{i + 1}
                      </span>
                      <span className="font-medium">{s.name}</span>
                    </span>
                    <span className="flex items-baseline gap-3">
                      <span className="text-xs text-[color:var(--muted-foreground)]">
                        {s.sales} {s.sales === 1 ? "venda" : "vendas"}
                      </span>
                      <span className="font-mono">{formatCurrencyBRL(s.total)}</span>
                    </span>
                  </li>
                ))}
                {data.by_salesperson.length === 0 && (
                  <li className="px-6 py-6 text-center text-sm text-[color:var(--muted-foreground)]">
                    Nenhum vendedor com vendas neste período.
                  </li>
                )}
              </ul>
            </CardContent>
          </Card>
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
