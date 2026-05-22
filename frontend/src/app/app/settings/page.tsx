"use client";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileText,
  Loader2,
  Settings as SettingsIcon,
  ShieldAlert,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { logout } from "@/lib/auth";
import { deleteMyAccount, exportMyData, listAuditLogs } from "@/lib/security";

export default function SettingsPage() {
  const router = useRouter();

  const audit = useQuery({ queryKey: ["audit-logs"], queryFn: listAuditLogs });

  const exportMutation = useMutation({
    mutationFn: exportMyData,
    onSuccess: (data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `bluemetrics-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteMyAccount,
    onSuccess: () => {
      logout();
      router.push("/login");
    },
  });

  const [confirmText, setConfirmText] = useState("");
  const [showDelete, setShowDelete] = useState(false);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <SettingsIcon className="h-6 w-6 text-blue-500" />
          Configurações
        </h1>
        <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
          Privacidade, dados pessoais e conformidade com LGPD.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Download className="h-4 w-4" />
            Exportar meus dados
          </CardTitle>
          <CardDescription>
            Baixa um JSON com tudo que armazenamos sobre você e suas empresas (LGPD Art. 18).
          </CardDescription>
        </CardHeader>
        <CardContent>
          {exportMutation.error instanceof ApiError && (
            <Banner kind="error">{exportMutation.error.message}</Banner>
          )}
          <Button
            onClick={() => exportMutation.mutate()}
            disabled={exportMutation.isPending}
            variant="outline"
            className="inline-flex items-center gap-2"
          >
            {exportMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Baixar JSON
          </Button>
          {exportMutation.isSuccess && (
            <p className="mt-3 text-xs text-green-600 dark:text-green-400">
              ✓ Download iniciado.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="h-4 w-4" />
            Logs de auditoria
          </CardTitle>
          <CardDescription>
            Últimas {audit.data?.entries.length ?? 0} ações registradas na sua conta.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {audit.isLoading ? (
            <div className="space-y-2 px-6 pb-6">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : !audit.data || audit.data.entries.length === 0 ? (
            <p className="px-6 pb-6 text-sm text-[color:var(--muted-foreground)]">
              Nenhuma ação registrada ainda.
            </p>
          ) : (
            <ul className="divide-y divide-[color:var(--border)]">
              {audit.data.entries.slice(0, 30).map((e) => (
                <li key={e.id} className="flex items-center justify-between px-6 py-3 text-sm">
                  <div>
                    <p className="font-medium">{e.action}</p>
                    <p className="text-xs text-[color:var(--muted-foreground)]">
                      {e.actor_email}{e.ip && ` · ${e.ip}`}
                    </p>
                  </div>
                  <span className="text-xs text-[color:var(--muted-foreground)]">
                    {new Date(e.created_at).toLocaleString("pt-BR", {
                      day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
                    })}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* Zona de perigo */}
      <Card className="border-red-500/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base text-red-600">
            <ShieldAlert className="h-4 w-4" />
            Zona de perigo
          </CardTitle>
          <CardDescription>
            Excluir sua conta é permanente e remove todos os seus dados.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {!showDelete ? (
            <Button
              variant="outline"
              className="border-red-500/30 text-red-600 hover:bg-red-500/10"
              onClick={() => setShowDelete(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Excluir minha conta
            </Button>
          ) : (
            <div className="space-y-3 rounded-lg border border-red-500/30 bg-red-500/5 p-4">
              <p className="text-sm">
                Para confirmar, digite{" "}
                <code className="rounded bg-[color:var(--muted)] px-1.5 py-0.5 font-mono">
                  DELETAR
                </code>{" "}
                no campo abaixo. Essa ação <strong>não pode ser desfeita</strong>.
              </p>
              <div className="space-y-1.5">
                <Label htmlFor="confirm-delete" className="text-xs">
                  Digite DELETAR para confirmar
                </Label>
                <Input
                  id="confirm-delete"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  placeholder="DELETAR"
                  autoComplete="off"
                />
              </div>
              {deleteMutation.error instanceof ApiError && (
                <Banner kind="error">{deleteMutation.error.message}</Banner>
              )}
              <div className="flex gap-2">
                <Button
                  variant="destructive"
                  onClick={() => deleteMutation.mutate(confirmText)}
                  disabled={confirmText !== "DELETAR" || deleteMutation.isPending}
                >
                  {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Confirmar exclusão
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setShowDelete(false);
                    setConfirmText("");
                  }}
                >
                  Cancelar
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Banner({
  kind,
  children,
}: {
  kind: "success" | "error";
  children: React.ReactNode;
}) {
  const cls =
    kind === "success"
      ? "border-green-500/30 bg-green-500/10 text-green-700 dark:text-green-300"
      : "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300";
  return (
    <div className={`mb-3 flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${cls}`}>
      {kind === "success" ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
      {children}
    </div>
  );
}
