import Link from "next/link";
import { AlertOctagon, AlertTriangle, ArrowRight, Info, Sparkles } from "lucide-react";
import type { SmartCard, SmartCardSeverity } from "@/lib/dashboards";
import { cn } from "@/lib/utils";

const STYLE: Record<
  SmartCardSeverity,
  { bar: string; chip: string; ring: string; icon: typeof Info }
> = {
  info: {
    bar: "bg-blue-500",
    chip: "bg-blue-500/10 text-blue-700 border-blue-500/30 dark:text-blue-300",
    ring: "ring-blue-500/30",
    icon: Info,
  },
  success: {
    bar: "bg-emerald-500",
    chip: "bg-emerald-500/10 text-emerald-700 border-emerald-500/30 dark:text-emerald-300",
    ring: "ring-emerald-500/30",
    icon: Sparkles,
  },
  warning: {
    bar: "bg-amber-500",
    chip: "bg-amber-500/10 text-amber-700 border-amber-500/30 dark:text-amber-300",
    ring: "ring-amber-500/30",
    icon: AlertTriangle,
  },
  critical: {
    bar: "bg-red-500",
    chip: "bg-red-500/10 text-red-700 border-red-500/30 dark:text-red-300",
    ring: "ring-red-500/30",
    icon: AlertOctagon,
  },
};

export function SmartCardItem({ card }: { card: SmartCard }) {
  const s = STYLE[card.severity];
  const Icon = s.icon;

  const body = (
    <>
      <div className={cn("w-1", s.bar)} />
      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="flex items-start gap-2">
          <span
            className={cn(
              "inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md border",
              s.chip,
            )}
          >
            <Icon className="h-3.5 w-3.5" />
          </span>
          <h3 className="text-sm font-semibold leading-snug">{card.title}</h3>
        </div>
        <p className="line-clamp-3 text-xs text-[color:var(--muted-foreground)]">
          {card.message}
        </p>
        {card.action && (
          <span className="mt-auto inline-flex items-center gap-1 text-xs font-medium text-[color:var(--primary)] opacity-0 transition group-hover:opacity-100">
            Ver detalhes <ArrowRight className="h-3 w-3" />
          </span>
        )}
      </div>
    </>
  );

  const baseClass = cn(
    "group relative flex h-full overflow-hidden rounded-lg border border-[color:var(--border)] bg-[color:var(--card)] shadow-sm transition hover:shadow-md",
    card.action && "cursor-pointer",
  );

  if (card.action) {
    return (
      <Link href={card.action} className={baseClass}>
        {body}
      </Link>
    );
  }
  return <div className={baseClass}>{body}</div>;
}
