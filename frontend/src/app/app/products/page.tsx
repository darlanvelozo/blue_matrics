"use client";
import { useQuery } from "@tanstack/react-query";
import { Package, Search } from "lucide-react";
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Pagination } from "@/components/dashboards/pagination";
import { listProducts } from "@/lib/explorer";
import { formatCurrencyBRL } from "@/lib/utils";

export default function ProductsPage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["products", q, page],
    queryFn: () => listProducts({ q: q || undefined, page, page_size: 20 }),
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <Package className="h-6 w-6 text-blue-500" />
          Produtos
          {data && (
            <span className="text-base font-medium text-[color:var(--muted-foreground)]">
              · {data.meta.total}
            </span>
          )}
        </h1>
        <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
          Catálogo de produtos sincronizado da Conta Azul.
        </p>
      </header>

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

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-14" />
          ))}
        </div>
      ) : !data || data.results.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-[color:var(--muted-foreground)]">
            Nenhum produto encontrado.
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
                    <th className="px-6 py-3 text-left font-medium">SKU</th>
                    <th className="px-6 py-3 text-right font-medium">Preço</th>
                    <th className="px-6 py-3 text-right font-medium">Custo</th>
                    <th className="px-6 py-3 text-right font-medium">Margem</th>
                    <th className="px-6 py-3 text-center font-medium">Ativo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--border)]">
                  {data.results.map((p) => (
                    <tr key={p.id} className="hover:bg-[color:var(--muted)]/40">
                      <td className="px-6 py-3 font-medium">{p.name}</td>
                      <td className="px-6 py-3 font-mono text-xs text-[color:var(--muted-foreground)]">
                        {p.sku || "—"}
                      </td>
                      <td className="px-6 py-3 text-right font-mono">
                        {formatCurrencyBRL(p.price)}
                      </td>
                      <td className="px-6 py-3 text-right font-mono text-[color:var(--muted-foreground)]">
                        {formatCurrencyBRL(p.cost)}
                      </td>
                      <td className="px-6 py-3 text-right">
                        <span
                          className={
                            p.margin_pct > 50
                              ? "font-mono text-green-600 dark:text-green-400"
                              : p.margin_pct > 20
                              ? "font-mono text-amber-600 dark:text-amber-400"
                              : "font-mono text-red-600 dark:text-red-400"
                          }
                        >
                          {p.margin_pct.toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-6 py-3 text-center">
                        {p.is_active ? "✓" : "—"}
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
