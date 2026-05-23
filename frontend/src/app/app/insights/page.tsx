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
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
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
