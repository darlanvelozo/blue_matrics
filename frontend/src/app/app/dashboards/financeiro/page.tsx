"use client";
import { useQuery } from "@tanstack/react-query";
import { Suspense, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CashflowChart, NetProfitChart } from "@/components/dashboards/charts";
import { EmptyDashboardState } from "@/components/dashboards/empty-state";
import { FiltersPanel, type DashboardFilters } from "@/components/dashboards/filters-panel";
import { KpiCard } from "@/components/dashboards/kpi-card";
import { PeriodFilter } from "@/components/dashboards/period-filter";
import { RankingList } from "@/components/dashboards/ranking-list";
import { ReportActions } from "@/components/dashboards/report-actions";
import { getFinancial } from "@/lib/dashboards";
import { usePeriod } from "@/lib/use-period";
import { formatCurrencyBRL } from "@/lib/utils";

export default function FinancialDashboardPage() {
  return (
    <Suspense fallback={<Skeleton className="h-96" />}>
      <Inner />
    </Suspense>
  );
}

function Inner() {
  const { preset, setPreset } = usePeriod();
  const [filters, setFilters] = useState<DashboardFilters>({});
  const customRange = filters.start && filters.end ? { start: filters.start, end: filters.end } : {};

  const { data, isLoading } = useQuery({
    queryKey: ["dashboards", "financial", preset, filters],
    queryFn: () =>
      getFinancial({
        ...(customRange.start ? {} : { preset }),
        ...customRange,
        comparison: filters.comparison,
        category: filters.category,
        customer: filters.customer,
      }),
  });

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard financeiro</h1>
          <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
            Fluxo de caixa, recebimentos, pagamentos e inadimplência.
            {data?.filters_applied && (
              <span className="ml-2 inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-600">
                filtros ativos
              </span>
            )}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PeriodFilter value={preset} onChange={setPreset} />
          <FiltersPanel
            filters={filters}
            onChange={setFilters}
            showSalesperson={false}
            showProduct={false}
            showCustomer={true}
            showCategory={true}
          />
          <ReportActions dashboard="financial" preset={preset} />
        </div>
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

          <section className="grid gap-4 md:grid-cols-2">
            <RankingList
              title="Top categorias — receitas"
              description="Categorias com maior volume recebido no período"
              rows={data.top_receivable_categories.map((c) => ({
                id: c.category_id,
                name: c.name,
                total: c.total,
                count: c.count,
                countLabel: "lançamentos",
              }))}
            />
            <RankingList
              title="Top categorias — despesas"
              description="Categorias com maior volume pago no período"
              rows={data.top_payable_categories.map((c) => ({
                id: c.category_id,
                name: c.name,
                total: c.total,
                count: c.count,
                countLabel: "lançamentos",
              }))}
            />
          </section>

          <section className="grid gap-4 md:grid-cols-2">
            <RankingList
              title="Top clientes — recebimentos"
              description="Quem mais pagou para você no período"
              rows={data.top_receivable_customers.map((c) => ({
                id: c.customer_id,
                name: c.name,
                total: c.total,
                count: c.count,
                countLabel: "transações",
              }))}
            />
            <RankingList
              title="Top fornecedores — pagamentos"
              description="Para quem você mais pagou no período"
              rows={data.top_payable_suppliers.map((c) => ({
                id: c.customer_id,
                name: c.name,
                total: c.total,
                count: c.count,
                countLabel: "transações",
              }))}
            />
          </section>

          <section className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>A receber — próximos dias</CardTitle>
                <p className="text-xs text-[color:var(--muted-foreground)]">
                  Lançamentos em aberto, com vencimento futuro
                </p>
              </CardHeader>
              <CardContent>
                <ForecastTable
                  rows={[
                    { label: "30 dias", ...data.upcoming_receivables_30d },
                    { label: "60 dias", ...data.upcoming_receivables_60d },
                    { label: "90 dias", ...data.upcoming_receivables_90d },
                  ]}
                  highlight={data.overdue_receivables}
                  highlightLabel="Vencidos hoje"
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>A pagar — próximos dias</CardTitle>
                <p className="text-xs text-[color:var(--muted-foreground)]">
                  Compromissos futuros (pendentes/atrasados)
                </p>
              </CardHeader>
              <CardContent>
                <ForecastTable
                  rows={[
                    { label: "30 dias", ...data.upcoming_payables_30d },
                    { label: "60 dias", ...data.upcoming_payables_60d },
                    { label: "90 dias", ...data.upcoming_payables_90d },
                  ]}
                  highlight={data.overdue_payables}
                  highlightLabel="Vencidos hoje"
                />
              </CardContent>
            </Card>
          </section>
        </>
      )}
    </div>
  );
}

function ForecastTable({
  rows,
  highlight,
  highlightLabel,
}: {
  rows: Array<{ label: string; total: number; count: number }>;
  highlight: { total: number; count: number };
  highlightLabel: string;
}) {
  return (
    <div className="space-y-3">
      {highlight.count > 0 && (
        <div className="flex items-center justify-between rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm">
          <span className="font-medium text-red-600">{highlightLabel}</span>
          <span className="font-mono text-xs tabular-nums">
            {formatCurrencyBRL(highlight.total)}
            <span className="ml-1 text-[10px] text-[color:var(--muted-foreground)]">
              ({highlight.count})
            </span>
          </span>
        </div>
      )}
      <ul className="space-y-2">
        {rows.map((r) => (
          <li
            key={r.label}
            className="flex items-center justify-between text-sm"
          >
            <span className="text-[color:var(--muted-foreground)]">{r.label}</span>
            <span className="font-mono text-xs tabular-nums">
              {formatCurrencyBRL(r.total)}
              <span className="ml-1 text-[10px] text-[color:var(--muted-foreground)]">
                ({r.count})
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
