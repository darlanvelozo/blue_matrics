"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AlertCircle, Receipt, Search } from "lucide-react";
import { Suspense, useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Pagination } from "@/components/dashboards/pagination";
import { listSales, getFilterOptions } from "@/lib/explorer";
import { formatCurrencyBRL } from "@/lib/utils";

export default function SalesPage() {
  return (
    <Suspense fallback={<Skeleton className="h-96" />}>
      <Inner />
    </Suspense>
  );
}

function Inner() {
  const params = useSearchParams();

  // Filtros iniciais a partir do query string (drill-down vem com eles)
  const [start, setStart] = useState(params.get("start") ?? "");
  const [end, setEnd] = useState(params.get("end") ?? "");
  const [customer, setCustomer] = useState(params.get("customer") ?? "");
  const [salesperson, setSalesperson] = useState(params.get("salesperson") ?? "");
  const [statusFilter, setStatusFilter] = useState(params.get("status") ?? "");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [start, end, customer, salesperson, statusFilter, q]);

  const { data: opts } = useQuery({
    queryKey: ["filter-options"],
    queryFn: getFilterOptions,
    staleTime: 5 * 60 * 1000,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["sales", start, end, customer, salesperson, statusFilter, q, page],
    queryFn: () =>
      listSales({
        start: start || undefined,
        end: end || undefined,
        customer: customer ? Number(customer) : undefined,
        salesperson: salesperson ? Number(salesperson) : undefined,
        status: statusFilter || undefined,
        q: q || undefined,
        page,
        page_size: 25,
      }),
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <Receipt className="h-6 w-6 text-blue-500" />
          Vendas
          {data && (
            <span className="text-base font-medium text-[color:var(--muted-foreground)]">
              · {data.meta.total}
            </span>
          )}
        </h1>
        <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
          Vendas formais registradas no módulo Conta Azul. Empresas que recebem
          direto pelo financeiro (PIX/dinheiro/cartão sem ticket de venda) podem
          ter esta lista quase vazia.
          {data?.summary && (
            <>
              {" Total no filtro:"}{" "}
              <strong className="text-[color:var(--foreground)]">
                {formatCurrencyBRL(data.summary.total_value)}
              </strong>
            </>
          )}
        </p>

        {data && data.meta.total <= 1 && (
          <div className="mt-4 flex items-start gap-3 rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
            <div className="text-amber-900 dark:text-amber-200">
              <p className="font-medium">Poucas (ou nenhuma) venda formal sincronizada.</p>
              <p className="mt-0.5 text-xs">
                Isso é normal para varejo/serviços que registram entradas direto pelo
                Financeiro da Conta Azul. Para análise de faturamento, abra o{" "}
                <Link href="/app/dashboards/financeiro" className="font-medium underline">
                  dashboard Financeiro
                </Link>{" "}
                ou converse com o{" "}
                <Link href="/app/ai" className="font-medium underline">
                  Analista IA
                </Link>
                .
              </p>
            </div>
          </div>
        )}
      </header>

      <Card>
        <CardContent className="space-y-3 p-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[color:var(--muted-foreground)]" />
              <Input
                placeholder="Nº ou cliente..."
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="pl-9"
              />
            </div>
            <Input
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              aria-label="Data inicial"
            />
            <Input
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              aria-label="Data final"
            />
            <Select
              value={customer}
              onChange={(e) => setCustomer(e.target.value)}
              placeholder="Todos os clientes"
              options={(opts?.customers ?? []).map((o) => ({
                value: String(o.id),
                label: o.name,
              }))}
            />
            <Select
              value={salesperson}
              onChange={(e) => setSalesperson(e.target.value)}
              placeholder="Todos os vendedores"
              options={(opts?.salespeople ?? []).map((o) => ({
                value: String(o.id),
                label: o.name,
              }))}
            />
          </div>
          <div className="flex items-center gap-2">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              placeholder="Todos os status"
              options={[
                { value: "closed", label: "Fechadas" },
                { value: "open", label: "Abertas" },
                { value: "draft", label: "Rascunho" },
                { value: "canceled", label: "Canceladas" },
              ]}
              className="w-44"
            />
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : !data || data.results.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-[color:var(--muted-foreground)]">
            Nenhuma venda encontrada com esses filtros.
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[color:var(--border)] text-xs text-[color:var(--muted-foreground)]">
                    <th className="px-6 py-3 text-left font-medium">Data</th>
                    <th className="px-6 py-3 text-left font-medium">Nº</th>
                    <th className="px-6 py-3 text-left font-medium">Cliente</th>
                    <th className="px-6 py-3 text-left font-medium">Vendedor</th>
                    <th className="px-6 py-3 text-center font-medium">Status</th>
                    <th className="px-6 py-3 text-right font-medium">Valor</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--border)]">
                  {data.results.map((s) => (
                    <tr key={s.id} className="hover:bg-[color:var(--muted)]/40">
                      <td className="px-6 py-3 text-[color:var(--muted-foreground)]">
                        {s.issued_at && new Date(s.issued_at).toLocaleDateString("pt-BR")}
                      </td>
                      <td className="px-6 py-3 font-mono text-xs">{s.number || "—"}</td>
                      <td className="px-6 py-3 font-medium">{s.customer?.name ?? "—"}</td>
                      <td className="px-6 py-3 text-[color:var(--muted-foreground)]">
                        {s.salesperson?.name ?? "—"}
                      </td>
                      <td className="px-6 py-3 text-center">
                        <StatusBadge status={s.status} />
                      </td>
                      <td className="px-6 py-3 text-right font-mono">
                        {formatCurrencyBRL(s.total)}
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

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    closed: { label: "Fechada", cls: "bg-green-500/10 text-green-600 border-green-500/30" },
    open: { label: "Aberta", cls: "bg-blue-500/10 text-blue-600 border-blue-500/30" },
    draft: { label: "Rascunho", cls: "bg-zinc-500/10 text-zinc-500 border-zinc-500/30" },
    canceled: { label: "Cancelada", cls: "bg-red-500/10 text-red-600 border-red-500/30" },
  };
  const it = map[status] ?? map.draft;
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${it.cls}`}>
      {it.label}
    </span>
  );
}
