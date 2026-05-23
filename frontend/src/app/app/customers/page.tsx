"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Search, Users } from "lucide-react";
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { listCustomers } from "@/lib/explorer";
import { formatCurrencyBRL, cn } from "@/lib/utils";
import { Pagination } from "@/components/dashboards/pagination";

type FilterType = "all" | "customer" | "supplier" | "active";

const TYPE_LABELS: Record<FilterType, string> = {
  all: "Todos",
  active: "Com transações",
  customer: "Clientes (com recebimentos)",
  supplier: "Fornecedores (com pagamentos)",
};

export default function CustomersPage() {
  const [q, setQ] = useState("");
  const [type, setType] = useState<FilterType>("active");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["customers", q, type, page],
    queryFn: () =>
      listCustomers({ q: q || undefined, type, page, page_size: 20 }),
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <Users className="h-6 w-6 text-blue-500" />
          Clientes & Fornecedores
          {data && (
            <span className="text-base font-medium text-[color:var(--muted-foreground)]">
              · {data.meta.total}
            </span>
          )}
        </h1>
        <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
          Pessoas (físicas e jurídicas) sincronizadas da Conta Azul. As colunas
          mostram a movimentação financeira real associada a cada uma — não apenas
          vendas formais. Vazios significam que a Conta Azul não tem aquele dado
          cadastrado.
        </p>
      </header>

      {data?.summary && (
        <section className="grid gap-3 sm:grid-cols-2">
          <Card>
            <CardContent className="p-4">
              <p className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">
                Total recebido (clientes)
              </p>
              <p className="mt-1 font-mono text-xl font-semibold text-green-600 tabular-nums">
                {formatCurrencyBRL(data.summary.total_received)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">
                Total pago (fornecedores)
              </p>
              <p className="mt-1 font-mono text-xl font-semibold text-red-600 tabular-nums">
                {formatCurrencyBRL(data.summary.total_paid)}
              </p>
            </CardContent>
          </Card>
        </section>
      )}

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

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : !data || data.results.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-[color:var(--muted-foreground)]">
            Nenhuma pessoa encontrada com este filtro.
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardContent className="p-0 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[color:var(--border)] text-xs text-[color:var(--muted-foreground)]">
                    <th className="px-4 py-3 text-left font-medium">Nome</th>
                    <th className="px-4 py-3 text-left font-medium">Tipo</th>
                    <th className="px-4 py-3 text-left font-medium">Documento</th>
                    <th className="px-4 py-3 text-right font-medium">Recebido</th>
                    <th className="px-4 py-3 text-right font-medium">Pago</th>
                    <th className="px-4 py-3 text-right font-medium">Transações</th>
                    <th className="px-4 py-3 text-right font-medium">Última transação</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--border)]">
                  {data.results.map((c) => (
                    <tr key={c.id} className="hover:bg-[color:var(--muted)]/40">
                      <td className="px-4 py-3">
                        <Link
                          href={`/app/sales?customer=${c.id}`}
                          className="font-medium hover:underline"
                        >
                          {c.name || "(sem nome)"}
                        </Link>
                        {c.email && (
                          <p className="text-xs text-[color:var(--muted-foreground)]">
                            {c.email}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        {c.type === "—" ? (
                          <span className="text-[color:var(--muted-foreground)]">—</span>
                        ) : (
                          <span className="inline-flex flex-wrap gap-1">
                            {c.type.split(" · ").map((tag) => (
                              <span
                                key={tag}
                                className={cn(
                                  "rounded-full border px-2 py-0.5 text-[10px] font-medium",
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
                      <td className="px-4 py-3 font-mono text-xs text-[color:var(--muted-foreground)]">
                        {c.document || "—"}
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
                        {c.received_count + c.paid_count > 0 ? (
                          <span>
                            {c.received_count + c.paid_count}
                            <span className="ml-1 text-[10px] text-[color:var(--muted-foreground)]">
                              ({c.received_count}R / {c.paid_count}P)
                            </span>
                          </span>
                        ) : (
                          <span className="text-[color:var(--muted-foreground)]">—</span>
                        )}
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
          <Pagination meta={data.meta} onChange={setPage} />
        </>
      )}
    </div>
  );
}
