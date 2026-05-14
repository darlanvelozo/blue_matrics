import Link from "next/link";
import { ArrowRight, Plug } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function AppHome() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Bem-vindo ao BlueMetrics</h1>
        <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
          Vamos conectar sua Conta Azul para começar a ver os dados.
        </p>
      </header>

      {/* Empty state — conectar Conta Azul */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
              <Plug className="h-5 w-5" />
            </span>
            <div>
              <CardTitle>Conecte sua Conta Azul</CardTitle>
              <CardDescription>30 segundos, sem digitar nenhuma senha.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-[color:var(--muted-foreground)]">
            Quando você conectar, vamos sincronizar seus últimos 12 meses automaticamente
            e gerar os primeiros dashboards.
          </p>
          <Button>
            <Link href="/app/integrations" className="inline-flex items-center gap-2">
              Conectar agora <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>

      {/* Preview dos cards de KPI (skeleton) */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[color:var(--muted-foreground)]">
          Pré-visualização
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="space-y-2 p-6">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-7 w-32" />
                <Skeleton className="h-3 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
