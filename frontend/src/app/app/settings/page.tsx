"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  AtSign,
  CheckCircle2,
  Download,
  FileText,
  KeyRound,
  Loader2,
  Settings as SettingsIcon,
  ShieldAlert,
  Trash2,
  User as UserIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  changeEmail,
  changePassword,
  getMe,
  logout,
  updateProfile,
  type User,
} from "@/lib/auth";
import { deleteMyAccount, exportMyData, listAuditLogs } from "@/lib/security";

export default function SettingsPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const me = useQuery({ queryKey: ["me"], queryFn: getMe });
  const audit = useQuery({ queryKey: ["audit-logs"], queryFn: listAuditLogs });

  const exportMutation = useMutation({
    mutationFn: exportMyData,
    onSuccess: (data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `biazul-export-${new Date().toISOString().slice(0, 10)}.json`;
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
          Perfil, senha, privacidade e dados pessoais (LGPD).
        </p>
      </header>

      {me.isLoading ? <Skeleton className="h-40" /> : me.data ? (
        <ProfileCard user={me.data} onUpdated={() => qc.invalidateQueries({ queryKey: ["me"] })} />
      ) : null}

      <PasswordCard />

      {me.data && (
        <EmailCard
          currentEmail={me.data.email}
          onUpdated={() => qc.invalidateQueries({ queryKey: ["me"] })}
        />
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Download className="h-4 w-4" />
            Exportar meus dados (LGPD Art. 18)
          </CardTitle>
          <CardDescription>
            Baixa um JSON com tudo que armazenamos sobre você e suas empresas.
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
          >
            {exportMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
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
            {audit.data?.entries.length
              ? `Últimas ${Math.min(audit.data.entries.length, 30)} ações registradas na sua conta.`
              : "Ações sensíveis (login, troca de senha, sincronização) aparecem aqui."}
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
                  <div className="min-w-0">
                    <p className="truncate font-medium">{prettyAction(e.action)}</p>
                    <p className="truncate text-xs text-[color:var(--muted-foreground)]">
                      {e.actor_email}{e.ip && ` · ${e.ip}`}
                    </p>
                  </div>
                  <span className="shrink-0 text-xs text-[color:var(--muted-foreground)]">
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
            Excluir sua conta é permanente e remove todos os seus dados (LGPD Art. 18).
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

// ============================================================
function ProfileCard({ user, onUpdated }: { user: User; onUpdated: () => void }) {
  const [fullName, setFullName] = useState(user.full_name);
  const dirty = fullName !== user.full_name;

  useEffect(() => {
    setFullName(user.full_name);
  }, [user.full_name]);

  const mut = useMutation({
    mutationFn: () => updateProfile({ full_name: fullName }),
    onSuccess: onUpdated,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <UserIcon className="h-4 w-4" />
          Perfil
        </CardTitle>
        <CardDescription>
          Como você aparece dentro do BI AZUL.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="profile-name">Nome completo</Label>
          <Input
            id="profile-name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Seu nome"
            maxLength={200}
          />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs text-[color:var(--muted-foreground)]">
            E-mail
          </Label>
          <p className="text-sm">
            {user.email}{" "}
            <span className="text-xs text-[color:var(--muted-foreground)]">
              (alterar abaixo)
            </span>
          </p>
        </div>
        {mut.error instanceof ApiError && (
          <Banner kind="error">{mut.error.message}</Banner>
        )}
        {mut.isSuccess && !dirty && (
          <Banner kind="success">Perfil atualizado.</Banner>
        )}
        <Button onClick={() => mut.mutate()} disabled={!dirty || mut.isPending}>
          {mut.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Salvar alterações
        </Button>
      </CardContent>
    </Card>
  );
}

// ============================================================
function PasswordCard() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [clientErr, setClientErr] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: () =>
      changePassword({ current_password: current, new_password: next }),
    onSuccess: () => {
      setCurrent("");
      setNext("");
      setConfirm("");
    },
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setClientErr(null);
    if (next.length < 8) {
      setClientErr("A nova senha precisa ter pelo menos 8 caracteres.");
      return;
    }
    if (next !== confirm) {
      setClientErr("A confirmação não confere com a nova senha.");
      return;
    }
    mut.mutate();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <KeyRound className="h-4 w-4" />
          Trocar senha
        </CardTitle>
        <CardDescription>
          Mínimo 8 caracteres. Você precisará informar a senha atual.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="pwd-current">Senha atual</Label>
            <Input
              id="pwd-current"
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="pwd-new">Nova senha</Label>
            <Input
              id="pwd-new"
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              autoComplete="new-password"
              required
              minLength={8}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="pwd-confirm">Confirmar nova senha</Label>
            <Input
              id="pwd-confirm"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
              required
              minLength={8}
            />
          </div>
          {clientErr && <Banner kind="error">{clientErr}</Banner>}
          {mut.error instanceof ApiError && <Banner kind="error">{mut.error.message}</Banner>}
          {mut.isSuccess && <Banner kind="success">Senha alterada com sucesso.</Banner>}
          <Button type="submit" disabled={mut.isPending || !current || !next || !confirm}>
            {mut.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Atualizar senha
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

// ============================================================
function EmailCard({
  currentEmail,
  onUpdated,
}: {
  currentEmail: string;
  onUpdated: () => void;
}) {
  const [newEmail, setNewEmail] = useState("");
  const [password, setPassword] = useState("");

  const mut = useMutation({
    mutationFn: () =>
      changeEmail({ new_email: newEmail, current_password: password }),
    onSuccess: () => {
      setNewEmail("");
      setPassword("");
      onUpdated();
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <AtSign className="h-4 w-4" />
          Alterar e-mail
        </CardTitle>
        <CardDescription>
          E-mail atual: <strong>{currentEmail}</strong>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            mut.mutate();
          }}
          className="space-y-3"
        >
          <div className="space-y-1.5">
            <Label htmlFor="email-new">Novo e-mail</Label>
            <Input
              id="email-new"
              type="email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              placeholder="voce@empresa.com.br"
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="email-pwd">Senha atual</Label>
            <Input
              id="email-pwd"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          {mut.error instanceof ApiError && (
            <Banner kind="error">{mut.error.message}</Banner>
          )}
          {mut.isSuccess && (
            <Banner kind="success">
              E-mail atualizado. Use o novo no próximo login.
            </Banner>
          )}
          <Button type="submit" disabled={mut.isPending || !newEmail || !password}>
            {mut.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Atualizar e-mail
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

// ============================================================
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
    <div className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${cls}`}>
      {kind === "success" ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
      {children}
    </div>
  );
}

const ACTION_LABELS: Record<string, string> = {
  login: "Login",
  logout: "Logout",
  register: "Cadastro",
  password_change: "Troca de senha",
  password_reset_request: "Solicitação de redefinição de senha",
  password_reset_confirm: "Senha redefinida via e-mail",
  contaazul_connect: "Conta Azul conectada",
  contaazul_disconnect: "Conta Azul desconectada",
  credentials_updated: "Credenciais atualizadas",
  sync_triggered: "Sincronização disparada",
  subscription_checkout: "Checkout iniciado",
  subscription_canceled: "Assinatura cancelada",
  subscription_reactivated: "Assinatura reativada",
  data_export: "Exportação de dados",
  data_delete: "Exclusão de dados",
  admin_access: "Acesso admin",
};
function prettyAction(code: string): string {
  return ACTION_LABELS[code] ?? code;
}
