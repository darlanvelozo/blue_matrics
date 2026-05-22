import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn, formatCurrencyBRL, formatPercent } from "@/lib/utils";
import { Sparkline } from "./charts";

type ValueFormat = "currency" | "number" | "percent";

export function KpiCard({
  label,
  value,
  changePct,
  format = "currency",
  positiveIsGood = true,
  sparkline,
  sparkColor,
}: {
  label: string;
  value: number;
  changePct?: number | null;
  format?: ValueFormat;
  /** Para inadimplência, "subir" é ruim. */
  positiveIsGood?: boolean;
  /** Série temporal mensal (12 pontos). Quando passada, mostra sparkline. */
  sparkline?: Array<{ value: number }>;
  sparkColor?: string;
}) {
  const formatted =
    format === "currency"
      ? formatCurrencyBRL(value)
      : format === "percent"
      ? `${value.toFixed(1)}%`
      : new Intl.NumberFormat("pt-BR").format(Math.round(value));

  const showChange = changePct !== null && changePct !== undefined && Number.isFinite(changePct);
  const isUp = showChange && changePct! > 0;
  const isDown = showChange && changePct! < 0;
  const isGood = (isUp && positiveIsGood) || (isDown && !positiveIsGood);

  // cor do sparkline acompanha sentido (bom/ruim) quando possível
  const sparkFinal =
    sparkColor ??
    (showChange
      ? isGood
        ? "#16a34a" // green
        : "#dc2626" // red
      : "#3b82f6"); // blue neutral

  return (
    <Card>
      <CardContent className="p-5">
        <p className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">
          {label}
        </p>
        <p className="mt-2 text-2xl font-bold tracking-tight">{formatted}</p>
        <div className="mt-1 flex items-center gap-1 text-xs">
          {showChange ? (
            <>
              <span
                className={cn(
                  "inline-flex items-center gap-0.5 font-medium",
                  isGood
                    ? "text-green-600 dark:text-green-400"
                    : isUp || isDown
                    ? "text-red-600 dark:text-red-400"
                    : "text-[color:var(--muted-foreground)]",
                )}
              >
                {isUp ? (
                  <ArrowUp className="h-3 w-3" />
                ) : isDown ? (
                  <ArrowDown className="h-3 w-3" />
                ) : (
                  <Minus className="h-3 w-3" />
                )}
                {formatPercent(Math.abs(changePct!) / 100)}
              </span>
              <span className="text-[color:var(--muted-foreground)]">vs período anterior</span>
            </>
          ) : (
            <span className="text-[color:var(--muted-foreground)]">sem comparação</span>
          )}
        </div>
        {sparkline && sparkline.length > 1 && (
          <div className="mt-3 -mx-1">
            <Sparkline data={sparkline} color={sparkFinal} height={32} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
