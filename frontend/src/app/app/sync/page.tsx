"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Clock,
  Loader2,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { listSyncLogs, runSyncNow, type SyncLogEntry, type SyncStatus } from "@/lib/sync";

const RESOURCE_LABEL: Record<string, string> = {
  all: "Sincronização completa",
  categories: "Categorias",
  salespeople: "Vendedores",
  customers: "Clientes",
  products: "Produtos",
  sales: "Vendas",
  financial_receivables: "Contas a receber",
  financial_payables: "Contas a pagar",
};

export default function SyncPage() {
  const qc = useQueryClient();

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["sync", "logs"],
    queryFn: listSyncLogs,
    refetchInterval: (q) => {
      // se há sync rodando, refetch a cada 3s
      const logs = q.state.data?.logs ?? [];
      return logs.some((l) => l.status === "running") ? 3000 : false;
    },
  });

  const runMutation = useMutation({
    mutationFn: runSyncNow,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sync", "logs"] });
    },
  });

  const logs = data?.logs ?? [];
  const masterLogs = logs.filter((l) => l.resource === "all");
  const resourceLogs = logs.filter((l) => l.resource !== "all");
  const lastMaster = masterLogs[0];
  const isRunning = logs.some((l) => l.status === "running");

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Sincronização</h1>
          <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
            Acompanhe e dispare a sincronização dos seus dados com a Conta Azul.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`mr-2 h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
            Atualizar
          </Button>
          <Button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending || isRunning}
          >
            {runMutation.isPending || isRunning ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : null}
            {isRunning ? "Sincronizando…" : "Sincronizar agora"}
          </Button>
        </div>
      </header>

      {runMutation.error instanceof ApiError && (
        <Banner kind="error">
          <AlertCircle className="h-4 w-4" />
          {runMutation.error.message}
        </Banner>
      )}

      {error instanceof ApiError && (
        <Banner kind="error">
          <AlertCircle className="h-4 w-4" />
          Não consegui carregar o histórico: {error.message}
        </Banner>
      )}

      {/* Última sincronização */}
      <Card>
        <CardHeader>
          <CardTitle>Última sincronização</CardTitle>
          <CardDescription>Resumo do último run completo.</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="grid grid-cols-3 gap-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-16" />
              ))}
            </div>
          ) : !lastMaster ? (
            <p className="text-sm text-[color:var(--muted-foreground)]">
              Você ainda não sincronizou. Clique em <strong>Sincronizar agora</strong> para começar.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Metric label="Status" value={<StatusBadge status={lastMaster.status} />} />
              <Metric label="Registros importados" value={`${lastMaster.upserted}`} />
              <Metric
                label="Início"
                value={new Date(lastMaster.started_at).toLocaleString("pt-BR")}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Histórico por recurso */}
      <Card>
        <CardHeader>
          <CardTitle>Histórico por recurso</CardTitle>
          <CardDescription>Últimas execuções (50 mais recentes).</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-2 p-6">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : resourceLogs.length === 0 ? (
            <p className="px-6 pb-6 text-sm text-[color:var(--muted-foreground)]">
              Nenhuma execução por recurso ainda.
            </p>
          ) : (
            <ul className="divide-y divide-[color:var(--border)]">
              {resourceLogs.map((log) => (
                <LogRow key={log.id} log={log} />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function LogRow({ log }: { log: SyncLogEntry }) {
  const label = RESOURCE_LABEL[log.resource] ?? log.resource;
  return (
    <li className="flex items-center justify-between gap-4 px-6 py-3 text-sm hover:bg-[color:var(--muted)]/40">
      <div className="flex items-center gap-3">
        <StatusIcon status={log.status} />
        <div>
          <p className="font-medium">{label}</p>
          <p className="text-xs text-[color:var(--muted-foreground)]">
            {new Date(log.started_at).toLocaleString("pt-BR")}
            {log.finished_at && (
              <>
                {" "}·{" "}
                {Math.max(
                  0,
                  Math.round(
                    (new Date(log.finished_at).getTime() - new Date(log.started_at).getTime()) / 1000,
                  ),
                )}
                s
              </>
            )}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-6 text-xs text-[color:var(--muted-foreground)]">
        <span>
          <strong className="text-[color:var(--foreground)]">{log.upserted}</strong> importados
        </span>
        {log.errors > 0 && (
          <span className="text-amber-600">
            <strong>{log.errors}</strong> erro{log.errors > 1 ? "s" : ""}
          </span>
        )}
        <StatusBadge status={log.status} />
        <ChevronRight className="h-3.5 w-3.5 opacity-40" />
      </div>
    </li>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-[color:var(--border)] p-3">
      <p className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">{label}</p>
      <div className="mt-1 text-base font-medium">{value}</div>
    </div>
  );
}

function StatusIcon({ status }: { status: SyncStatus }) {
  if (status === "success")
    return <CheckCircle2 className="h-4 w-4 text-green-500" />;
  if (status === "running")
    return <Clock className="h-4 w-4 animate-pulse text-blue-500" />;
  if (status === "partial")
    return <AlertCircle className="h-4 w-4 text-amber-500" />;
  return <XCircle className="h-4 w-4 text-red-500" />;
}

function StatusBadge({ status }: { status: SyncStatus }) {
  const map: Record<SyncStatus, { label: string; cls: string }> = {
    success: { label: "Sucesso", cls: "bg-green-500/10 text-green-600 border-green-500/30" },
    running: { label: "Em execução", cls: "bg-blue-500/10 text-blue-600 border-blue-500/30" },
    partial: { label: "Parcial", cls: "bg-amber-500/10 text-amber-600 border-amber-500/30" },
    failed: { label: "Falhou", cls: "bg-red-500/10 text-red-600 border-red-500/30" },
  };
  const it = map[status];
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${it.cls}`}
    >
      {it.label}
    </span>
  );
}

function Banner({ kind, children }: { kind: "success" | "error"; children: React.ReactNode }) {
  const cls =
    kind === "success"
      ? "border-green-500/30 bg-green-500/10 text-green-700 dark:text-green-300"
      : "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300";
  return (
    <div className={`flex items-center gap-2 rounded-lg border px-4 py-3 text-sm ${cls}`}>
      {children}
    </div>
  );
}
