"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  Minus,
  TrendingDown,
  TrendingUp,
  Wand2,
} from "lucide-react";
import { Suspense, useState } from "react";
import { CashflowChart } from "@/components/dashboards/charts";
import { DrillDownModal } from "@/components/dashboards/drilldown-modal";
import { EmptyDashboardState } from "@/components/dashboards/empty-state";
import { FiltersPanel, type DashboardFilters } from "@/components/dashboards/filters-panel";
import { KpiCard } from "@/components/dashboards/kpi-card";
import { PeriodFilter } from "@/components/dashboards/period-filter";
import { RankingList } from "@/components/dashboards/ranking-list";
import { ReportActions } from "@/components/dashboards/report-actions";
import { ScoreGauge } from "@/components/overview/score-gauge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getExecutive, type MonthlyGrowthPoint } from "@/lib/dashboards";
import { usePeriod } from "@/lib/use-period";
import { cn, formatCurrencyBRL } from "@/lib/utils";

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
          <p className="text-xs font-medium uppercase tracking-widest text-[color:var(--muted-foreground)]">
            Dashboard executivo
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">Visão de alta direção</h1>
          <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
            KPIs estratégicos, score de saúde, projeção de caixa e ponto de equilíbrio
            no período selecionado.
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

      {isLoading || !data ? (
        <SkeletonGrid />
      ) : !data.has_data ? (
        <EmptyDashboardState />
      ) : (
        <>
          {/* Top: KPIs principais + score */}
          <section className="grid gap-4 lg:grid-cols-[1fr_300px]">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <KpiCard
                label="Receita (período)"
                value={data.cash_in.current}
                changePct={data.cash_in.change_pct}
                sparkline={data.cashflow_by_month.map((m) => ({ value: m.in }))}
                sparkColor="#10b981"
              />
              <KpiCard
                label="Despesas (período)"
                value={data.cash_out.current}
                changePct={data.cash_out.change_pct}
                positiveIsGood={false}
                sparkline={data.cashflow_by_month.map((m) => ({ value: m.out }))}
                sparkColor="#ef4444"
              />
              <KpiCard
                label="Lucro líquido"
                value={data.net_profit.current}
                changePct={data.net_profit.change_pct}
                sparkline={data.cashflow_by_month.map((m) => ({ value: m.net }))}
              />
              <KpiCard
                label="Margem líquida"
                value={data.net_margin_pct_period}
                format="percent"
              />
              <KpiCard
                label="EBITDA"
                value={data.ebitda_period.current}
              />
              <KpiCard
                label="ROI operacional"
                value={data.roi_operational_pct}
                format="percent"
              />
            </div>
            <ScoreGauge score={data.health_score} />
          </section>

          {/* Linha 2: BEP + Forecast + Crescimento */}
          <section className="grid gap-4 md:grid-cols-3">
            <BreakevenMini data={data.breakeven} />
            <ForecastMini data={data.forecast_30d} />
            <GrowthMini growth={data.monthly_growth} />
          </section>

          {/* Linha 3: gráfico fluxo + tabela mensal */}
          <Card>
            <CardContent className="p-5">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold">Evolução financeira</h2>
                  <p className="text-xs text-[color:var(--muted-foreground)]">
                    Receita vs despesas mensal — clique numa barra para drill-down
                  </p>
                </div>
              </div>
              <CashflowChart data={data.cashflow_by_month} />
            </CardContent>
          </Card>

          {/* Tabela de crescimento mensal */}
          {data.monthly_growth.length > 0 && (
            <Card>
              <CardContent className="p-0 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[color:var(--border)] text-xs text-[color:var(--muted-foreground)]">
                      <th className="px-4 py-3 text-left font-medium">Mês</th>
                      <th className="px-4 py-3 text-right font-medium">Receita</th>
                      <th className="px-4 py-3 text-right font-medium">Despesa</th>
                      <th className="px-4 py-3 text-right font-medium">Lucro</th>
                      <th className="px-4 py-3 text-right font-medium">Margem</th>
                      <th className="px-4 py-3 text-right font-medium">Δ MoM</th>
                      <th className="px-4 py-3 text-right font-medium">Acumulado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[color:var(--border)]">
                    {data.monthly_growth.map((m) => (
                      <tr
                        key={m.month}
                        onClick={() => setDrillMonth(m.month)}
                        className="cursor-pointer hover:bg-[color:var(--muted)]/40"
                      >
                        <td className="px-4 py-2 font-medium">{m.month}</td>
                        <td className="px-4 py-2 text-right font-mono tabular-nums text-emerald-600">
                          {formatCurrencyBRL(m.revenue)}
                        </td>
                        <td className="px-4 py-2 text-right font-mono tabular-nums text-red-600">
                          {formatCurrencyBRL(m.expense)}
                        </td>
                        <td
                          className={cn(
                            "px-4 py-2 text-right font-mono font-semibold tabular-nums",
                            m.profit >= 0 ? "text-emerald-600" : "text-red-600",
                          )}
                        >
                          {formatCurrencyBRL(m.profit)}
                        </td>
                        <td className="px-4 py-2 text-right font-mono tabular-nums">
                          {m.margin_pct.toFixed(1).replace(".", ",")}%
                        </td>
                        <td className="px-4 py-2 text-right">
                          <Delta pct={m.revenue_growth_mom_pct} />
                        </td>
                        <td className="px-4 py-2 text-right font-mono text-xs text-[color:var(--muted-foreground)]">
                          {formatCurrencyBRL(m.cumulative_revenue)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}

          {/* Linha 4: rankings */}
          <section className="grid gap-4 md:grid-cols-2">
            <RankingList
              title="Onde entra dinheiro"
              description="Categorias de receita no período"
              rows={data.top_receivable_categories.map((c) => ({
                id: c.category_id,
                name: c.name,
                total: c.total,
                count: c.count,
                countLabel: "transações",
              }))}
            />
            <RankingList
              title="Onde sai dinheiro"
              description="Categorias de despesa no período"
              rows={data.top_payable_categories.map((c) => ({
                id: c.category_id,
                name: c.name,
                total: c.total,
                count: c.count,
                countLabel: "transações",
              }))}
            />
          </section>

          {/* Linha 5 — Sale-based (só renderiza se há venda formal) */}
          {data.num_sales.current > 0 && (
            <section className="grid gap-4 md:grid-cols-2">
              <RankingList
                title="Top clientes (vendas formais)"
                rows={data.top_customers.map((c) => ({
                  id: c.customer_id,
                  name: c.name,
                  total: c.total,
                  count: c.sales,
                  countLabel: "vendas",
                }))}
              />
              <RankingList
                title="Top produtos"
                rows={data.top_products.map((p) => ({
                  id: p.product_id,
                  name: p.name,
                  total: p.total,
                  count: p.quantity,
                  countLabel: "und",
                }))}
              />
            </section>
          )}

          {/* CTA IA */}
          <Link
            href="/app/ai"
            className="flex items-center justify-between rounded-lg border border-[color:var(--primary)]/30 bg-gradient-to-r from-[color:var(--primary)]/10 to-purple-500/10 p-4 transition hover:border-[color:var(--primary)]/50"
          >
            <div className="flex items-center gap-3">
              <Wand2 className="h-5 w-5 text-[color:var(--primary)]" />
              <div>
                <p className="text-sm font-semibold">Quer entender melhor esses números?</p>
                <p className="text-xs text-[color:var(--muted-foreground)]">
                  Pergunte ao Analista IA — ele explica em linguagem simples.
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

function Delta({ pct }: { pct: number | null }) {
  if (pct === null || !Number.isFinite(pct)) {
    return <span className="text-[color:var(--muted-foreground)]">—</span>;
  }
  const Icon = pct > 0 ? ArrowUp : pct < 0 ? ArrowDown : Minus;
  const color =
    pct > 0 ? "text-emerald-600" : pct < 0 ? "text-red-600" : "text-[color:var(--muted-foreground)]";
  return (
    <span className={cn("inline-flex items-center gap-0.5 font-mono text-xs tabular-nums", color)}>
      <Icon className="h-3 w-3" />
      {Math.abs(pct).toFixed(1).replace(".", ",")}%
    </span>
  );
}

function BreakevenMini({ data }: { data: { breakeven: number; revenue: number; above: boolean; diff: number; pct: number } }) {
  const pct = Math.min(100, Math.max(0, data.pct));
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[color:var(--muted-foreground)]">
            Ponto de equilíbrio
          </h3>
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-semibold",
              data.above
                ? "bg-emerald-500/10 text-emerald-700"
                : "bg-amber-500/10 text-amber-700",
            )}
          >
            {data.above ? "ACIMA" : "ABAIXO"}
          </span>
        </div>
        <p className="mt-2 font-mono text-lg font-semibold tabular-nums">
          {formatCurrencyBRL(data.breakeven)}
        </p>
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[color:var(--muted)]">
          <div
            className={data.above ? "h-full bg-emerald-500" : "h-full bg-amber-500"}
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="mt-2 text-[10px] text-[color:var(--muted-foreground)]">
          {data.above ? "Sobra" : "Faltam"}: {formatCurrencyBRL(Math.abs(data.diff))}
        </p>
      </CardContent>
    </Card>
  );
}

function ForecastMini({ data }: { data: { current_balance: number; expected_in: number; expected_out: number; projected_balance: number; at_risk: boolean } }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[color:var(--muted-foreground)]">
            Projeção 30 dias
          </h3>
          {data.at_risk && (
            <span className="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] font-semibold text-red-700">
              <AlertCircle className="h-3 w-3" /> RISCO
            </span>
          )}
        </div>
        <p
          className={cn(
            "mt-2 font-mono text-lg font-semibold tabular-nums",
            data.projected_balance < 0 ? "text-red-600" : "text-emerald-600",
          )}
        >
          {formatCurrencyBRL(data.projected_balance)}
        </p>
        <div className="mt-2 flex justify-between text-[10px] text-[color:var(--muted-foreground)]">
          <span className="text-emerald-600">+{formatCurrencyBRL(data.expected_in)}</span>
          <span className="text-red-600">−{formatCurrencyBRL(data.expected_out)}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function GrowthMini({ growth }: { growth: MonthlyGrowthPoint[] }) {
  if (growth.length < 2) {
    return (
      <Card>
        <CardContent className="p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[color:var(--muted-foreground)]">
            Crescimento mensal
          </h3>
          <p className="mt-2 text-sm text-[color:var(--muted-foreground)]">
            Dados insuficientes para tendência.
          </p>
        </CardContent>
      </Card>
    );
  }
  const last = growth[growth.length - 1];
  const trend = last.revenue_growth_mom_pct;
  const isUp = (trend ?? 0) > 0;
  const Icon = isUp ? TrendingUp : TrendingDown;
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[color:var(--muted-foreground)]">
            Crescimento (último mês)
          </h3>
          <Icon
            className={cn("h-4 w-4", isUp ? "text-emerald-600" : "text-red-600")}
          />
        </div>
        <p
          className={cn(
            "mt-2 font-mono text-lg font-semibold tabular-nums",
            isUp ? "text-emerald-600" : "text-red-600",
          )}
        >
          {trend !== null
            ? `${trend > 0 ? "+" : ""}${trend.toFixed(1).replace(".", ",")}%`
            : "—"}
        </p>
        <p className="mt-2 text-[10px] text-[color:var(--muted-foreground)]">
          {last.month} vs anterior · margem {last.margin_pct.toFixed(1).replace(".", ",")}%
        </p>
      </CardContent>
    </Card>
  );
}

function SkeletonGrid() {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
      <Skeleton className="h-48" />
    </div>
  );
}
