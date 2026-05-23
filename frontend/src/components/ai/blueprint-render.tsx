import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalysisBlueprint } from "@/lib/ai";
import { formatCurrencyBRL } from "@/lib/utils";
import { CashflowChart } from "@/components/dashboards/charts";

/** Render genérico de blueprint de análise gerado pela IA. */
export function BlueprintRender({ blueprint }: { blueprint: AnalysisBlueprint }) {
  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h2 className="text-xl font-bold tracking-tight">{blueprint.title}</h2>
        <p className="text-sm text-[color:var(--muted-foreground)]">{blueprint.summary}</p>
      </div>

      {blueprint.kpis.length > 0 && (
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {blueprint.kpis.map((k, i) => (
            <Card key={i}>
              <CardContent className="space-y-1 p-4">
                <p className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">
                  {k.label}
                </p>
                <p className="font-mono text-lg font-semibold tabular-nums">
                  {formatKpi(k.value, k.format, k.suffix)}
                </p>
              </CardContent>
            </Card>
          ))}
        </section>
      )}

      {blueprint.tables.map((t, i) => (
        <Card key={`t-${i}`}>
          <CardHeader>
            <CardTitle>{t.title}</CardTitle>
          </CardHeader>
          <CardContent className="px-0 pt-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-[color:var(--border)] text-xs uppercase text-[color:var(--muted-foreground)]">
                  <tr>
                    {t.headers.map((h, j) => (
                      <th
                        key={j}
                        className={`px-4 py-2.5 ${
                          (t.value_columns ?? []).includes(j) ? "text-right" : "text-left"
                        }`}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--border)]">
                  {t.rows.map((row, ri) => (
                    <tr key={ri}>
                      {row.map((cell, ci) => {
                        const isValue = (t.value_columns ?? []).includes(ci);
                        return (
                          <td
                            key={ci}
                            className={`px-4 py-2 ${
                              isValue ? "text-right font-mono tabular-nums" : ""
                            }`}
                          >
                            {isValue && typeof cell === "number"
                              ? formatCurrencyBRL(cell)
                              : String(cell)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ))}

      {blueprint.charts.map((c, i) => (
        <Card key={`c-${i}`}>
          <CardHeader>
            <CardTitle>{c.title}</CardTitle>
          </CardHeader>
          <CardContent>
            {c.type === "bar" && <SimpleBar data={c.data as Array<{ label: string; value: number }>} />}
            {c.type === "cashflow" && (
              <CashflowChart
                data={c.data as Array<{ month: string; in: number; out: number; net: number }>}
              />
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function formatKpi(value: number, format?: string, suffix?: string): string {
  if (format === "currency") return formatCurrencyBRL(value);
  if (format === "percent") return `${value.toFixed(1).replace(".", ",")}%`;
  return `${new Intl.NumberFormat("pt-BR").format(Math.round(value))}${suffix ?? ""}`;
}

/** Barra horizontal simples — não puxa Recharts pra coisa pequena. */
function SimpleBar({ data }: { data: Array<{ label: string; value: number }> }) {
  const max = Math.max(1, ...data.map((d) => d.value || 0));
  return (
    <ul className="space-y-2">
      {data.map((d, i) => (
        <li key={i} className="space-y-1">
          <div className="flex items-baseline justify-between gap-2 text-sm">
            <span className="truncate">{d.label}</span>
            <span className="font-mono text-xs tabular-nums">
              {formatCurrencyBRL(d.value || 0)}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-[color:var(--muted)]">
            <div
              className="h-full bg-blue-500"
              style={{ width: `${((d.value || 0) / max) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
