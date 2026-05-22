"use client";
import { useQuery } from "@tanstack/react-query";
import { Filter, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { getFilterOptions } from "@/lib/explorer";
import { cn } from "@/lib/utils";

export type Comparison = "prev_period" | "yoy";

export interface DashboardFilters {
  /** custom range (sobrescreve preset) */
  start?: string;
  end?: string;
  comparison?: Comparison;
  salesperson?: number | null;
  customer?: number | null;
  product?: number | null;
  category?: number | null;
}

export function FiltersPanel({
  filters,
  onChange,
  /** Quais dimensões mostrar (algumas páginas usam só algumas). */
  showSalesperson = true,
  showCustomer = true,
  showProduct = true,
  showCategory = false,
}: {
  filters: DashboardFilters;
  onChange: (next: DashboardFilters) => void;
  showSalesperson?: boolean;
  showCustomer?: boolean;
  showProduct?: boolean;
  showCategory?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const { data: opts } = useQuery({
    queryKey: ["filter-options"],
    queryFn: getFilterOptions,
    staleTime: 5 * 60 * 1000,
  });

  const activeCount =
    (filters.salesperson ? 1 : 0) +
    (filters.customer ? 1 : 0) +
    (filters.product ? 1 : 0) +
    (filters.category ? 1 : 0) +
    (filters.start && filters.end ? 1 : 0);

  function update<K extends keyof DashboardFilters>(key: K, value: DashboardFilters[K]) {
    onChange({ ...filters, [key]: value });
  }

  function clear() {
    onChange({});
  }

  return (
    <div className="relative">
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => setOpen((v) => !v)}
        className={cn("relative", activeCount > 0 && "border-blue-500/40")}
      >
        <Filter className="mr-1.5 h-3.5 w-3.5" />
        Filtros
        {activeCount > 0 && (
          <span className="ml-1.5 inline-flex h-4 w-4 items-center justify-center rounded-full bg-blue-500 text-[10px] font-semibold text-white">
            {activeCount}
          </span>
        )}
      </Button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-30"
            onClick={() => setOpen(false)}
            aria-label="Fechar"
          />
          <div className="absolute right-0 top-full z-40 mt-2 w-[min(420px,90vw)] rounded-xl border border-[color:var(--border)] bg-[color:var(--card)] p-4 shadow-xl">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold">Filtros avançados</h3>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded p-1 text-[color:var(--muted-foreground)] hover:bg-[color:var(--accent)]"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>

            <div className="space-y-3">
              {/* Custom date range */}
              <div>
                <p className="mb-1.5 text-xs font-medium text-[color:var(--muted-foreground)]">
                  Intervalo personalizado
                </p>
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    type="date"
                    value={filters.start ?? ""}
                    onChange={(e) => update("start", e.target.value || undefined)}
                    aria-label="Data inicial"
                  />
                  <Input
                    type="date"
                    value={filters.end ?? ""}
                    onChange={(e) => update("end", e.target.value || undefined)}
                    aria-label="Data final"
                  />
                </div>
                {filters.start && filters.end && (
                  <p className="mt-1 text-[11px] text-amber-600 dark:text-amber-400">
                    Intervalo personalizado sobrescreve o filtro de período rápido.
                  </p>
                )}
              </div>

              {/* Comparison mode */}
              <div>
                <p className="mb-1.5 text-xs font-medium text-[color:var(--muted-foreground)]">
                  Comparar com
                </p>
                <Select
                  value={filters.comparison ?? "prev_period"}
                  onChange={(e) => update("comparison", e.target.value as Comparison)}
                  options={[
                    { value: "prev_period", label: "Período anterior" },
                    { value: "yoy", label: "Mesmo período do ano passado" },
                  ]}
                />
              </div>

              {showSalesperson && (
                <DropdownFilter
                  label="Vendedor"
                  value={filters.salesperson ?? null}
                  options={opts?.salespeople ?? []}
                  onChange={(v) => update("salesperson", v)}
                />
              )}
              {showCustomer && (
                <DropdownFilter
                  label="Cliente"
                  value={filters.customer ?? null}
                  options={opts?.customers ?? []}
                  onChange={(v) => update("customer", v)}
                />
              )}
              {showProduct && (
                <DropdownFilter
                  label="Produto"
                  value={filters.product ?? null}
                  options={opts?.products ?? []}
                  onChange={(v) => update("product", v)}
                />
              )}
              {showCategory && (
                <DropdownFilter
                  label="Categoria"
                  value={filters.category ?? null}
                  options={opts?.categories ?? []}
                  onChange={(v) => update("category", v)}
                />
              )}
            </div>

            {activeCount > 0 && (
              <div className="mt-4 flex justify-end border-t border-[color:var(--border)] pt-3">
                <Button type="button" variant="ghost" size="sm" onClick={clear}>
                  Limpar tudo
                </Button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function DropdownFilter({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: number | null;
  options: Array<{ id: number; name: string }>;
  onChange: (v: number | null) => void;
}) {
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium text-[color:var(--muted-foreground)]">
        {label}
      </p>
      <Select
        value={value ? String(value) : ""}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
        placeholder="Todos"
        options={options.map((o) => ({ value: String(o.id), label: o.name }))}
      />
    </div>
  );
}
