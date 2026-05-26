import type { HealthScore } from "@/lib/dashboards";
import { cn } from "@/lib/utils";

const COLOR_MAP: Record<HealthScore["color"], { stroke: string; bg: string; text: string }> = {
  green: { stroke: "#10b981", bg: "bg-emerald-500/10", text: "text-emerald-600" },
  blue: { stroke: "#1e5cff", bg: "bg-blue-500/10", text: "text-blue-600" },
  amber: { stroke: "#f59e0b", bg: "bg-amber-500/10", text: "text-amber-600" },
  red: { stroke: "#ef4444", bg: "bg-red-500/10", text: "text-red-600" },
};

export function ScoreGauge({ score }: { score: HealthScore }) {
  const c = COLOR_MAP[score.color];
  const r = 56;
  const circ = 2 * Math.PI * r;
  const dash = (score.score / 100) * circ;

  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-[color:var(--border)] bg-[color:var(--card)] p-5">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-[color:var(--muted-foreground)]">
        Score de saúde financeira
      </h3>
      <div className="relative">
        <svg width="140" height="140" viewBox="0 0 140 140">
          <circle
            cx="70" cy="70" r={r}
            stroke="currentColor"
            strokeWidth="10"
            fill="none"
            className="text-[color:var(--muted)]"
          />
          <circle
            cx="70" cy="70" r={r}
            stroke={c.stroke}
            strokeWidth="10"
            fill="none"
            strokeLinecap="round"
            strokeDasharray={`${dash} ${circ}`}
            transform="rotate(-90 70 70)"
            style={{ transition: "stroke-dasharray 0.8s ease-out" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn("text-3xl font-bold tabular-nums", c.text)}>
            {score.score}
          </span>
          <span className="text-[10px] uppercase text-[color:var(--muted-foreground)]">
            /100
          </span>
        </div>
      </div>
      <span
        className={cn(
          "rounded-full px-3 py-0.5 text-xs font-semibold",
          c.bg,
          c.text,
        )}
      >
        {score.label}
      </span>
      <div className="grid w-full grid-cols-2 gap-1.5 text-[10px] text-[color:var(--muted-foreground)]">
        <Component label="Margem" value={score.components.margin} />
        <Component label="Caixa" value={score.components.cash_balance} />
        <Component label="Inadimplência" value={score.components.inadimplencia} />
        <Component label="Fornecedor" value={score.components.supplier_concentration} />
      </div>
    </div>
  );
}

function Component({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="truncate">{label}</span>
      <div className="h-1 overflow-hidden rounded-full bg-[color:var(--muted)]">
        <div
          className={cn(
            "h-full transition-all",
            value >= 70 ? "bg-emerald-500" : value >= 40 ? "bg-amber-500" : "bg-red-500",
          )}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}
