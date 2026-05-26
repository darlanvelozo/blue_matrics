"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Brain,
  Building2,
  CalendarClock,
  Info,
  Loader2,
  PieChart,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Users,
  Wand2,
  X,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { getPredictive, type PredictiveResponse } from "@/lib/dashboards";
import { formatCurrencyBRL, cn } from "@/lib/utils";
import {
  dismissInsight,
  generateInsights,
  listInsights,
  markInsightRead,
  type Insight,
  type InsightKind,
  type InsightSeverity,
} from "@/lib/insights";

const KIND_ICON: Record<InsightKind, LucideIcon> = {
  revenue_drop: TrendingDown,
  revenue_surge: TrendingUp,
  expense_surge: TrendingUp,
  ticket_drop: TrendingDown,
  top_customer: Users,
  top_product: Sparkles,
  inactive_customer: Users,
  overdue_high: AlertTriangle,
  cash_negative: XCircle,
  seasonality: Info,
  top_expense_category: PieChart,
  top_revenue_category: PieChart,
  upcoming_payables: CalendarClock,
  supplier_concentration: Building2,
  cash_in_trend: TrendingUp,
};

const SEVERITY_STYLE: Record<
  InsightSeverity,
  { iconBg: string; iconText: string; badge: string; badgeLabel: string }
> = {
  info: {
    iconBg: "bg-blue-500/10",
    iconText: "text-blue-500",
    badge: "border-blue-500/30 bg-blue-500/10 text-blue-600",
    badgeLabel: "Informação",
  },
  success: {
    iconBg: "bg-green-500/10",
    iconText: "text-green-500",
    badge: "border-green-500/30 bg-green-500/10 text-green-600",
    badgeLabel: "Positivo",
  },
  warning: {
    iconBg: "bg-amber-500/10",
    iconText: "text-amber-500",
    badge: "border-amber-500/30 bg-amber-500/10 text-amber-600",
    badgeLabel: "Atenção",
  },
  critical: {
    iconBg: "bg-red-500/10",
    iconText: "text-red-500",
    badge: "border-red-500/30 bg-red-500/10 text-red-600",
    badgeLabel: "Crítico",
  },
};

export default function InsightsPage() {
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["insights"],
    queryFn: listInsights,
  });

  const predictive = useQuery({
    queryKey: ["predictive"],
    queryFn: getPredictive,
    staleTime: 60_000,
  });

  const generateMutation = useMutation({
    mutationFn: (opts: { enrich?: boolean } = {}) => generateInsights(opts),
    onSuccess: async () => {
      // Invalida E força refetch imediato (sem esperar staleTime).
      await qc.invalidateQueries({ queryKey: ["insights"] });
      await qc.refetchQueries({ queryKey: ["insights"], type: "active" });
      // Scroll suave pro topo da lista para o usuário ver os insights
      if (typeof window !== "undefined") {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
  });

  const dismissMutation = useMutation({
    mutationFn: dismissInsight,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insights"] }),
  });

  const readMutation = useMutation({
    mutationFn: markInsightRead,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insights"] }),
  });

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            <Brain className="h-6 w-6 text-blue-500" />
            Insights
          </h1>
          <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
            Observações automáticas sobre seus dados.
            {data?.unread ? ` ${data.unread} não lido${data.unread > 1 ? "s" : ""}.` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            onClick={() => generateMutation.mutate({ enrich: false })}
            disabled={generateMutation.isPending}
          >
            {generateMutation.isPending && generateMutation.variables?.enrich === false ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="mr-2 h-4 w-4" />
            )}
            Gerar com regras
          </Button>
          <Button
            onClick={() => generateMutation.mutate({ enrich: true })}
            disabled={generateMutation.isPending}
          >
            {generateMutation.isPending && generateMutation.variables?.enrich === true ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Wand2 className="mr-2 h-4 w-4" />
            )}
            Gerar com IA
          </Button>
        </div>
      </header>

      {generateMutation.error instanceof ApiError && (
        <Banner kind="error">{generateMutation.error.message}</Banner>
      )}
      {generateMutation.isSuccess && (
        <Banner kind={generateMutation.data.llm.requested && !generateMutation.data.llm.enabled ? "warning" : "success"}>
          {generateMutation.data.stats.created} novo(s),{" "}
          {generateMutation.data.stats.updated} atualizado(s).
          {generateMutation.data.llm.requested && generateMutation.data.llm.enabled && (
            <>
              {" "}
              <strong>{generateMutation.data.llm.enriched ?? 0}</strong> enriquecido(s) com IA.
            </>
          )}
          {generateMutation.data.llm.requested && !generateMutation.data.llm.enabled && (
            <>
              {" "}
              <em>IA não configurada</em> — preencha <code>OPENAI_API_KEY</code> e{" "}
              <code>INSIGHT_LLM_PROVIDER=openai</code> no .env para ativar.
            </>
          )}
        </Banner>
      )}

      {/* SEÇÃO PREDITIVA — previsão IA + risco de inadimplência */}
      {predictive.data && <PredictivePanel data={predictive.data} />}

      {isLoading ? (
        <div className="grid gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : error instanceof ApiError ? (
        <Banner kind="error">{error.message}</Banner>
      ) : !data || data.total === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/10 text-blue-500">
              <Brain className="h-5 w-5" />
            </span>
            <h2 className="text-lg font-semibold">Nenhum insight ainda</h2>
            <p className="max-w-sm text-sm text-[color:var(--muted-foreground)]">
              Clique em <strong>Gerar insights agora</strong> para analisarmos seus dados e te
              avisar sobre quedas, picos, clientes inativos e mais.
            </p>
          </CardContent>
        </Card>
      ) : (
        <ul className="space-y-3">
          {data.insights.map((insight) => (
            <InsightCard
              key={insight.id}
              insight={insight}
              onRead={() => !insight.is_read && readMutation.mutate(insight.id)}
              onDismiss={() => dismissMutation.mutate(insight.id)}
              dismissing={dismissMutation.isPending && dismissMutation.variables === insight.id}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function InsightCard({
  insight,
  onRead,
  onDismiss,
  dismissing,
}: {
  insight: Insight;
  onRead: () => void;
  onDismiss: () => void;
  dismissing: boolean;
}) {
  const Icon = KIND_ICON[insight.kind] ?? Info;
  const style = SEVERITY_STYLE[insight.severity];

  return (
    <li>
      <Card className={insight.is_read ? "opacity-70" : ""}>
        <CardContent className="flex gap-4 p-5" onClick={onRead}>
          <span
            className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${style.iconBg} ${style.iconText}`}
          >
            <Icon className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1 space-y-1.5">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h3 className="font-semibold leading-tight">{insight.title}</h3>
              <span className="flex shrink-0 items-center gap-1.5">
                {insight.generated_by === "llm" && (
                  <span className="inline-flex items-center gap-1 rounded-full border border-purple-500/30 bg-purple-500/10 px-2 py-0.5 text-[10px] font-medium text-purple-600">
                    <Wand2 className="h-3 w-3" /> IA
                  </span>
                )}
                <span
                  className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-medium ${style.badge}`}
                >
                  {style.badgeLabel}
                </span>
              </span>
            </div>
            <p className="text-sm text-[color:var(--muted-foreground)]">{insight.narrative}</p>
            {Array.isArray(insight.data?.recommendations) &&
              (insight.data.recommendations as string[]).length > 0 && (
                <ul className="mt-2 space-y-1 rounded-md border border-[color:var(--border)]/60 bg-[color:var(--muted)]/40 px-3 py-2 text-xs">
                  <li className="font-medium text-[color:var(--muted-foreground)]">
                    Recomendações
                  </li>
                  {(insight.data.recommendations as string[]).map((r, i) => (
                    <li key={i} className="flex gap-2 text-[color:var(--foreground)]">
                      <span className="text-purple-500">›</span>
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              )}
            <p className="text-xs text-[color:var(--muted-foreground)]/70">
              {new Date(insight.created_at).toLocaleString("pt-BR", {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
              {!insight.is_read && (
                <>
                  {" · "}
                  <span className="font-semibold text-blue-600 dark:text-blue-400">
                    não lido
                  </span>
                </>
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDismiss();
            }}
            disabled={dismissing}
            className="self-start rounded p-1 text-[color:var(--muted-foreground)] hover:bg-[color:var(--accent)]"
            aria-label="Dispensar"
          >
            {dismissing ? <Loader2 className="h-4 w-4 animate-spin" /> : <X className="h-4 w-4" />}
          </button>
        </CardContent>
      </Card>
    </li>
  );
}

function Banner({
  kind,
  children,
}: {
  kind: "success" | "error" | "warning";
  children: React.ReactNode;
}) {
  const cls =
    kind === "success"
      ? "border-green-500/30 bg-green-500/10 text-green-700 dark:text-green-300"
      : kind === "warning"
      ? "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300"
      : "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300";
  return (
    <div className={`flex items-center gap-2 rounded-lg border px-4 py-3 text-sm ${cls}`}>
      {kind === "success" ? (
        <Sparkles className="h-4 w-4" />
      ) : (
        <AlertTriangle className="h-4 w-4" />
      )}
      <span>{children}</span>
    </div>
  );
}

function PredictivePanel({ data }: { data: PredictiveResponse }) {
  const p = data.predictive;
  const confidence30 = p.revenue_forecast["30d"].confidence;
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-widest text-[color:var(--muted-foreground)]">
          <Sparkles className="h-3 w-3 text-[color:var(--primary)]" />
          Previsões IA · próximos dias
        </h2>
        <Link
          href="/app/ai"
          className="text-xs font-medium text-[color:var(--primary)] hover:underline"
        >
          Conversar com IA →
        </Link>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <PredictiveCard
          label="Receita prevista 30d"
          value={p.revenue_forecast["30d"].forecast_total}
          format="currency"
          subtitle={`tendência ${p.revenue_forecast["30d"].trend_pct_monthly > 0 ? "+" : ""}${p.revenue_forecast["30d"].trend_pct_monthly.toFixed(1).replace(".", ",")}%/mês`}
          confidence={confidence30}
        />
        <PredictiveCard
          label="Receita prevista 90d"
          value={p.revenue_forecast["90d"].forecast_total}
          format="currency"
        />
        <PredictiveCard
          label="Despesa prevista 30d"
          value={p.expense_forecast_30d.forecast_total}
          format="currency"
          subtitle={`média histórica: ${formatCurrencyBRL(p.expense_forecast_30d.baseline_avg_monthly)}/mês`}
          negative
        />
        <PredictiveCard
          label="Saldo projetado 30d"
          value={p.cash_forecast["30d"].projected_balance}
          format="currency"
          atRisk={p.cash_forecast["30d"].at_risk}
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <PredictiveCard
          label="LTV médio"
          value={p.ltv.ltv_avg}
          format="currency"
          subtitle={
            p.ltv.low_confidence
              ? `${p.ltv.unique_customers} clientes nomeados (${(p.ltv.anonymous_pct || 0).toFixed(0)}% da receita é anônima)`
              : `${p.ltv.unique_customers} clientes únicos`
          }
        />
        <PredictiveCard
          label="Taxa de recompra (90d)"
          value={p.repurchase.rate_pct}
          format="percent"
          subtitle={`${p.repurchase.repurchased}/${p.repurchase.total_customers} clientes`}
        />
        <PredictiveCard
          label="Risco de inadimplência"
          value={p.overdue_risk.risk_pct}
          format="percent"
          negative
          subtitle={`${formatCurrencyBRL(p.overdue_risk.overdue_amount)} vencido`}
        />
      </div>
    </section>
  );
}

function PredictiveCard({
  label,
  value,
  format,
  subtitle,
  confidence,
  negative,
  atRisk,
}: {
  label: string;
  value: number;
  format: "currency" | "percent";
  subtitle?: string;
  confidence?: "high" | "medium" | "low";
  negative?: boolean;
  atRisk?: boolean;
}) {
  const formatted =
    format === "currency"
      ? formatCurrencyBRL(value)
      : `${value.toFixed(1).replace(".", ",")}%`;
  const confMap: Record<string, { label: string; cls: string }> = {
    high: { label: "alta", cls: "bg-emerald-500/10 text-emerald-700" },
    medium: { label: "média", cls: "bg-amber-500/10 text-amber-700" },
    low: { label: "baixa", cls: "bg-red-500/10 text-red-700" },
  };
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <p className="text-xs font-medium uppercase tracking-wide text-[color:var(--muted-foreground)]">
            {label}
          </p>
          {confidence && (
            <span className={cn("rounded-full px-1.5 py-0.5 text-[9px] font-semibold", confMap[confidence].cls)}>
              {confMap[confidence].label}
            </span>
          )}
          {atRisk && (
            <span className="rounded-full bg-red-500/10 px-1.5 py-0.5 text-[9px] font-semibold text-red-700">
              RISCO
            </span>
          )}
        </div>
        <p
          className={cn(
            "mt-2 font-mono text-xl font-bold tabular-nums",
            atRisk || (negative && value > 0) ? "text-red-600" : value > 0 ? "text-foreground" : "text-[color:var(--muted-foreground)]",
          )}
        >
          {formatted}
        </p>
        {subtitle && (
          <p className="mt-1 text-[10px] text-[color:var(--muted-foreground)]">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}
