"use client";
import { cn } from "@/lib/utils";
import type { Preset } from "@/lib/dashboards";

const OPTIONS: { value: Preset; label: string }[] = [
  { value: "this_month", label: "Este mês" },
  { value: "last_month", label: "Mês passado" },
  { value: "last_30d", label: "30 dias" },
  { value: "last_90d", label: "90 dias" },
  { value: "ytd", label: "Ano atual" },
  { value: "last_12m", label: "12 meses" },
];

export function PeriodFilter({
  value,
  onChange,
}: {
  value: Preset;
  onChange: (preset: Preset) => void;
}) {
  return (
    <div className="inline-flex flex-wrap gap-1 rounded-lg border border-[color:var(--border)] bg-[color:var(--card)] p-1">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={cn(
            "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
            value === opt.value
              ? "bg-[color:var(--primary)] text-[color:var(--primary-foreground)]"
              : "text-[color:var(--muted-foreground)] hover:bg-[color:var(--accent)] hover:text-[color:var(--accent-foreground)]",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
