"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Brain,
  Plug,
  RefreshCw,
  ShoppingCart,
  Wallet,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { KpiCard } from "@/components/dashboards/kpi-card";
import { getExecutive } from "@/lib/dashboards";
import { getContaAzulStatus } from "@/lib/integrations";
import { listInsights } from "@/lib/insights";
import { listSyncLogs } from "@/lib/sync";

const SEVERITY_CLS = {
  info: "bg-blue-500/10 text-blue-600 border-blue-500/30",
  success: "bg-green-500/10 text-green-600 border-green-500/30",
  warning: "bg-amber-500/10 text-amber-600 border-amber-500/30",
  critical: "bg-red-500/10 text-red-600 border-red-500/30",
} as const;

export default function AppHome() {
  const exec = useQuery({
    queryKey: ["dashboards", "executive", "last_12m"],
    queryFn: () => getExecutive({ preset: "last_12m" }),
  });
  const ca = useQuery({ queryKey: ["contaazul", "status"], queryFn: getContaAzulStatus });
  const insights = useQuery({ queryKey: ["insights"], queryFn: listInsights });
  const sync = useQuery({ queryKey: ["sync", "logs"], queryFn: listSyncLogs });

  const hasData = !!exec.data?.has_data;
  const lastSyncMaster = sync.data?.logs.find((l) => l.resource === "all");
  const recentInsights = insights.data?.insights.slice(0, 3) ?? [];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Visão geral</h1>
        <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
          Tudo que importa em um só lugar.
        </p>
      </header>

      {/* Empty state: nada conectado */}
      {!hasData && !exec.isLoading && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
                <Plug className="h-5 w-5" />
              </span>
              <div>
                <CardTitle>Conecte sua Conta Azul</CardTitle>
                <CardDescription>30 segundos. Sem digitar nenhuma senha.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="mb-4 text-sm text-[color:var(--muted-foreground)]">
              Quando você conectar, vamos sincronizar seus últimos 12 meses automaticamente.
            </p>
            <Link href="/app/integrations">
              <Button className="inline-flex items-center gap-2">
                Conectar agora <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* KPIs principais */}
      {hasData && (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {exec.isLoading
            ? Array.from({ length: 4 }).map((_, i) => (
                <Card key={i}>
                  <CardContent className="space-y-2 p-5">
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="h-7 w-32" />
                    <Skeleton className="h-3 w-24" />
                  </CardContent>
                </Card>
              ))
            : exec.data && (
                <>
                  <KpiCard
                    label="Faturamento (12m)"
                    value={exec.data.revenue.current}
                    changePct={exec.data.revenue.change_pct}
                  />
                  <KpiCard
                    label="Lucro líquido (12m)"
                    value={exec.data.net_profit.current}
                    changePct={exec.data.net_profit.change_pct}
                  />
                  <KpiCard
                    label="Ticket médio"
                    value={exec.data.avg_ticket.current}
                    changePct={exec.data.avg_ticket.change_pct}
                  />
                  <KpiCard
                    label="Inadimplência"
                    value={exec.data.overdue_rate}
                    format="percent"
                    positiveIsGood={false}
                  />
                </>
              )}
        </section>
      )}

      {/* Insights + status */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Insights recentes */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-blue-500" />
                <CardTitle className="text-base">Insights recentes</CardTitle>
              </div>
              <Link
                href="/app/insights"
                className="text-xs font-medium text-[color:var(--primary)] hover:underline"
              >
                Ver todos
              </Link>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {insights.isLoading ? (
              <div className="space-y-3 px-6 pb-6">
                <Skeleton className="h-14" />
                <Skeleton className="h-14" />
              </div>
            ) : recentInsights.length === 0 ? (
              <p className="px-6 pb-6 text-sm text-[color:var(--muted-foreground)]">
                Nenhum insight ainda. Vá em <Link href="/app/insights" className="underline">Insights</Link> e clique em "Gerar insights agora".
              </p>
            ) : (
              <ul className="divide-y divide-[color:var(--border)]">
                {recentInsights.map((i) => (
                  <li key={i.id} className="flex items-start gap-3 px-6 py-3">
                    <span
                      className={`inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${SEVERITY_CLS[i.severity]}`}
                    >
                      {i.severity}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{i.title}</p>
                      <p className="line-clamp-2 text-xs text-[color:var(--muted-foreground)]">
                        {i.narrative}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Status integrações + sync */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Conta Azul</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div>
              <p className="text-[color:var(--muted-foreground)]">Conexão</p>
              <p className="mt-1 flex items-center gap-2 font-medium">
                <span
                  className={`inline-block h-2 w-2 rounded-full ${
                    ca.data?.status === "connected" ? "bg-green-500" : "bg-zinc-400"
                  }`}
                />
                {ca.data?.status ?? "—"}
                {ca.data?.dev_mode && (
                  <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700 dark:text-amber-300">
                    DEV
                  </span>
                )}
              </p>
            </div>
            <div>
              <p className="text-[color:var(--muted-foreground)]">Última sincronização</p>
              <p className="mt-1 font-medium">
                {lastSyncMaster
                  ? new Date(lastSyncMaster.started_at).toLocaleString("pt-BR", {
                      day: "2-digit",
                      month: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : "—"}
                {lastSyncMaster && (
                  <span
                    className={`ml-2 rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                      lastSyncMaster.status === "success"
                        ? "border-green-500/30 bg-green-500/10 text-green-600"
                        : lastSyncMaster.status === "partial"
                        ? "border-amber-500/30 bg-amber-500/10 text-amber-600"
                        : "border-red-500/30 bg-red-500/10 text-red-600"
                    }`}
                  >
                    {lastSyncMaster.status}
                  </span>
                )}
              </p>
            </div>
            <div className="flex gap-2 pt-2">
              <Link href="/app/integrations" className="flex-1">
                <Button variant="outline" size="sm" className="w-full">
                  <Plug className="mr-1.5 h-3 w-3" />
                  Integrações
                </Button>
              </Link>
              <Link href="/app/sync" className="flex-1">
                <Button variant="outline" size="sm" className="w-full">
                  <RefreshCw className="mr-1.5 h-3 w-3" />
                  Sincronizar
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Atalhos para os dashboards */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[color:var(--muted-foreground)]">
          Dashboards
        </h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <ShortcutCard
            href="/app/dashboards/executivo"
            icon={BarChart3}
            title="Executivo"
            description="Faturamento, lucro, top clientes e produtos."
          />
          <ShortcutCard
            href="/app/dashboards/financeiro"
            icon={Wallet}
            title="Financeiro"
            description="Fluxo de caixa, contas a pagar e receber, inadimplência."
          />
          <ShortcutCard
            href="/app/dashboards/comercial"
            icon={ShoppingCart}
            title="Comercial"
            description="Vendas, ticket médio, ranking de vendedores."
          />
        </div>
      </section>
    </div>
  );
}

function ShortcutCard({
  href,
  icon: Icon,
  title,
  description,
}: {
  href: string;
  icon: typeof BarChart3;
  title: string;
  description: string;
}) {
  return (
    <Link href={href}>
      <Card className="h-full transition-shadow hover:shadow-md">
        <CardContent className="p-5">
          <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
            <Icon className="h-4 w-4" />
          </div>
          <h3 className="mb-1 font-semibold">{title}</h3>
          <p className="text-xs text-[color:var(--muted-foreground)]">{description}</p>
          <span className="mt-3 inline-flex items-center text-xs font-medium text-[color:var(--primary)]">
            Abrir <ArrowRight className="ml-1 h-3 w-3" />
          </span>
        </CardContent>
      </Card>
    </Link>
  );
}
