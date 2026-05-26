import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrencyBRL } from "@/lib/utils";

export interface RankingRow {
  /** Identificador da linha (usado como key). */
  id: number | string;
  /** Nome principal exibido à esquerda. */
  name: string;
  /** Valor monetário principal (somatório). */
  total: number;
  /** Contagem secundária (nº de transações / vendas). Opcional. */
  count?: number;
  /** Sufixo descritivo para `count` (ex: "transações", "vendas"). */
  countLabel?: string;
}

export function RankingList({
  title,
  description,
  rows,
  emptyMessage = "Sem dados no período.",
}: {
  title: string;
  description?: string;
  rows: RankingRow[];
  emptyMessage?: string;
}) {
  const total = rows.reduce((acc, r) => acc + (r.total || 0), 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && (
          <p className="text-xs text-[color:var(--muted-foreground)]">{description}</p>
        )}
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <p className="py-4 text-center text-sm text-[color:var(--muted-foreground)]">
            {emptyMessage}
          </p>
        ) : (
          <ul className="space-y-3">
            {rows.map((r, idx) => {
              const pct = total > 0 ? (r.total / total) * 100 : 0;
              return (
                <li key={r.id} className="space-y-1.5">
                  <div className="flex items-baseline justify-between gap-2 text-sm">
                    <span className="flex items-center gap-2 truncate">
                      <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[color:var(--muted)] text-[10px] font-semibold">
                        {idx + 1}
                      </span>
                      <span className="truncate font-medium">{r.name || "—"}</span>
                    </span>
                    <span className="shrink-0 whitespace-nowrap font-mono text-xs tabular-nums">
                      {formatCurrencyBRL(r.total)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[color:var(--muted)]">
                      <div
                        className="h-full bg-blue-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    {typeof r.count === "number" && (
                      <span className="shrink-0 text-[10px] text-[color:var(--muted-foreground)]">
                        {r.count} {r.countLabel ?? ""}
                      </span>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
