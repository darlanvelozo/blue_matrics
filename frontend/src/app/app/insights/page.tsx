"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Brain,
  CheckCircle2,
  Info,
  Loader2,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Users,
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
    mutationFn: generateInsights,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insights"] }),
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
        <Button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
        >
          {generateMutation.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="mr-2 h-4 w-4" />
          )}
          Gerar insights agora
        </Button>
      </header>

      {generateMutation.error instanceof ApiError && (
        <Banner kind="error">{generateMutation.error.message}</Banner>
      )}
      {generateMutation.isSuccess && (
        <Banner kind="success">
          {generateMutation.data.stats.created} novo(s), {generateMutation.data.stats.updated}{" "}
          atualizado(s).
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
              <span
                className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-0.5 text-[10px] font-medium ${style.badge}`}
              >
                {style.badgeLabel}
              </span>
            </div>
            <p className="text-sm text-[color:var(--muted-foreground)]">{insight.narrative}</p>
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
  kind: "success" | "error";
  children: React.ReactNode;
}) {
  const cls =
    kind === "success"
      ? "border-green-500/30 bg-green-500/10 text-green-700 dark:text-green-300"
      : "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300";
  return (
    <div className={`flex items-center gap-2 rounded-lg border px-4 py-3 text-sm ${cls}`}>
      {kind === "success" ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
      {children}
    </div>
  );
}
