"use client";
import { useQuery } from "@tanstack/react-query";
import {
  AlertOctagon,
  AlertTriangle,
  Info,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { Suspense, useState } from "react";
import { CashflowChart, NetProfitChart } from "@/components/dashboards/charts";
import { EmptyDashboardState } from "@/components/dashboards/empty-state";
import { FiltersPanel, type DashboardFilters } from "@/components/dashboards/filters-panel";
import { KpiCard } from "@/components/dashboards/kpi-card";
import { PeriodFilter } from "@/components/dashboards/period-filter";
import { RankingList } from "@/components/dashboards/ranking-list";
import { ReportActions } from "@/components/dashboards/report-actions";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getFinancial,
  type DreStructured,
  type FinancialAlert,
} from "@/lib/dashboards";
import { usePeriod } from "@/lib/use-period";
import { cn, formatCurrencyBRL } from "@/lib/utils";

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
          <p className="text-xs font-medium uppercase tracking-widest text-[color:var(--muted-foreground)]">
            Dashboard financeiro
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">DRE + Fluxo de caixa</h1>
          <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
            Demonstrativo, custos fixos vs variáveis, capital de giro, burn rate e
            alertas automáticos.
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

      {isLoading || !data ? (
        <Skeleton className="h-96" />
      ) : !data.has_data ? (
        <EmptyDashboardState />
      ) : (
        <>
          {/* Alertas (no topo - prioridade visual) */}
          {data.alerts.length > 0 && (
            <section className="space-y-2">
              {data.alerts.map((a, i) => (
                <AlertCard key={i} alert={a} />
              ))}
            </section>
          )}

          {/* KPIs primários */}
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              label="Entradas"
              value={data.cash_in.current}
              changePct={data.cash_in.change_pct}
              sparkline={data.cashflow_by_month.map((m) => ({ value: m.in }))}
              sparkColor="#10b981"
            />
            <KpiCard
              label="Saídas"
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
              label="Inadimplência"
              value={data.overdue_rate}
              format="percent"
              positiveIsGood={false}
            />
          </section>

          {/* Linha 2: KPIs financeiros avançados */}
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard label="EBITDA" value={data.ebitda_period.current} />
            <KpiCard
              label="Margem de contribuição"
              value={data.contribution_margin_pct}
              format="percent"
            />
            <KpiCard
              label="Capital de giro"
              value={data.working_capital.working_capital}
            />
            <KpiCard
              label="Burn rate / mês"
              value={data.burn_rate_monthly}
              positiveIsGood={false}
            />
          </section>

          {/* DRE estruturado */}
          <DreTable dre={data.dre} />

          {/* Custos fixos vs variáveis */}
          <Card>
            <CardContent className="p-5">
              <h3 className="mb-3 text-sm font-semibold">
                Composição das despesas — fixos vs variáveis
              </h3>
              <ExpenseBreakdown
                fixed={data.expense_breakdown.fixed}
                variable={data.expense_breakdown.variable}
                total={data.expense_breakdown.total}
              />
            </CardContent>
          </Card>

          {/* Fluxo de caixa mensal */}
          <Card>
            <CardContent className="p-5">
              <h3 className="mb-3 text-sm font-semibold">Fluxo de caixa</h3>
              <CashflowChart data={data.cashflow_by_month} />
            </CardContent>
          </Card>

          {/* Lucro líquido mensal */}
          <Card>
            <CardContent className="p-5">
              <h3 className="mb-3 text-sm font-semibold">Lucro líquido por mês</h3>
              <NetProfitChart data={data.dre_monthly} />
            </CardContent>
          </Card>

          {/* Rankings */}
          <section className="grid gap-4 md:grid-cols-2">
            <RankingList
              title="Categorias de receita"
              description="Onde entra dinheiro no período"
              rows={data.top_receivable_categories.map((c) => ({
                id: c.category_id,
                name: c.name,
                total: c.total,
                count: c.count,
                countLabel: "lançamentos",
              }))}
            />
            <RankingList
              title="Categorias de despesa"
              description="Onde sai dinheiro no período"
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
              title="Maiores clientes (recebido)"
              rows={data.top_receivable_customers.map((c) => ({
                id: c.customer_id,
                name: c.name,
                total: c.total,
                count: c.count,
                countLabel: "transações",
              }))}
            />
            <RankingList
              title="Maiores fornecedores (pago)"
              rows={data.top_payable_suppliers.map((c) => ({
                id: c.customer_id,
                name: c.name,
                total: c.total,
                count: c.count,
                countLabel: "transações",
              }))}
            />
          </section>

          {/* Forecast 30/60/90 */}
          <section className="grid gap-4 md:grid-cols-2">
            <ForecastTable
              title="A receber — próximos dias"
              receivable
              data={{
                d30: data.upcoming_receivables_30d,
                d60: data.upcoming_receivables_60d,
                d90: data.upcoming_receivables_90d,
                overdue: data.overdue_receivables,
              }}
            />
            <ForecastTable
              title="A pagar — próximos dias"
              receivable={false}
              data={{
                d30: data.upcoming_payables_30d,
                d60: data.upcoming_payables_60d,
                d90: data.upcoming_payables_90d,
                overdue: data.overdue_payables,
              }}
            />
          </section>
        </>
      )}
    </div>
  );
}

function AlertCard({ alert }: { alert: FinancialAlert }) {
  const config = {
    critical: { Icon: AlertOctagon, cls: "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300" },
    warning: { Icon: AlertTriangle, cls: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300" },
    info: { Icon: Info, cls: "border-blue-500/30 bg-blue-500/10 text-blue-700 dark:text-blue-300" },
  };
  const c = config[alert.severity];
  const Icon = c.Icon;
  return (
    <div className={cn("flex items-start gap-3 rounded-lg border px-4 py-3 text-sm", c.cls)}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">
        <p className="font-semibold">{alert.title}</p>
        <p className="text-xs opacity-90">{alert.message}</p>
      </div>
    </div>
  );
}

function DreTable({ dre }: { dre: DreStructured }) {
  return (
    <Card>
      <CardContent className="p-5">
        <h3 className="mb-3 text-sm font-semibold">DRE simplificado</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <tbody className="divide-y divide-[color:var(--border)]">
              {/* Receitas */}
              <tr className="bg-emerald-500/5">
                <td colSpan={3} className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-emerald-700">
                  Receitas
                </td>
              </tr>
              {dre.revenues.slice(0, 10).map((r) => (
                <tr key={`r-${r.category_id ?? r.category}`}>
                  <td className="px-6 py-2">{r.category}</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {formatCurrencyBRL(r.total)}
                  </td>
                  <td className="px-3 py-2 text-right text-xs text-[color:var(--muted-foreground)]">
                    {r.share_pct.toFixed(1).replace(".", ",")}%
                  </td>
                </tr>
              ))}
              <tr className="bg-emerald-500/10 font-semibold">
                <td className="px-3 py-2">(=) Receita total</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums text-emerald-700">
                  {formatCurrencyBRL(dre.totals.revenue)}
                </td>
                <td></td>
              </tr>

              {/* Custos variáveis */}
              <tr className="bg-amber-500/5">
                <td colSpan={3} className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-amber-700">
                  (−) Custos / despesas variáveis
                </td>
              </tr>
              {dre.expenses_variable.slice(0, 10).map((e) => (
                <tr key={`v-${e.category_id ?? e.category}`}>
                  <td className="px-6 py-2 text-[color:var(--muted-foreground)]">{e.category}</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {formatCurrencyBRL(e.total)}
                  </td>
                  <td className="px-3 py-2 text-right text-xs text-[color:var(--muted-foreground)]">
                    {e.share_pct.toFixed(1).replace(".", ",")}%
                  </td>
                </tr>
              ))}
              <tr className="bg-amber-500/10 font-semibold">
                <td className="px-3 py-2">(−) Variáveis total</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums text-amber-700">
                  {formatCurrencyBRL(dre.totals.expense_variable)}
                </td>
                <td></td>
              </tr>

              {/* Margem de contribuição */}
              <tr className="bg-blue-500/5 font-semibold">
                <td className="px-3 py-2">(=) Margem de contribuição</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums text-blue-700">
                  {formatCurrencyBRL(dre.totals.contribution_margin)}
                </td>
                <td className="px-3 py-2 text-right text-xs text-[color:var(--muted-foreground)]">
                  {(dre.totals.revenue > 0 ? (dre.totals.contribution_margin / dre.totals.revenue) * 100 : 0).toFixed(1).replace(".", ",")}%
                </td>
              </tr>

              {/* Custos fixos */}
              <tr className="bg-red-500/5">
                <td colSpan={3} className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-red-700">
                  (−) Custos fixos
                </td>
              </tr>
              {dre.expenses_fixed.slice(0, 10).map((e) => (
                <tr key={`f-${e.category_id ?? e.category}`}>
                  <td className="px-6 py-2 text-[color:var(--muted-foreground)]">{e.category}</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {formatCurrencyBRL(e.total)}
                  </td>
                  <td className="px-3 py-2 text-right text-xs text-[color:var(--muted-foreground)]">
                    {e.share_pct.toFixed(1).replace(".", ",")}%
                  </td>
                </tr>
              ))}
              <tr className="bg-red-500/10 font-semibold">
                <td className="px-3 py-2">(−) Fixos total</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums text-red-700">
                  {formatCurrencyBRL(dre.totals.expense_fixed)}
                </td>
                <td></td>
              </tr>

              {/* Resultado final */}
              <tr className="bg-[color:var(--muted)]/60 text-base font-bold">
                <td className="px-3 py-3">(=) Lucro líquido</td>
                <td
                  className={cn(
                    "px-3 py-3 text-right font-mono tabular-nums",
                    dre.totals.net_profit >= 0 ? "text-emerald-700" : "text-red-700",
                  )}
                >
                  {formatCurrencyBRL(dre.totals.net_profit)}
                </td>
                <td className="px-3 py-3 text-right text-xs">
                  {dre.totals.net_margin_pct.toFixed(1).replace(".", ",")}%
                </td>
              </tr>
              <tr className="text-xs">
                <td className="px-3 py-2 text-[color:var(--muted-foreground)]">EBITDA (período)</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">
                  {formatCurrencyBRL(dre.totals.ebitda)}
                </td>
                <td></td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function ExpenseBreakdown({ fixed, variable, total }: { fixed: number; variable: number; total: number }) {
  const fixedPct = total > 0 ? (fixed / total) * 100 : 0;
  const varPct = total > 0 ? (variable / total) * 100 : 0;
  return (
    <div className="space-y-3">
      <div className="flex h-3 overflow-hidden rounded-full bg-[color:var(--muted)]">
        <div className="h-full bg-red-500" style={{ width: `${fixedPct}%` }} title="Fixos" />
        <div className="h-full bg-amber-500" style={{ width: `${varPct}%` }} title="Variáveis" />
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-md border border-[color:var(--border)] bg-red-500/5 p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-red-700">
            Custos fixos
          </p>
          <p className="mt-1 font-mono text-lg font-semibold tabular-nums">
            {formatCurrencyBRL(fixed)}
          </p>
          <p className="text-[10px] text-[color:var(--muted-foreground)]">
            {fixedPct.toFixed(1).replace(".", ",")}% do total
          </p>
        </div>
        <div className="rounded-md border border-[color:var(--border)] bg-amber-500/5 p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-amber-700">
            Custos variáveis
          </p>
          <p className="mt-1 font-mono text-lg font-semibold tabular-nums">
            {formatCurrencyBRL(variable)}
          </p>
          <p className="text-[10px] text-[color:var(--muted-foreground)]">
            {varPct.toFixed(1).replace(".", ",")}% do total
          </p>
        </div>
      </div>
    </div>
  );
}

function ForecastTable({
  title,
  receivable,
  data,
}: {
  title: string;
  receivable: boolean;
  data: {
    d30: { total: number; count: number; days: number };
    d60: { total: number; count: number; days: number };
    d90: { total: number; count: number; days: number };
    overdue: { total: number; count: number };
  };
}) {
  const Icon = receivable ? TrendingUp : TrendingDown;
  const color = receivable ? "text-emerald-600" : "text-red-600";
  return (
    <Card>
      <CardContent className="p-5">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <Icon className={cn("h-4 w-4", color)} />
          {title}
        </h3>
        {data.overdue.count > 0 && (
          <div className="mb-3 flex items-center justify-between rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm">
            <span className="font-medium text-red-700">Vencidos hoje</span>
            <span className="font-mono font-semibold tabular-nums">
              {formatCurrencyBRL(data.overdue.total)}
              <span className="ml-1 text-[10px] opacity-70">({data.overdue.count})</span>
            </span>
          </div>
        )}
        <ul className="space-y-2">
          {[data.d30, data.d60, data.d90].map((win) => (
            <li
              key={win.days}
              className="flex items-center justify-between text-sm"
            >
              <span className="text-[color:var(--muted-foreground)]">{win.days} dias</span>
              <span className="font-mono tabular-nums">
                {formatCurrencyBRL(win.total)}
                <span className="ml-1 text-[10px] text-[color:var(--muted-foreground)]">
                  ({win.count})
                </span>
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
