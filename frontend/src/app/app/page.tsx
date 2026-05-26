"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  Banknote,
  BarChart3,
  Building2,
  CreditCard,
  Plug,
  ShoppingCart,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Wallet,
  Wand2,
} from "lucide-react";
import { CashflowChart } from "@/components/dashboards/charts";
import { KpiCard } from "@/components/dashboards/kpi-card";
import { RankingList } from "@/components/dashboards/ranking-list";
import { WelcomeWizard } from "@/components/onboarding/welcome-wizard";
import { ScoreGauge } from "@/components/overview/score-gauge";
import { SmartCardItem } from "@/components/overview/smart-card";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getOverview,
  type OverviewKpi,
  type OverviewResponse,
} from "@/lib/dashboards";
import { getContaAzulCredentials } from "@/lib/integrations";
import { listSyncLogs } from "@/lib/sync";
import { formatCurrencyBRL } from "@/lib/utils";

export default function HomePage() {
  const overview = useQuery({
    queryKey: ["overview"],
    queryFn: getOverview,
    refetchOnWindowFocus: false,
  });
  const ca = useQuery({
    queryKey: ["contaazul-credentials"],
    queryFn: getContaAzulCredentials,
    staleTime: 60_000,
  });
  const sync = useQuery({
    queryKey: ["sync-logs"],
    queryFn: listSyncLogs,
    staleTime: 60_000,
  });

  const data = overview.data;

  return (
    <div className="space-y-8">
      {/* Header */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-[color:var(--muted-foreground)]">
            Visão geral · {data?.period.current_month.label ?? "—"}
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">
            {data?.tenant?.name ?? "Sua empresa"}
          </h1>
          <p className="mt-0.5 text-sm text-[color:var(--muted-foreground)]">
            Resumo executivo automático com base nos dados sincronizados da Conta Azul.
          </p>
        </div>
        <Link
          href="/app/ai"
          className="group inline-flex items-center gap-2 rounded-lg bg-[color:var(--primary)] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:brightness-110"
        >
          <Wand2 className="h-4 w-4" />
          Perguntar à IA
          <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
        </Link>
      </header>

      {/* Loading state */}
      {overview.isLoading ? (
        <SkeletonSection />
      ) : !data?.has_data ? (
        <WelcomeWizard
          contaAzulConnected={Boolean(ca.data?.has_credentials)}
          syncCount={sync.data?.logs?.length ?? 0}
          syncSuccess={
            sync.data?.logs?.some((l) => l.status === "success") ?? false
          }
          hasAskedAi={
            typeof window !== "undefined" &&
            window.localStorage.getItem("biazul_has_asked_ai") === "1"
          }
        />
      ) : (
        <>
          {/* Cards inteligentes */}
          {data.smart_cards.length > 0 && (
            <section>
              <h2 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[color:var(--muted-foreground)]">
                <Sparkles className="h-3 w-3 text-[color:var(--primary)]" />
                Alertas e oportunidades · gerados automaticamente
              </h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {data.smart_cards.map((c, i) => (
                  <SmartCardItem key={i} card={c} />
                ))}
              </div>
            </section>
          )}

          {/* KPIs principais + Score */}
          <section className="grid gap-4 lg:grid-cols-[1fr_280px]">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <KpiCard
                label="Faturamento do mês"
                value={data.kpis.revenue_month.current}
                changePct={data.kpis.revenue_month.change_pct ?? null}
                sparkline={data.trend_12m.map((m) => ({ value: m.in }))}
                sparkColor="#10b981"
              />
              <KpiCard
                label="Lucro líquido"
                value={data.kpis.net_profit_month.current}
                changePct={data.kpis.net_profit_month.change_pct ?? null}
                sparkline={data.trend_12m.map((m) => ({ value: m.net }))}
              />
              <KpiCard
                label="Margem líquida"
                value={data.kpis.net_margin_pct.current}
                changePct={data.kpis.net_margin_pct.change_pct ?? null}
                format="percent"
              />
              <KpiCard
                label="EBITDA do mês"
                value={data.kpis.ebitda.current}
              />
              <KpiCard
                label="Saldo de caixa atual"
                value={data.kpis.cash_balance_now.current}
              />
              <KpiCard
                label="Burn rate mensal"
                value={data.kpis.burn_rate_monthly.current}
                positiveIsGood={false}
              />
            </div>
            <ScoreGauge score={data.health_score} />
          </section>

          {/* Ponto de equilíbrio + Forecast 30d */}
          <section className="grid gap-4 lg:grid-cols-2">
            <BreakevenCard data={data.kpis.breakeven} />
            <ForecastCard data={data.kpis.forecast_30d} />
          </section>

          {/* Receita vs despesa (12m) */}
          <Card>
            <CardContent className="p-5">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold">Receita vs Despesas</h2>
                  <p className="text-xs text-[color:var(--muted-foreground)]">
                    Últimos 12 meses
                  </p>
                </div>
                <Link
                  href="/app/dashboards/financeiro"
                  className="text-xs font-medium text-[color:var(--primary)] hover:underline"
                >
                  Ver financeiro →
                </Link>
              </div>
              <CashflowChart data={data.trend_12m} />
            </CardContent>
          </Card>

          {/* Top rankings */}
          <section className="grid gap-4 md:grid-cols-2">
            <RankingList
              title="Onde entra dinheiro"
              description="Categorias de receita do mês"
              rows={data.rankings.top_revenue_categories.map((c) => ({
                id: c.category_id,
                name: c.name,
                total: c.total,
                count: c.count,
                countLabel: "transações",
              }))}
            />
            <RankingList
              title="Onde sai dinheiro"
              description="Categorias de despesa do mês"
              rows={data.rankings.top_expense_categories.map((c) => ({
                id: c.category_id,
                name: c.name,
                total: c.total,
                count: c.count,
                countLabel: "transações",
              }))}
            />
          </section>

          <section className="grid gap-4 md:grid-cols-2">
            <RankingList
              title="Clientes VIP"
              description="Maiores pagadores no mês"
              rows={data.rankings.top_customers_receivable.map((c) => ({
                id: c.customer_id,
                name: c.name,
                total: c.total,
                count: c.count,
                countLabel: "transações",
              }))}
              emptyMessage="Sem clientes identificados no mês (à vista anônimo)."
            />
            <RankingList
              title="Principais fornecedores"
              description="Para quem mais pagamos no mês"
              rows={data.rankings.top_suppliers_payable.map((c) => ({
                id: c.customer_id,
                name: c.name,
                total: c.total,
                count: c.count,
                countLabel: "transações",
              }))}
            />
          </section>

          {/* Atalhos para dashboards */}
          <section>
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-[color:var(--muted-foreground)]">
              Aprofundar
            </h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Shortcut href="/app/dashboards/executivo" icon={BarChart3} title="Executivo" />
              <Shortcut href="/app/dashboards/financeiro" icon={Wallet} title="Financeiro" />
              <Shortcut href="/app/dashboards/comercial" icon={ShoppingCart} title="Comercial" />
              <Shortcut href="/app/insights" icon={Sparkles} title="Insights" />
            </div>
          </section>
        </>
      )}

      {/* Status footer */}
      <SystemFooter ca={ca.data} sync={sync.data} />
    </div>
  );
}

function BreakevenCard({ data }: { data: OverviewResponse["kpis"]["breakeven"] }) {
  const above = data.above;
  const pct = Math.min(100, Math.max(0, data.pct));
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-sm font-semibold">Ponto de equilíbrio</h3>
            <p className="text-xs text-[color:var(--muted-foreground)]">
              Receita necessária pra cobrir os custos
            </p>
          </div>
          <span
            className={
              above
                ? "rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-700"
                : "rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-700"
            }
          >
            {above ? "ACIMA" : "ABAIXO"}
          </span>
        </div>
        <div className="mt-4 space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-[color:var(--muted-foreground)]">Receita atual</span>
            <span className="font-mono font-semibold">{formatCurrencyBRL(data.revenue)}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-[color:var(--muted-foreground)]">Ponto de equilíbrio</span>
            <span className="font-mono">{formatCurrencyBRL(data.breakeven)}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-[color:var(--muted)]">
            <div
              className={above ? "h-full bg-emerald-500" : "h-full bg-amber-500"}
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-[color:var(--muted-foreground)]">
              {above ? "Sobra" : "Faltam"}
            </span>
            <span
              className={
                above
                  ? "font-mono font-semibold text-emerald-600"
                  : "font-mono font-semibold text-amber-600"
              }
            >
              {formatCurrencyBRL(Math.abs(data.diff))}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ForecastCard({ data }: { data: OverviewResponse["kpis"]["forecast_30d"] }) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-sm font-semibold">Previsão de caixa · 30 dias</h3>
            <p className="text-xs text-[color:var(--muted-foreground)]">
              Baseada em recebíveis e pagamentos em aberto
            </p>
          </div>
          {data.at_risk && (
            <span className="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] font-semibold text-red-700">
              <AlertCircle className="h-3 w-3" />
              EM RISCO
            </span>
          )}
        </div>
        <div className="mt-4 grid grid-cols-3 gap-3 text-center text-xs">
          <div>
            <p className="text-[color:var(--muted-foreground)]">Hoje</p>
            <p className="mt-1 font-mono text-sm font-semibold">
              {formatCurrencyBRL(data.current_balance)}
            </p>
          </div>
          <div>
            <p className="flex items-center justify-center gap-1 text-emerald-600">
              <TrendingUp className="h-3 w-3" /> Entradas
            </p>
            <p className="mt-1 font-mono text-sm">{formatCurrencyBRL(data.expected_in)}</p>
          </div>
          <div>
            <p className="flex items-center justify-center gap-1 text-red-600">
              <TrendingDown className="h-3 w-3" /> Saídas
            </p>
            <p className="mt-1 font-mono text-sm">{formatCurrencyBRL(data.expected_out)}</p>
          </div>
        </div>
        <div className="mt-4 rounded-md border border-[color:var(--border)] bg-[color:var(--muted)]/40 p-3 text-center">
          <p className="text-[10px] uppercase tracking-wide text-[color:var(--muted-foreground)]">
            Saldo projetado em 30 dias
          </p>
          <p
            className={
              data.projected_balance < 0
                ? "mt-1 font-mono text-xl font-bold text-red-600"
                : "mt-1 font-mono text-xl font-bold text-emerald-600"
            }
          >
            {formatCurrencyBRL(data.projected_balance)}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function Shortcut({
  href,
  icon: Icon,
  title,
}: {
  href: string;
  icon: typeof BarChart3;
  title: string;
}) {
  return (
    <Link
      href={href}
      className="group flex items-center gap-3 rounded-lg border border-[color:var(--border)] bg-[color:var(--card)] p-3 transition hover:border-[color:var(--primary)]/40 hover:shadow-sm"
    >
      <span className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-[color:var(--primary)]/10 text-[color:var(--primary)]">
        <Icon className="h-4 w-4" />
      </span>
      <span className="text-sm font-medium">{title}</span>
      <ArrowRight className="ml-auto h-3.5 w-3.5 text-[color:var(--muted-foreground)] transition group-hover:translate-x-0.5 group-hover:text-[color:var(--primary)]" />
    </Link>
  );
}

function SkeletonSection() {
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

function SystemFooter({ ca, sync }: { ca: unknown; sync: unknown }) {
  type Cred = { has_credentials?: boolean; status?: string };
  type Logs = { logs?: Array<{ resource: string; status: string; started_at: string }> };
  const credsTyped = ca as Cred | undefined;
  const syncTyped = sync as Logs | undefined;
  const connected =
    credsTyped?.has_credentials && (credsTyped?.status ?? "connected") === "connected";
  const lastSync = syncTyped?.logs?.find((l) => l.resource === "")?.started_at;

  return (
    <section className="grid gap-3 rounded-lg border border-[color:var(--border)] bg-[color:var(--card)] p-4 text-xs sm:grid-cols-3">
      <FooterItem
        icon={Plug}
        label="Integração Conta Azul"
        value={connected ? "Conectada" : "Pendente"}
        color={connected ? "text-emerald-600" : "text-amber-600"}
        href="/app/integrations"
      />
      <FooterItem
        icon={Banknote}
        label="Última sincronização"
        value={
          lastSync ? new Date(lastSync).toLocaleString("pt-BR") : "Nunca sincronizado"
        }
        color="text-[color:var(--muted-foreground)]"
        href="/app/sync"
      />
      <FooterItem
        icon={CreditCard}
        label="Plano"
        value="Trial"
        color="text-[color:var(--muted-foreground)]"
        href="/app/billing"
      />
    </section>
  );
}

function FooterItem({
  icon: Icon,
  label,
  value,
  color,
  href,
}: {
  icon: typeof Building2;
  label: string;
  value: string;
  color: string;
  href: string;
}) {
  return (
    <Link href={href} className="flex items-center gap-3 hover:bg-[color:var(--muted)] rounded-md p-1 -m-1">
      <span className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-[color:var(--muted)]">
        <Icon className="h-3.5 w-3.5 text-[color:var(--muted-foreground)]" />
      </span>
      <div>
        <p className="text-[10px] uppercase tracking-wide text-[color:var(--muted-foreground)]">
          {label}
        </p>
        <p className={`font-medium ${color}`}>{value}</p>
      </div>
    </Link>
  );
}
