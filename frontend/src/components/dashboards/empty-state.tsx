import Link from "next/link";
import { Database } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function EmptyDashboardState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
        <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/10 text-blue-500">
          <Database className="h-5 w-5" />
        </span>
        <h2 className="text-lg font-semibold">Ainda não temos dados pra mostrar</h2>
        <p className="max-w-sm text-sm text-[color:var(--muted-foreground)]">
          Conecte sua Conta Azul e dispare a primeira sincronização — os dashboards começam a
          mostrar números em segundos.
        </p>
        <div className="mt-2 flex gap-2">
          <Link href="/app/integrations">
            <Button>Conectar Conta Azul</Button>
          </Link>
          <Link href="/app/sync">
            <Button variant="outline">Ir para sincronização</Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
