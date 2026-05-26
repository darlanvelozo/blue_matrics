"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ShoppingCart, TrendingUp, Users, Wand2 } from "lucide-react";
import { Suspense, useState } from "react";
import { CashflowChart, RevenueChart } from "@/components/dashboards/charts";
import { DrillDownModal } from "@/components/dashboards/drilldown-modal";
import { EmptyDashboardState } from "@/components/dashboards/empty-state";
import { FiltersPanel, type DashboardFilters } from "@/components/dashboards/filters-panel";
import { KpiCard } from "@/components/dashboards/kpi-card";
import { PeriodFilter } from "@/components/dashboards/period-filter";
import { RankingList } from "@/components/dashboards/ranking-list";
import { ReportActions } from "@/components/dashboards/report-actions";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getCommercial,
  type AbcCurve,
  type RevenueForecast,
} from "@/lib/dashboards";
import { usePeriod } from "@/lib/use-period";
import { cn, formatCurrencyBRL } from "@/lib/utils";

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

  const hasFormalSales = (data?.num_sales.current ?? 0) > 0;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-[color:var(--muted-foreground)]">
            Dashboard comercial
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">Vendas & previsões</h1>
          <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
            Faturamento, ticket médio, ranking de vendedores, previsão de vendas,
            LTV e taxa de recompra.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PeriodFilter value={preset} onChange={setPreset} />
          <FiltersPanel filters={filters} onChange={setFilters} />
          <ReportActions dashboard="commercial" preset={preset} />
        </div>
      </header>

      {isLoading || !data ? (
        <Skeleton className="h-96" />
      ) : !data.has_data ? (
        <EmptyDashboardState />
      ) : (
        <>
          {!hasFormalSales && (
            <div className="flex items-start gap-3 rounded-md border border-blue-500/30 bg-blue-500/10 px-4 py-3 text-sm text-blue-900 dark:text-blue-200">
              <ShoppingCart className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <p className="font-medium">Sem vendas formais no período</p>
                <p className="mt-0.5 text-xs">
                  Empresas que registram entradas direto pelo Financeiro (PIX/dinheiro)
                  podem ter este dashboard parcial. Os recebimentos identificados
                  abaixo vêm do módulo Financeiro.
                </p>
              </div>
            </div>
          )}

          {/* KPIs principais */}
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              label="Faturamento (vendas)"
              value={data.revenue.current}
              changePct={data.revenue.change_pct}
              sparkline={data.revenue_by_month.map((m) => ({ value: m.revenue }))}
            />
            <KpiCard
              label="Recebimentos totais"
              value={data.cash_in.current}
              changePct={data.cash_in.change_pct}
              sparkColor="#10b981"
            />
            <KpiCard
              label="Nº de vendas"
              value={data.num_sales.current}
              changePct={data.num_sales.change_pct}
              format="number"
            />
            <KpiCard
              label="Ticket médio"
              value={data.avg_ticket.current}
              changePct={data.avg_ticket.change_pct}
            />
          </section>

          {/* Linha 2: LTV + Recompra + Previsões */}
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              label="LTV médio"
              value={data.ltv.ltv_avg}
            />
            <KpiCard
              label="Taxa de recompra (90d)"
              value={data.repurchase_rate.rate_pct}
              format="percent"
            />
            <KpiCard
              label="Clientes únicos (12m)"
              value={data.ltv.unique_customers}
              format="number"
            />
            <KpiCard
              label="Clientes que voltaram"
              value={data.repurchase_rate.repurchased}
              format="number"
            />
          </section>

          {/* Previsão de receita */}
          <RevenueForecastCard
            forecast30={data.revenue_forecast_30d}
            forecast90={data.revenue_forecast_90d}
          />

          {/* Gráfico mensal */}
          <Card>
            <CardContent className="p-5">
              <h3 className="mb-3 text-sm font-semibold">Receita mensal</h3>
              <CashflowChart
                data={data.monthly_growth.map((m) => ({
                  month: m.month,
                  in: m.revenue,
                  out: m.expense,
                  net: m.profit,
                }))}
              />
            </CardContent>
          </Card>

          {/* Curva ABC (só se houver Sale) */}
          {data.abc_curve && data.abc_curve.rows.length > 0 && (
            <AbcCurveCard curve={data.abc_curve} />
          )}

          {/* Rankings */}
          <section className="grid gap-4 md:grid-cols-2">
            <RankingList
              title="Top clientes (recebimentos)"
              description="Quem mais paga no período"
              rows={data.top_receivable_customers.map((c) => ({
                id: c.customer_id,
                name: c.name,
                total: c.total,
                count: c.count,
                countLabel: "transações",
              }))}
            />
            {hasFormalSales ? (
              <Card>
                <CardContent className="p-5">
                  <h3 className="mb-3 text-sm font-semibold">Ranking de vendedores</h3>
                  <ul className="space-y-2">
                    {data.by_salesperson.slice(0, 10).map((s, i) => (
                      <li key={s.salesperson_id} className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2">
                          <span className="text-xs font-mono text-[color:var(--muted-foreground)]">
                            #{i + 1}
                          </span>
                          <span className="font-medium">{s.name}</span>
                        </span>
                        <span className="font-mono">
                          {formatCurrencyBRL(s.total)}
                          <span className="ml-1 text-[10px] text-[color:var(--muted-foreground)]">
                            ({s.sales} vendas)
                          </span>
                        </span>
                      </li>
                    ))}
                    {data.by_salesperson.length === 0 && (
                      <li className="py-3 text-center text-xs text-[color:var(--muted-foreground)]">
                        Sem vendedores com vendas no período.
                      </li>
                    )}
                  </ul>
                </CardContent>
              </Card>
            ) : (
              <RankingList
                title="Top categorias de receita"
                rows={data.commercial_kpis.top_revenue_categories.map((c) => ({
                  id: c.category_id,
                  name: c.name,
                  total: c.total,
                  count: c.count,
                  countLabel: "transações",
                }))}
              />
            )}
          </section>

          {hasFormalSales && (
            <Card>
              <CardContent className="p-5">
                <h3 className="mb-3 text-sm font-semibold">Top produtos</h3>
                <RevenueChart
                  data={data.revenue_by_month}
                  onMonthClick={(ym) => setDrillMonth(ym)}
                />
              </CardContent>
            </Card>
          )}

          {/* CTA IA */}
          <Link
            href="/app/ai"
            className="flex items-center justify-between rounded-lg border border-[color:var(--primary)]/30 bg-gradient-to-r from-[color:var(--primary)]/10 to-purple-500/10 p-4 transition hover:border-[color:var(--primary)]/50"
          >
            <div className="flex items-center gap-3">
              <Wand2 className="h-5 w-5 text-[color:var(--primary)]" />
              <div>
                <p className="text-sm font-semibold">
                  Pergunte: &quot;Quanto vou faturar nos próximos 30 dias?&quot;
                </p>
                <p className="text-xs text-[color:var(--muted-foreground)]">
                  O Analista IA detalha a previsão + recomendações.
                </p>
              </div>
            </div>
            <span className="text-sm font-medium text-[color:var(--primary)]">Conversar →</span>
          </Link>
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

function RevenueForecastCard({
  forecast30,
  forecast90,
}: {
  forecast30: RevenueForecast;
  forecast90: RevenueForecast;
}) {
  const confidenceMap: Record<string, { label: string; cls: string }> = {
    high: { label: "Alta", cls: "bg-emerald-500/10 text-emerald-700 border-emerald-500/30" },
    medium: { label: "Média", cls: "bg-amber-500/10 text-amber-700 border-amber-500/30" },
    low: { label: "Baixa", cls: "bg-red-500/10 text-red-700 border-red-500/30" },
  };
  const conf = confidenceMap[forecast30.confidence] ?? confidenceMap.medium;

  return (
    <Card>
      <CardContent className="p-5">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-[color:var(--primary)]" />
            <h3 className="text-sm font-semibold">Previsão de receita</h3>
          </div>
          <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-semibold", conf.cls)}>
            Confiança {conf.label.toLowerCase()}
          </span>
        </div>
        <div className="grid grid-cols-3 gap-3 text-center">
          <ForecastItem label="Próximos 30 dias" value={forecast30.forecast_total} />
          <ForecastItem label="Próximos 90 dias" value={forecast90.forecast_total} />
          <ForecastItem
            label="Tendência mensal"
            value={forecast30.trend_pct_monthly}
            format="percent"
          />
        </div>
        {forecast30.has_seasonality && (
          <p className="mt-3 text-[10px] text-[color:var(--muted-foreground)]">
            ⚠️ Variação mensal alta detectada — previsão pode ter desvios sazonais
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function ForecastItem({
  label,
  value,
  format = "currency",
}: {
  label: string;
  value: number;
  format?: "currency" | "percent";
}) {
  const formatted =
    format === "currency"
      ? formatCurrencyBRL(value)
      : `${value > 0 ? "+" : ""}${value.toFixed(1).replace(".", ",")}%`;
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-[color:var(--muted-foreground)]">
        {label}
      </p>
      <p className="mt-1 font-mono text-lg font-semibold tabular-nums">{formatted}</p>
    </div>
  );
}

function AbcCurveCard({ curve }: { curve: AbcCurve }) {
  const visible = curve.rows.slice(0, 20);
  return (
    <Card>
      <CardContent className="p-5">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold">Curva ABC de produtos</h3>
            <p className="text-xs text-[color:var(--muted-foreground)]">
              A (80% receita): {curve.counts.A} · B (15%): {curve.counts.B} · C (5%): {curve.counts.C}
            </p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[color:var(--border)] text-xs text-[color:var(--muted-foreground)]">
                <th className="px-3 py-2 text-left">#</th>
                <th className="px-3 py-2 text-left">Produto</th>
                <th className="px-3 py-2 text-center">Classe</th>
                <th className="px-3 py-2 text-right">Valor</th>
                <th className="px-3 py-2 text-right">% acum</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[color:var(--border)]">
              {visible.map((r, i) => (
                <tr key={r.product_id}>
                  <td className="px-3 py-2 text-xs text-[color:var(--muted-foreground)]">
                    {i + 1}
                  </td>
                  <td className="px-3 py-2 font-medium">{r.name}</td>
                  <td className="px-3 py-2 text-center">
                    <span
                      className={cn(
                        "inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold",
                        r.class === "A" && "bg-emerald-500/20 text-emerald-700",
                        r.class === "B" && "bg-amber-500/20 text-amber-700",
                        r.class === "C" && "bg-red-500/20 text-red-700",
                      )}
                    >
                      {r.class}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {formatCurrencyBRL(r.value)}
                  </td>
                  <td className="px-3 py-2 text-right text-xs font-mono">
                    {r.cumulative_pct.toFixed(1).replace(".", ",")}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
