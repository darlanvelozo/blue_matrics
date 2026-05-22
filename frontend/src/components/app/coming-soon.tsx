import Link from "next/link";
import { ArrowRight, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function ComingSoon({
  icon: Icon,
  title,
  description,
  features,
  ctaHref = "/app",
  ctaLabel = "Voltar ao início",
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  features?: string[];
  ctaHref?: string;
  ctaLabel?: string;
}) {
  return (
    <div className="mx-auto max-w-2xl space-y-6 py-6">
      <Card>
        <CardContent className="flex flex-col items-center gap-4 py-16 text-center">
          <span className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-violet-600 text-white shadow-lg">
            <Icon className="h-6 w-6" />
          </span>
          <span className="inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-xs font-medium text-blue-600 dark:text-blue-300">
            Em breve
          </span>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <p className="max-w-md text-sm text-[color:var(--muted-foreground)]">{description}</p>

          {features && features.length > 0 && (
            <ul className="mt-4 grid w-full max-w-sm gap-2 text-left text-sm">
              {features.map((f) => (
                <li
                  key={f}
                  className="flex items-start gap-2 rounded-lg border border-[color:var(--border)] bg-[color:var(--muted)]/40 px-3 py-2"
                >
                  <span className="mt-1 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          )}

          <Link href={ctaHref} className="mt-2">
            <Button variant="outline" className="inline-flex items-center gap-2">
              {ctaLabel}
              <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
