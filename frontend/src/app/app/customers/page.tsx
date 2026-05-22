"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Search, Users } from "lucide-react";
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { listCustomers } from "@/lib/explorer";
import { formatCurrencyBRL } from "@/lib/utils";
import { Pagination } from "@/components/dashboards/pagination";

export default function CustomersPage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["customers", q, page],
    queryFn: () => listCustomers({ q: q || undefined, page, page_size: 20 }),
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <Users className="h-6 w-6 text-blue-500" />
          Clientes
          {data && (
            <span className="text-base font-medium text-[color:var(--muted-foreground)]">
              · {data.meta.total}
            </span>
          )}
        </h1>
        <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
          Todos os clientes da sua empresa.
        </p>
      </header>

      <div className="relative max-w-md">
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

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : !data || data.results.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-[color:var(--muted-foreground)]">
            Nenhum cliente encontrado.
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[color:var(--border)] text-xs text-[color:var(--muted-foreground)]">
                    <th className="px-6 py-3 text-left font-medium">Nome</th>
                    <th className="px-6 py-3 text-left font-medium">Documento</th>
                    <th className="px-6 py-3 text-right font-medium">Vendas</th>
                    <th className="px-6 py-3 text-right font-medium">Total comprado</th>
                    <th className="px-6 py-3 text-right font-medium">Última compra</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--border)]">
                  {data.results.map((c) => (
                    <tr key={c.id} className="hover:bg-[color:var(--muted)]/40">
                      <td className="px-6 py-3">
                        <Link
                          href={`/app/sales?customer=${c.id}`}
                          className="font-medium hover:underline"
                        >
                          {c.name}
                        </Link>
                        {c.email && (
                          <p className="text-xs text-[color:var(--muted-foreground)]">{c.email}</p>
                        )}
                      </td>
                      <td className="px-6 py-3 font-mono text-xs text-[color:var(--muted-foreground)]">
                        {c.document || "—"}
                      </td>
                      <td className="px-6 py-3 text-right">{c.sales_count}</td>
                      <td className="px-6 py-3 text-right font-mono">
                        {formatCurrencyBRL(c.total_spent)}
                      </td>
                      <td className="px-6 py-3 text-right text-xs text-[color:var(--muted-foreground)]">
                        {c.last_purchase
                          ? new Date(c.last_purchase).toLocaleDateString("pt-BR")
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
