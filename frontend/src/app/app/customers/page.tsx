"use client";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Award,
  Heart,
  Search,
  Sparkles,
  Star,
  Users,
  UserX,
  Wand2,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Pagination } from "@/components/dashboards/pagination";
import {
  getCustomersAnalytics,
  type RfvCustomer,
  type RfvSegmentKey,
} from "@/lib/analytics";
import { listCustomers } from "@/lib/explorer";
import { formatCurrencyBRL, cn } from "@/lib/utils";

type FilterType = "all" | "customer" | "supplier" | "active";
const TYPE_LABELS: Record<FilterType, string> = {
  all: "Todos",
  active: "Com transações",
  customer: "Clientes (recebíveis)",
  supplier: "Fornecedores (a pagar)",
};

const SEGMENT_META: Record<
  RfvSegmentKey,
  { label: string; description: string; color: string; bg: string; icon: LucideIcon }
> = {
  champions: {
    label: "Champions",
    description: "Compram com frequência e alto valor",
    color: "text-emerald-700",
    bg: "bg-emerald-500/10 border-emerald-500/30",
    icon: Award,
  },
  high_value: {
    label: "Alto Valor",
    description: "Tickets altos, mesmo que esporádicos",
    color: "text-blue-700",
    bg: "bg-blue-500/10 border-blue-500/30",
    icon: Star,
  },
  loyal: {
    label: "Fiéis",
    description: "Recorrentes, ticket regular",
    color: "text-violet-700",
    bg: "bg-violet-500/10 border-violet-500/30",
    icon: Heart,
  },
  new: {
    label: "Novos",
    description: "Primeiras compras recentes",
    color: "text-cyan-700",
    bg: "bg-cyan-500/10 border-cyan-500/30",
    icon: Sparkles,
  },
  at_risk: {
    label: "Em risco",
    description: "Compravam mas estão sumindo",
    color: "text-amber-700",
    bg: "bg-amber-500/10 border-amber-500/30",
    icon: AlertTriangle,
  },
  lost: {
    label: "Perdidos",
    description: "Inativos há tempo significativo",
    color: "text-red-700",
    bg: "bg-red-500/10 border-red-500/30",
    icon: UserX,
  },
};

const SEGMENT_ORDER: RfvSegmentKey[] = [
  "champions",
  "high_value",
  "loyal",
  "new",
  "at_risk",
  "lost",
];

export default function CustomersPage() {
  const [q, setQ] = useState("");
  const [type, setType] = useState<FilterType>("active");
  const [page, setPage] = useState(1);

  const analytics = useQuery({
    queryKey: ["customers-analytics"],
    queryFn: getCustomersAnalytics,
    staleTime: 60_000,
  });

  const explorer = useQuery({
    queryKey: ["customers", q, type, page],
    queryFn: () => listCustomers({ q: q || undefined, type, page, page_size: 20 }),
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <Users className="h-6 w-6 text-blue-500" />
          Clientes & Fornecedores
        </h1>
        <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
          Segmentação RFV (Recência · Frequência · Valor) automática, clientes
          em risco e ranking financeiro.
        </p>
      </header>

      {/* KPIs LTV + Recompra */}
      {analytics.data && (
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <KpiTile
            label="LTV médio"
            value={formatCurrencyBRL(analytics.data.ltv.ltv_avg)}
            subtitle={`${analytics.data.ltv.unique_customers} clientes únicos`}
          />
          <KpiTile
            label="Taxa de recompra"
            value={`${analytics.data.repurchase.rate_pct.toFixed(1).replace(".", ",")}%`}
            subtitle={`${analytics.data.repurchase.repurchased}/${analytics.data.repurchase.total_customers} em 90d`}
          />
          <KpiTile
            label="Clientes RFV"
            value={analytics.data.rfv.total.toLocaleString("pt-BR")}
            subtitle="Únicos com transações"
          />
          <KpiTile
            label="Em risco"
            value={analytics.data.at_risk.length.toString()}
            subtitle="Sumiram há 60+ dias"
            danger
          />
        </section>
      )}

      {/* Segmentação RFV */}
      {analytics.data && analytics.data.rfv.total > 0 && (
        <section className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-[color:var(--muted-foreground)]">
            Segmentação RFV
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {SEGMENT_ORDER.map((key) => (
              <SegmentCard
                key={key}
                segmentKey={key}
                count={analytics.data!.rfv.counts[key] ?? 0}
                top={analytics.data!.rfv.segments[key] ?? []}
              />
            ))}
          </div>
        </section>
      )}

      {/* Clientes em risco */}
      {analytics.data && analytics.data.at_risk.length > 0 && (
        <Card>
          <CardContent className="p-5">
            <div className="mb-3 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              <h3 className="text-sm font-semibold">
                Clientes em risco (sumiram há 60+ dias)
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[color:var(--border)] text-xs text-[color:var(--muted-foreground)]">
                    <th className="px-3 py-2 text-left">Cliente</th>
                    <th className="px-3 py-2 text-right">Total comprado</th>
                    <th className="px-3 py-2 text-right">Compras</th>
                    <th className="px-3 py-2 text-right">Dias inativo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--border)]">
                  {analytics.data.at_risk.slice(0, 10).map((c) => (
                    <tr key={c.customer_id}>
                      <td className="px-3 py-2 font-medium">{c.name}</td>
                      <td className="px-3 py-2 text-right font-mono tabular-nums">
                        {formatCurrencyBRL(c.total_purchased)}
                      </td>
                      <td className="px-3 py-2 text-right">{c.purchases}</td>
                      <td className="px-3 py-2 text-right">
                        <span
                          className={cn(
                            "rounded px-2 py-0.5 text-xs font-medium",
                            c.days_inactive > 180
                              ? "bg-red-500/10 text-red-700"
                              : "bg-amber-500/10 text-amber-700",
                          )}
                        >
                          {c.days_inactive} dias
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filtros + tabela explorer */}
      <section className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-[color:var(--muted-foreground)]">
          Listagem completa
        </h2>
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative max-w-md flex-1">
            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[color:var(--muted-foreground)]" />
            <Input
              placeholder="Buscar por nome..."
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
              className="pl-9"
            />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(Object.keys(TYPE_LABELS) as FilterType[]).map((t) => (
              <button
                key={t}
                onClick={() => {
                  setType(t);
                  setPage(1);
                }}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs transition",
                  type === t
                    ? "border-[color:var(--primary)] bg-[color:var(--primary)] text-white"
                    : "border-[color:var(--border)] hover:bg-[color:var(--muted)]",
                )}
              >
                {TYPE_LABELS[t]}
              </button>
            ))}
          </div>
        </div>

        {explorer.isLoading ? (
          <Skeleton className="h-64" />
        ) : !explorer.data || explorer.data.results.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center text-sm text-[color:var(--muted-foreground)]">
              Nenhuma pessoa encontrada.
            </CardContent>
          </Card>
        ) : (
          <>
            <Card>
              <CardContent className="p-0 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[color:var(--border)] text-xs text-[color:var(--muted-foreground)]">
                      <th className="px-4 py-3 text-left">Nome</th>
                      <th className="px-4 py-3 text-left">Tipo</th>
                      <th className="px-4 py-3 text-right">Recebido</th>
                      <th className="px-4 py-3 text-right">Pago</th>
                      <th className="px-4 py-3 text-right">Transações</th>
                      <th className="px-4 py-3 text-right">Última</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[color:var(--border)]">
                    {explorer.data.results.map((c) => (
                      <tr key={c.id} className="hover:bg-[color:var(--muted)]/40">
                        <td className="px-4 py-3 font-medium">{c.name || "(sem nome)"}</td>
                        <td className="px-4 py-3 text-xs">
                          {c.type === "—" ? (
                            <span className="text-[color:var(--muted-foreground)]">—</span>
                          ) : (
                            <span className="inline-flex flex-wrap gap-1">
                              {c.type.split(" · ").map((tag) => (
                                <span
                                  key={tag}
                                  className={cn(
                                    "rounded-full border px-2 py-0.5 text-[10px]",
                                    tag === "Cliente"
                                      ? "border-green-500/30 bg-green-500/10 text-green-700"
                                      : "border-red-500/30 bg-red-500/10 text-red-700",
                                  )}
                                >
                                  {tag}
                                </span>
                              ))}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right font-mono tabular-nums">
                          {c.total_received > 0 ? (
                            <span className="text-green-600">
                              {formatCurrencyBRL(c.total_received)}
                            </span>
                          ) : (
                            <span className="text-[color:var(--muted-foreground)]">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right font-mono tabular-nums">
                          {c.total_paid > 0 ? (
                            <span className="text-red-600">
                              {formatCurrencyBRL(c.total_paid)}
                            </span>
                          ) : (
                            <span className="text-[color:var(--muted-foreground)]">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right text-xs">
                          {c.received_count + c.paid_count > 0
                            ? `${c.received_count + c.paid_count}`
                            : "—"}
                        </td>
                        <td className="px-4 py-3 text-right text-xs text-[color:var(--muted-foreground)]">
                          {c.last_transaction
                            ? new Date(c.last_transaction).toLocaleDateString("pt-BR")
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
            <Pagination meta={explorer.data.meta} onChange={setPage} />
          </>
        )}
      </section>

      {/* CTA IA */}
      <Link
        href="/app/ai"
        className="flex items-center justify-between rounded-lg border border-[color:var(--primary)]/30 bg-gradient-to-r from-[color:var(--primary)]/10 to-purple-500/10 p-4 transition hover:border-[color:var(--primary)]/50"
      >
        <div className="flex items-center gap-3">
          <Wand2 className="h-5 w-5 text-[color:var(--primary)]" />
          <div>
            <p className="text-sm font-semibold">
              Pergunte: &quot;Quem são meus clientes campeões?&quot;
            </p>
            <p className="text-xs text-[color:var(--muted-foreground)]">
              A IA detalha cada segmento + estratégias de retenção.
            </p>
          </div>
        </div>
        <span className="text-sm font-medium text-[color:var(--primary)]">Conversar →</span>
      </Link>
    </div>
  );
}

function KpiTile({
  label,
  value,
  subtitle,
  danger,
}: {
  label: string;
  value: string;
  subtitle?: string;
  danger?: boolean;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">
          {label}
        </p>
        <p
          className={cn(
            "mt-1 font-mono text-xl font-semibold tabular-nums",
            danger && "text-amber-600",
          )}
        >
          {value}
        </p>
        {subtitle && (
          <p className="mt-0.5 text-[10px] text-[color:var(--muted-foreground)]">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}

function SegmentCard({
  segmentKey,
  count,
  top,
}: {
  segmentKey: RfvSegmentKey;
  count: number;
  top: RfvCustomer[];
}) {
  const meta = SEGMENT_META[segmentKey];
  const Icon = meta.icon;
  return (
    <Card>
      <CardContent className={cn("border-l-2 p-4", meta.bg)}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <Icon className={cn("h-4 w-4", meta.color)} />
            <span className={cn("font-semibold", meta.color)}>{meta.label}</span>
          </div>
          <span className={cn("rounded-full px-2 py-0.5 text-xs font-bold", meta.color)}>
            {count}
          </span>
        </div>
        <p className="mt-1 text-[11px] text-[color:var(--muted-foreground)]">
          {meta.description}
        </p>
        {top.length > 0 && (
          <ul className="mt-3 space-y-1 text-xs">
            {top.slice(0, 3).map((c) => (
              <li key={c.customer_id} className="flex justify-between gap-2 truncate">
                <span className="truncate">{c.name}</span>
                <span className="shrink-0 font-mono tabular-nums">
                  {formatCurrencyBRL(c.total)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
