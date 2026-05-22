"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ExternalLink, Loader2, X } from "lucide-react";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { listSales } from "@/lib/explorer";
import { formatCurrencyBRL } from "@/lib/utils";

const MONTHS_PT = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

function monthRange(ym: string): { start: string; end: string; label: string } {
  const [y, m] = ym.split("-").map(Number);
  const start = new Date(Date.UTC(y, m - 1, 1));
  const end = new Date(Date.UTC(y, m, 0));
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return {
    start: iso(start),
    end: iso(end),
    label: `${MONTHS_PT[m - 1]} de ${y}`,
  };
}

/**
 * Modal de drill-down — dispara quando usuário clica numa barra/ponto de chart.
 * Mostra lista das primeiras 20 vendas + link para "ver todas" no /app/sales.
 */
export function DrillDownModal({
  month, // "YYYY-MM"
  filters = {},
  onClose,
}: {
  month: string | null;
  filters?: {
    salesperson?: number | null;
    customer?: number | null;
    product?: number | null;
  };
  onClose: () => void;
}) {
  // Hooks SEMPRE no topo, antes de qualquer return condicional
  useEffect(() => {
    if (!month) return;
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = original;
    };
  }, [month]);

  const range = month ? monthRange(month) : null;
  const { data, isLoading } = useQuery({
    enabled: !!month,
    queryKey: ["drilldown-sales", month, filters],
    queryFn: () =>
      listSales({
        start: range!.start,
        end: range!.end,
        salesperson: filters.salesperson ?? undefined,
        customer: filters.customer ?? undefined,
        product: filters.product ?? undefined,
        status: "closed",
        page_size: 20,
      }),
  });

  if (!month || !range) return null;

  const linkHref = `/app/sales?start=${range.start}&end=${range.end}` +
    (filters.salesperson ? `&salesperson=${filters.salesperson}` : "") +
    (filters.customer ? `&customer=${filters.customer}` : "");

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl rounded-t-2xl border border-[color:var(--border)] bg-[color:var(--card)] p-5 shadow-2xl sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">
              Drill-down
            </p>
            <h2 className="capitalize text-lg font-bold tracking-tight">{range.label}</h2>
            {data && (
              <p className="mt-1 text-xs text-[color:var(--muted-foreground)]">
                {data.meta.total} venda{data.meta.total !== 1 ? "s" : ""} ·{" "}
                <span className="font-semibold text-[color:var(--foreground)]">
                  {formatCurrencyBRL(data.summary.total_value)}
                </span>
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1.5 text-[color:var(--muted-foreground)] hover:bg-[color:var(--accent)]"
            aria-label="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="max-h-[60vh] overflow-y-auto">
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12" />
              ))}
            </div>
          ) : !data || data.results.length === 0 ? (
            <p className="py-8 text-center text-sm text-[color:var(--muted-foreground)]">
              Nenhuma venda neste período.
            </p>
          ) : (
            <ul className="divide-y divide-[color:var(--border)]">
              {data.results.map((s) => (
                <li key={s.id} className="flex items-center justify-between gap-3 py-3 text-sm">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">
                      {s.customer?.name ?? "—"}
                      {s.number && (
                        <span className="ml-2 font-mono text-xs text-[color:var(--muted-foreground)]">
                          #{s.number}
                        </span>
                      )}
                    </p>
                    <p className="text-xs text-[color:var(--muted-foreground)]">
                      {s.issued_at && new Date(s.issued_at).toLocaleDateString("pt-BR")}
                      {s.salesperson && ` · ${s.salesperson.name}`}
                    </p>
                  </div>
                  <span className="font-mono font-semibold">{formatCurrencyBRL(s.total)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {data && data.meta.total > 20 && (
          <div className="mt-4 border-t border-[color:var(--border)] pt-3">
            <Link href={linkHref}>
              <Button variant="outline" size="sm" className="w-full">
                Ver todas as {data.meta.total} vendas
                <ExternalLink className="ml-2 h-3 w-3" />
              </Button>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

interface ClickableChartProps {
  onMonthClick: (ym: string) => void;
}

/** Wrapper que adiciona handler onClick a um chart Recharts pelo `dataKey="month"`. */
export function useChartClickToDrill(onMonthClick: (ym: string) => void): {
  onClick: (e: unknown) => void;
} {
  return {
    onClick: (e: unknown) => {
      // Recharts passa { activeLabel: "2026-04", ... }
      const ev = e as { activeLabel?: string } | undefined;
      if (ev?.activeLabel) onMonthClick(ev.activeLabel);
    },
  };
}

export type { ClickableChartProps };
