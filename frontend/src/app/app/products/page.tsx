"use client";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  Package,
  Search,
  ShoppingBag,
  TrendingDown,
  Wand2,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Pagination } from "@/components/dashboards/pagination";
import { getProductsAnalytics, type AbcRow } from "@/lib/analytics";
import { listProducts } from "@/lib/explorer";
import { cn, formatCurrencyBRL } from "@/lib/utils";

type Tab = "abc" | "stagnant" | "reorder" | "all";

const TAB_LABELS: Record<Tab, string> = {
  abc: "Curva ABC",
  stagnant: "Parados",
  reorder: "Reposição",
  all: "Catálogo completo",
};

export default function ProductsPage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [tab, setTab] = useState<Tab>("abc");
  const [abcBy, setAbcBy] = useState<"stock_value" | "sales">("stock_value");

  const explorer = useQuery({
    queryKey: ["products", q, page],
    queryFn: () => listProducts({ q: q || undefined, page, page_size: 20 }),
    enabled: tab === "all",
  });

  const analytics = useQuery({
    queryKey: ["products-analytics", abcBy],
    queryFn: () => getProductsAnalytics({ by: abcBy }),
    staleTime: 60_000,
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <Package className="h-6 w-6 text-blue-500" />
          Produtos & Estoque
        </h1>
        <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
          Curva ABC, produtos parados, sugestão de recompra e catálogo completo
          sincronizados da Conta Azul.
        </p>
      </header>

      {/* KPIs principais sempre visíveis */}
      {analytics.data && (
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <KpiTile
            label="Valor em estoque"
            value={formatCurrencyBRL(analytics.data.abc.total)}
            subtitle={`${analytics.data.abc.by === "sales" ? "por receita" : "saldo × custo"}`}
          />
          <KpiTile
            label="Classe A"
            value={analytics.data.abc.counts.A.toString()}
            subtitle="produtos (80% do valor)"
            tone="emerald"
          />
          <KpiTile
            label="Parados"
            value={analytics.data.stagnant.length.toString()}
            subtitle={`R$ ${analytics.data.stagnant.reduce((a, s) => a + s.stuck_value, 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} travado`}
            tone="red"
          />
          <KpiTile
            label="Para repor"
            value={analytics.data.reorder.total_count.toString()}
            subtitle={`em ${analytics.data.reorder.target_coverage_days}d`}
            tone="amber"
          />
        </section>
      )}

      {/* Tabs */}
      <div className="flex flex-wrap gap-1.5 border-b border-[color:var(--border)] pb-px">
        {(Object.keys(TAB_LABELS) as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "rounded-t-md border-b-2 px-3 py-2 text-sm transition",
              tab === t
                ? "border-[color:var(--primary)] font-semibold text-[color:var(--primary)]"
                : "border-transparent text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)]",
            )}
          >
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      {/* CONTEÚDO POR TAB */}
      {tab === "abc" && (
        <>
          <div className="flex items-center gap-2">
            <span className="text-xs text-[color:var(--muted-foreground)]">Ordenar por:</span>
            {(["stock_value", "sales"] as const).map((b) => (
              <button
                key={b}
                onClick={() => setAbcBy(b)}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs",
                  abcBy === b
                    ? "border-[color:var(--primary)] bg-[color:var(--primary)] text-white"
                    : "border-[color:var(--border)] hover:bg-[color:var(--muted)]",
                )}
              >
                {b === "stock_value" ? "Valor em estoque" : "Receita de vendas"}
              </button>
            ))}
          </div>
          {analytics.isLoading ? (
            <Skeleton className="h-96" />
          ) : analytics.data && analytics.data.abc.rows.length > 0 ? (
            <AbcTable rows={analytics.data.abc.rows} />
          ) : (
            <EmptyCard
              icon={<Package className="h-5 w-5" />}
              title="Sem dados de Curva ABC"
              message={
                abcBy === "sales"
                  ? "Este tenant não tem vendas formais (SaleItem). Tente ordenar por 'Valor em estoque'."
                  : "Nenhum produto com estoque e custo > 0."
              }
            />
          )}
        </>
      )}

      {tab === "stagnant" && (
        <>
          {analytics.isLoading ? (
            <Skeleton className="h-96" />
          ) : analytics.data && analytics.data.stagnant.length > 0 ? (
            <Card>
              <CardContent className="p-0 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[color:var(--border)] text-xs text-[color:var(--muted-foreground)]">
                      <th className="px-4 py-3 text-left">SKU</th>
                      <th className="px-4 py-3 text-left">Produto</th>
                      <th className="px-4 py-3 text-right">Estoque</th>
                      <th className="px-4 py-3 text-right">Custo unit.</th>
                      <th className="px-4 py-3 text-right">Valor travado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[color:var(--border)]">
                    {analytics.data.stagnant.map((p) => (
                      <tr key={p.product_id}>
                        <td className="px-4 py-2 font-mono text-xs">{p.sku}</td>
                        <td className="px-4 py-2">{p.name}</td>
                        <td className="px-4 py-2 text-right font-mono tabular-nums">
                          {p.stock.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}
                        </td>
                        <td className="px-4 py-2 text-right font-mono tabular-nums text-[color:var(--muted-foreground)]">
                          {formatCurrencyBRL(p.cost)}
                        </td>
                        <td className="px-4 py-2 text-right font-mono font-semibold tabular-nums text-amber-700">
                          {formatCurrencyBRL(p.stuck_value)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          ) : (
            <EmptyCard
              icon={<ShoppingBag className="h-5 w-5" />}
              title="Sem produtos parados"
              message="Bom sinal — todo produto ativo com estoque tem alguma saída no histórico."
            />
          )}
        </>
      )}

      {tab === "reorder" && (
        <>
          {analytics.isLoading ? (
            <Skeleton className="h-96" />
          ) : analytics.data && analytics.data.reorder.suggestions.length > 0 ? (
            <Card>
              <CardContent className="p-0 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[color:var(--border)] text-xs text-[color:var(--muted-foreground)]">
                      <th className="px-4 py-3 text-left">SKU</th>
                      <th className="px-4 py-3 text-left">Produto</th>
                      <th className="px-4 py-3 text-right">Estoque</th>
                      <th className="px-4 py-3 text-right">Cobertura</th>
                      <th className="px-4 py-3 text-right">Qtd. sugerida</th>
                      <th className="px-4 py-3 text-right">Custo estimado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[color:var(--border)]">
                    {analytics.data.reorder.suggestions.map((s) => (
                      <tr key={s.product_id}>
                        <td className="px-4 py-2 font-mono text-xs">{s.sku}</td>
                        <td className="px-4 py-2">{s.name}</td>
                        <td className="px-4 py-2 text-right font-mono tabular-nums">
                          {s.stock.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}
                        </td>
                        <td className="px-4 py-2 text-right">
                          <span
                            className={cn(
                              "rounded px-2 py-0.5 text-xs font-medium",
                              s.coverage_days < 7
                                ? "bg-red-500/10 text-red-700"
                                : s.coverage_days < 15
                                ? "bg-amber-500/10 text-amber-700"
                                : "bg-blue-500/10 text-blue-700",
                            )}
                          >
                            {s.coverage_days.toFixed(0)}d
                          </span>
                        </td>
                        <td className="px-4 py-2 text-right font-mono font-semibold tabular-nums">
                          {s.suggested_qty.toLocaleString("pt-BR")}
                        </td>
                        <td className="px-4 py-2 text-right font-mono tabular-nums">
                          {formatCurrencyBRL(s.reorder_cost_estimate)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          ) : (
            <EmptyCard
              icon={<AlertCircle className="h-5 w-5" />}
              title="Nenhuma sugestão de recompra"
              message="Sem vendas suficientes pra calcular velocidade de saída, ou todos os produtos têm cobertura > 30 dias."
            />
          )}
        </>
      )}

      {tab === "all" && (
        <>
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[color:var(--muted-foreground)]" />
            <Input
              placeholder="Buscar por nome ou SKU..."
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
              className="pl-9"
            />
          </div>

          {explorer.isLoading ? (
            <Skeleton className="h-96" />
          ) : !explorer.data || explorer.data.results.length === 0 ? (
            <EmptyCard
              icon={<Package className="h-5 w-5" />}
              title="Nenhum produto encontrado"
              message="Refine a busca ou aguarde uma nova sincronização."
            />
          ) : (
            <>
              <Card>
                <CardContent className="p-0 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-[color:var(--border)] text-xs text-[color:var(--muted-foreground)]">
                        <th className="px-4 py-3 text-left">Nome</th>
                        <th className="px-4 py-3 text-left">SKU</th>
                        <th className="px-4 py-3 text-right">Custo</th>
                        <th className="px-4 py-3 text-right">Preço</th>
                        <th className="px-4 py-3 text-right">Margem</th>
                        <th className="px-4 py-3 text-right">Estoque</th>
                        <th className="px-4 py-3 text-right">Valor</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[color:var(--border)]">
                      {explorer.data.results.map((p) => (
                        <tr key={p.id} className="hover:bg-[color:var(--muted)]/40">
                          <td className="px-4 py-3 font-medium">{p.name}</td>
                          <td className="px-4 py-3 font-mono text-xs text-[color:var(--muted-foreground)]">
                            {p.sku || "—"}
                          </td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums">
                            {p.cost > 0 ? (
                              formatCurrencyBRL(p.cost)
                            ) : (
                              <span className="text-[color:var(--muted-foreground)]">—</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums">
                            {p.price > 0 ? (
                              formatCurrencyBRL(p.price)
                            ) : (
                              <span className="text-[10px] font-medium text-amber-600">
                                não cadastrado
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {p.price > 0 && p.cost > 0 ? (
                              <span
                                className={cn(
                                  "font-mono",
                                  p.margin_pct > 50
                                    ? "text-green-600"
                                    : p.margin_pct > 20
                                    ? "text-amber-600"
                                    : "text-red-600",
                                )}
                              >
                                {p.margin_pct.toFixed(1)}%
                              </span>
                            ) : (
                              <span className="text-[color:var(--muted-foreground)]">—</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums">
                            {p.stock_balance.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}
                          </td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums">
                            {p.stock_value > 0 ? (
                              formatCurrencyBRL(p.stock_value)
                            ) : (
                              <span className="text-[color:var(--muted-foreground)]">—</span>
                            )}
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
        </>
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
              Pergunte: &quot;Quais produtos preciso recomprar?&quot;
            </p>
            <p className="text-xs text-[color:var(--muted-foreground)]">
              A IA prioriza por urgência + custo estimado.
            </p>
          </div>
        </div>
        <span className="text-sm font-medium text-[color:var(--primary)]">Conversar →</span>
      </Link>
    </div>
  );
}

function AbcTable({ rows }: { rows: AbcRow[] }) {
  return (
    <Card>
      <CardContent className="p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[color:var(--border)] text-xs text-[color:var(--muted-foreground)]">
              <th className="px-4 py-3 text-left">#</th>
              <th className="px-4 py-3 text-left">Produto</th>
              <th className="px-4 py-3 text-center">Classe</th>
              <th className="px-4 py-3 text-right">Valor</th>
              <th className="px-4 py-3 text-right">% acum</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[color:var(--border)]">
            {rows.slice(0, 50).map((r, i) => (
              <tr key={r.product_id} className="hover:bg-[color:var(--muted)]/40">
                <td className="px-4 py-2 text-xs text-[color:var(--muted-foreground)]">
                  {i + 1}
                </td>
                <td className="px-4 py-2 font-medium">{r.name}</td>
                <td className="px-4 py-2 text-center">
                  <span
                    className={cn(
                      "inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold",
                      r.class === "A" && "bg-emerald-500/20 text-emerald-700",
                      r.class === "B" && "bg-amber-500/20 text-amber-700",
                      r.class === "C" && "bg-red-500/20 text-red-700",
                    )}
                  >
                    {r.class}
                  </span>
                </td>
                <td className="px-4 py-2 text-right font-mono tabular-nums">
                  {formatCurrencyBRL(r.value)}
                </td>
                <td className="px-4 py-2 text-right text-xs font-mono">
                  {r.cumulative_pct.toFixed(1).replace(".", ",")}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function KpiTile({
  label,
  value,
  subtitle,
  tone,
}: {
  label: string;
  value: string;
  subtitle?: string;
  tone?: "emerald" | "amber" | "red";
}) {
  const toneCls =
    tone === "emerald"
      ? "text-emerald-600"
      : tone === "amber"
      ? "text-amber-600"
      : tone === "red"
      ? "text-red-600"
      : "";
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">
          {label}
        </p>
        <p className={cn("mt-1 font-mono text-xl font-semibold tabular-nums", toneCls)}>
          {value}
        </p>
        {subtitle && (
          <p className="mt-0.5 text-[10px] text-[color:var(--muted-foreground)]">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}

function EmptyCard({
  icon,
  title,
  message,
}: {
  icon: React.ReactNode;
  title: string;
  message: string;
}) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-[color:var(--muted)] text-[color:var(--muted-foreground)]">
          {icon}
        </span>
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="max-w-md text-xs text-[color:var(--muted-foreground)]">{message}</p>
      </CardContent>
    </Card>
  );
}
