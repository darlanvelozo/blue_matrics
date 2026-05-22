"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  CreditCard,
  ExternalLink,
  FileText,
  FlaskConical,
  Loader2,
  Sparkles,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  cancelSubscription,
  getSubscription,
  reactivateSubscription,
  startCheckout,
  type InvoiceData,
  type Plan,
  type PlanCode,
  type SubscriptionData,
} from "@/lib/billing";
import { cn, formatCurrencyBRL } from "@/lib/utils";

const STATUS_LABEL: Record<SubscriptionData["status"], { label: string; cls: string }> = {
  trialing: { label: "Em trial", cls: "bg-blue-500/10 text-blue-600 border-blue-500/30" },
  active: { label: "Ativa", cls: "bg-green-500/10 text-green-600 border-green-500/30" },
  past_due: { label: "Pagamento pendente", cls: "bg-amber-500/10 text-amber-600 border-amber-500/30" },
  canceled: { label: "Cancelada", cls: "bg-zinc-500/10 text-zinc-500 border-zinc-500/30" },
  incomplete: { label: "Incompleta", cls: "bg-red-500/10 text-red-600 border-red-500/30" },
};

export default function BillingPage() {
  return (
    <Suspense fallback={<div className="text-sm text-[color:var(--muted-foreground)]">Carregando…</div>}>
      <BillingInner />
    </Suspense>
  );
}

function BillingInner() {
  const params = useSearchParams();
  const qc = useQueryClient();
  const successFlag = params.get("status") === "success";
  const isMock = params.get("mock") === "1";

  const { data, isLoading, error } = useQuery({
    queryKey: ["billing", "subscription"],
    queryFn: getSubscription,
  });

  const checkoutMutation = useMutation({
    mutationFn: startCheckout,
    onSuccess: ({ url }) => {
      window.location.href = url;
    },
  });

  const cancelMutation = useMutation({
    mutationFn: cancelSubscription,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["billing", "subscription"] }),
  });

  const reactivateMutation = useMutation({
    mutationFn: reactivateSubscription,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["billing", "subscription"] }),
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <CreditCard className="h-6 w-6 text-blue-500" />
          Planos & Assinatura
        </h1>
        <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
          Gerencie seu plano, faturas e pagamentos.
        </p>
      </header>

      {successFlag && (
        <Banner kind="success">
          <CheckCircle2 className="h-4 w-4" />
          Assinatura atualizada com sucesso!{" "}
          {isMock && (
            <span className="text-xs opacity-80">
              (modo desenvolvimento — sem cobrança real)
            </span>
          )}
        </Banner>
      )}

      {isLoading ? (
        <Skeleton className="h-40" />
      ) : error instanceof ApiError ? (
        <Banner kind="error">
          <AlertTriangle className="h-4 w-4" />
          {error.message}
        </Banner>
      ) : !data ? null : (
        <>
          {data.provider === "mock" && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-xs text-amber-800 dark:text-amber-300">
              <span className="inline-flex items-center gap-2 font-medium">
                <FlaskConical className="h-3.5 w-3.5" />
                Modo desenvolvimento
              </span>
              <p className="mt-1">
                Stripe não está configurado — as ações aqui simulam o fluxo localmente
                (sem cobrança real). Para ativar pagamentos reais, configure{" "}
                <code className="rounded bg-amber-500/20 px-1">STRIPE_SECRET_KEY</code> no{" "}
                <code className="rounded bg-amber-500/20 px-1">.env</code>.
              </p>
            </div>
          )}

          <CurrentPlanCard
            data={data.subscription}
            onCancel={() => cancelMutation.mutate()}
            onReactivate={() => reactivateMutation.mutate()}
            cancelling={cancelMutation.isPending}
            reactivating={reactivateMutation.isPending}
          />

          {(cancelMutation.error || reactivateMutation.error) instanceof ApiError && (
            <Banner kind="error">
              <AlertTriangle className="h-4 w-4" />
              {(cancelMutation.error || reactivateMutation.error)?.message}
            </Banner>
          )}

          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[color:var(--muted-foreground)]">
              Trocar de plano
            </h2>
            <PlansGrid
              current={data.subscription.plan.code}
              onSelect={(code) => checkoutMutation.mutate(code)}
              busy={checkoutMutation.isPending}
              busyCode={checkoutMutation.variables}
            />
            {checkoutMutation.error instanceof ApiError && (
              <Banner kind="error" className="mt-3">
                <AlertTriangle className="h-4 w-4" />
                {checkoutMutation.error.message}
              </Banner>
            )}
          </section>

          <InvoicesCard invoices={data.invoices} />
        </>
      )}
    </div>
  );
}

// ============================================================
function CurrentPlanCard({
  data,
  onCancel,
  onReactivate,
  cancelling,
  reactivating,
}: {
  data: SubscriptionData;
  onCancel: () => void;
  onReactivate: () => void;
  cancelling: boolean;
  reactivating: boolean;
}) {
  const status = STATUS_LABEL[data.status];
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              {data.plan.name}
              <span className={cn(
                "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium",
                status.cls,
              )}>
                {status.label}
              </span>
            </CardTitle>
            <CardDescription className="mt-1">{data.plan.description}</CardDescription>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold">{formatCurrencyBRL(data.plan.price_monthly)}</p>
            <p className="text-xs text-[color:var(--muted-foreground)]">por mês</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="grid gap-2 sm:grid-cols-2">
          {data.plan.features.map((f) => (
            <li key={f} className="flex items-start gap-2 text-sm">
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-500" />
              {f}
            </li>
          ))}
        </ul>

        <dl className="grid grid-cols-1 gap-x-6 gap-y-1.5 border-t border-[color:var(--border)] pt-4 text-sm sm:grid-cols-2">
          {data.is_trialing && data.trial_ends_at && (
            <>
              <dt className="text-[color:var(--muted-foreground)]">Trial até</dt>
              <dd>{fmtDate(data.trial_ends_at)}</dd>
            </>
          )}
          {data.current_period_end && (
            <>
              <dt className="text-[color:var(--muted-foreground)]">Próxima cobrança</dt>
              <dd>{fmtDate(data.current_period_end)}</dd>
            </>
          )}
          {data.cancel_at_period_end && (
            <>
              <dt className="text-amber-600">Cancelamento agendado</dt>
              <dd className="text-amber-600">
                no fim do período atual
              </dd>
            </>
          )}
        </dl>

        <div className="flex flex-wrap gap-2">
          {data.cancel_at_period_end ? (
            <Button onClick={onReactivate} disabled={reactivating}>
              {reactivating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Reativar assinatura
            </Button>
          ) : data.status === "active" || data.status === "trialing" ? (
            <Button variant="outline" onClick={onCancel} disabled={cancelling}>
              {cancelling ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Cancelar assinatura
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================
function PlansGrid({
  current,
  onSelect,
  busy,
  busyCode,
}: {
  current: PlanCode;
  onSelect: (code: PlanCode) => void;
  busy: boolean;
  busyCode?: PlanCode;
}) {
  const { data: plansData, isLoading } = useQuery({
    queryKey: ["billing", "plans"],
    queryFn: async () => {
      const { listPlans } = await import("@/lib/billing");
      return listPlans();
    },
  });

  if (isLoading || !plansData) {
    return (
      <div className="grid gap-4 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-72" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {plansData.plans.map((p) => (
        <PlanCard
          key={p.code}
          plan={p}
          isCurrent={p.code === current}
          highlight={p.code === "growth"}
          onSelect={() => onSelect(p.code)}
          loading={busy && busyCode === p.code}
        />
      ))}
    </div>
  );
}

function PlanCard({
  plan,
  isCurrent,
  highlight,
  onSelect,
  loading,
}: {
  plan: Plan;
  isCurrent: boolean;
  highlight: boolean;
  onSelect: () => void;
  loading: boolean;
}) {
  return (
    <Card
      className={cn(
        "relative flex flex-col",
        highlight && "border-blue-500/40 shadow-lg ring-1 ring-blue-500/20",
      )}
    >
      {highlight && !isCurrent && (
        <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 rounded-full bg-blue-500 px-2.5 py-0.5 text-[10px] font-semibold text-white shadow">
          Mais popular
        </span>
      )}
      {isCurrent && (
        <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 rounded-full bg-green-500 px-2.5 py-0.5 text-[10px] font-semibold text-white shadow">
          Plano atual
        </span>
      )}
      <CardContent className="flex flex-1 flex-col p-5">
        <h3 className="text-base font-semibold">{plan.name}</h3>
        <p className="mt-1 text-xs text-[color:var(--muted-foreground)]">{plan.description}</p>
        <div className="mt-4 flex items-baseline gap-1">
          <span className="text-3xl font-bold">{formatCurrencyBRL(plan.price_monthly)}</span>
          <span className="text-xs text-[color:var(--muted-foreground)]">/mês</span>
        </div>
        <ul className="mt-4 flex-1 space-y-1.5 text-xs">
          {plan.features.map((f) => (
            <li key={f} className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-blue-500" />
              <span>{f}</span>
            </li>
          ))}
        </ul>
        <Button
          className="mt-5"
          variant={isCurrent ? "outline" : highlight ? "default" : "outline"}
          disabled={isCurrent || loading}
          onClick={onSelect}
        >
          {loading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : isCurrent ? null : (
            <Sparkles className="mr-2 h-3.5 w-3.5" />
          )}
          {isCurrent ? "Plano atual" : `Mudar para ${plan.name}`}
        </Button>
      </CardContent>
    </Card>
  );
}

// ============================================================
function InvoicesCard({ invoices }: { invoices: InvoiceData[] }) {
  if (invoices.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Faturas</CardTitle>
          <CardDescription>Suas faturas aparecerão aqui após a primeira cobrança.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Faturas</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <ul className="divide-y divide-[color:var(--border)]">
          {invoices.map((inv) => (
            <li key={inv.id} className="flex items-center justify-between px-6 py-3 text-sm">
              <div className="flex items-center gap-3">
                <FileText className="h-4 w-4 text-[color:var(--muted-foreground)]" />
                <div>
                  <p className="font-medium">{formatCurrencyBRL(inv.amount)}</p>
                  <p className="text-xs text-[color:var(--muted-foreground)]">
                    {inv.period_start && inv.period_end
                      ? `${fmtDate(inv.period_start)} → ${fmtDate(inv.period_end)}`
                      : fmtDate(inv.created_at)}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <InvoiceBadge status={inv.status} />
                {inv.hosted_invoice_url && !inv.hosted_invoice_url.startsWith("#") && (
                  <a
                    href={inv.hosted_invoice_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-[color:var(--primary)] hover:underline"
                  >
                    Ver fatura <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function InvoiceBadge({ status }: { status: InvoiceData["status"] }) {
  const map = {
    paid: { l: "Paga", c: "bg-green-500/10 text-green-600 border-green-500/30" },
    open: { l: "Em aberto", c: "bg-amber-500/10 text-amber-600 border-amber-500/30" },
    draft: { l: "Rascunho", c: "bg-zinc-500/10 text-zinc-500 border-zinc-500/30" },
    void: { l: "Anulada", c: "bg-zinc-500/10 text-zinc-500 border-zinc-500/30" },
    uncollectible: { l: "Não cobrada", c: "bg-red-500/10 text-red-600 border-red-500/30" },
  } as const;
  const it = map[status];
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${it.c}`}>
      {it.l}
    </span>
  );
}

// ============================================================
function Banner({
  kind,
  children,
  className,
}: {
  kind: "success" | "error";
  children: React.ReactNode;
  className?: string;
}) {
  const cls =
    kind === "success"
      ? "border-green-500/30 bg-green-500/10 text-green-700 dark:text-green-300"
      : "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300";
  return (
    <div className={cn("flex items-center gap-2 rounded-lg border px-4 py-3 text-sm", cls, className)}>
      {children}
    </div>
  );
}

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}
