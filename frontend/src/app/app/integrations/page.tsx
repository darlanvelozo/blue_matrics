"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Copy,
  ExternalLink,
  Eye,
  EyeOff,
  FlaskConical,
  Key,
  KeyRound,
  Loader2,
  Plug,
  PlugZap,
  Trash2,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import {
  deleteContaAzulCredentials,
  disconnectContaAzul,
  exchangeContaAzulCode,
  getContaAzulStatus,
  injectContaAzulToken,
  saveContaAzulCredentials,
  startContaAzulAuthorize,
  type ContaAzulStatus,
} from "@/lib/integrations";

const DEV_REDIRECT_URI = "https://contaazul.com";
const DEV_AUTH_URL = "https://auth.contaazul.com/login";

export default function IntegrationsPage() {
  return (
    <Suspense
      fallback={
        <div className="text-sm text-[color:var(--muted-foreground)]">Carregando…</div>
      }
    >
      <IntegrationsPageInner />
    </Suspense>
  );
}

function IntegrationsPageInner() {
  const qc = useQueryClient();
  const params = useSearchParams();
  const callbackStatus = params.get("status");
  const callbackReason = params.get("reason");
  const [bannerDismissed, setBannerDismissed] = useState(false);

  const { data, isLoading, error } = useQuery<ContaAzulStatus>({
    queryKey: ["contaazul", "status"],
    queryFn: getContaAzulStatus,
    refetchOnWindowFocus: true,
  });

  const connectMutation = useMutation({
    mutationFn: startContaAzulAuthorize,
    onSuccess: ({ url }) => {
      window.open(url, "_blank", "noopener,noreferrer");
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: disconnectContaAzul,
    onSuccess: (fresh) => {
      qc.setQueryData(["contaazul", "status"], fresh);
    },
  });

  useEffect(() => {
    if (data?.status === "connected" && callbackStatus === "connected") {
      const t = setTimeout(() => setBannerDismissed(true), 5000);
      return () => clearTimeout(t);
    }
  }, [data?.status, callbackStatus]);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Integrações</h1>
        <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
          Conecte seu ERP para começarmos a sincronizar.
        </p>
      </header>

      {!bannerDismissed && callbackStatus === "connected" && (
        <Banner kind="success">
          <CheckCircle2 className="h-4 w-4" />
          Conectado com sucesso! Vamos começar a sincronizar seus dados.
        </Banner>
      )}
      {!bannerDismissed && callbackStatus === "error" && (
        <Banner kind="error">
          <AlertCircle className="h-4 w-4" />
          Falha na conexão: <code className="text-xs">{callbackReason ?? "desconhecido"}</code>
        </Banner>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
                <PlugZap className="h-5 w-5" />
              </span>
              <div>
                <CardTitle>Conta Azul</CardTitle>
                <CardDescription>
                  ERP de gestão financeira e comercial — fonte de dados principal.
                </CardDescription>
              </div>
            </div>
            <StatusBadge status={data?.status ?? "disconnected"} />
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-[color:var(--muted-foreground)]">
              <Loader2 className="h-4 w-4 animate-spin" />
              Carregando status…
            </div>
          )}

          {error instanceof ApiError && (
            <Banner kind="error">
              <AlertCircle className="h-4 w-4" />
              Não consegui carregar o status: {error.message}
            </Banner>
          )}

          {data && (
            <>
              <CredentialsCard data={data} />

              <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
                <Field label="Conectado em" value={fmt(data.connected_at)} />
                <Field label="Última sincronização" value={fmt(data.last_synced_at)} />
                <Field label="Token expira em" value={fmt(data.expires_at)} />
                <Field label="Escopo" value={data.scope || "—"} />
                {data.last_error && (
                  <div className="sm:col-span-2">
                    <Field label="Último erro" value={data.last_error} mono />
                  </div>
                )}
              </dl>

              {connectMutation.error instanceof ApiError && (
                <Banner kind="error">
                  <AlertCircle className="h-4 w-4" />
                  {connectMutation.error.message}
                </Banner>
              )}

              <div className="flex flex-wrap gap-2 pt-2">
                {data.status !== "connected" ? (
                  <Button
                    onClick={() => connectMutation.mutate()}
                    disabled={connectMutation.isPending || !data.has_credentials}
                    className="inline-flex items-center gap-2"
                    title={!data.has_credentials ? "Configure as credenciais primeiro" : undefined}
                  >
                    {connectMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Plug className="h-4 w-4" />
                    )}
                    {data.dev_mode ? "Abrir URL de autorização" : "Conectar Conta Azul"}
                    <ExternalLink className="h-3.5 w-3.5 opacity-70" />
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    onClick={() => disconnectMutation.mutate()}
                    disabled={disconnectMutation.isPending}
                  >
                    {disconnectMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : null}
                    Desconectar
                  </Button>
                )}
              </div>

              {/* Em modo dev, mostra os 2 fluxos alternativos */}
              {data.has_credentials && data.dev_mode && (
                <div className="space-y-4 border-t border-[color:var(--border)] pt-6">
                  <div className="flex items-center gap-2 text-sm font-semibold">
                    <FlaskConical className="h-4 w-4 text-amber-500" />
                    Modo desenvolvimento — caminhos alternativos
                  </div>
                  <p className="text-xs text-[color:var(--muted-foreground)]">
                    Como o app dev da Conta Azul tem redirect_uri fixo (
                    <code className="rounded bg-[color:var(--muted)] px-1">{DEV_REDIRECT_URI}</code>
                    ), o callback automático não chega aqui. Use um destes dois caminhos:
                  </p>
                  <ExchangeCodeCard />
                  <ManualTokenCard />
                </div>
              )}

              <p className="border-t border-[color:var(--border)] pt-4 text-xs text-[color:var(--muted-foreground)]">
                Ao conectar, você é redirecionado para a Conta Azul para autorizar o acesso.
                Não armazenamos sua senha. Tokens e credenciais ficam criptografados em repouso.
              </p>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ============================================================
// Credentials sub-card (com toggle "modo dev")
// ============================================================
function CredentialsCard({ data }: { data: ContaAzulStatus }) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [clientId, setClientId] = useState(data.client_id);
  const [clientSecret, setClientSecret] = useState("");
  const [devMode, setDevMode] = useState<boolean>(!!data.dev_mode);
  const [showSecret, setShowSecret] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!editing) {
      setClientId(data.client_id);
      setDevMode(!!data.dev_mode);
    }
  }, [data.client_id, data.dev_mode, editing]);

  const saveMutation = useMutation({
    mutationFn: saveContaAzulCredentials,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contaazul", "status"] });
      setEditing(false);
      setClientSecret("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteContaAzulCredentials,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contaazul", "status"] });
      setClientId("");
      setClientSecret("");
    },
  });

  async function copyRedirect() {
    try {
      await navigator.clipboard.writeText(data.redirect_uri);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!clientId || !clientSecret) return;
    saveMutation.mutate({
      client_id: clientId.trim(),
      client_secret: clientSecret,
      redirect_uri_override: devMode ? DEV_REDIRECT_URI : "",
      auth_url_override: devMode ? DEV_AUTH_URL : "",
    });
  }

  // Modo colapsado (já tem creds e não está editando)
  if (data.has_credentials && !editing) {
    return (
      <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--muted)]/40 p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-green-500/10 text-green-600">
              <Key className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold">
                Credenciais configuradas
                {data.dev_mode && (
                  <span className="ml-2 inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-300">
                    <FlaskConical className="h-2.5 w-2.5" />
                    DEV
                  </span>
                )}
              </p>
              <p className="font-mono text-xs text-[color:var(--muted-foreground)]">
                Client ID: {data.client_id}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => setEditing(true)}>
              Alterar
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              aria-label="Remover credenciais"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-xl border border-blue-500/30 bg-blue-500/5 p-5">
      <div className="flex items-center gap-3">
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
          <Key className="h-4 w-4" />
        </span>
        <div>
          <p className="text-sm font-semibold">
            {data.has_credentials ? "Alterar credenciais OAuth" : "Configurar credenciais OAuth"}
          </p>
          <p className="text-xs text-[color:var(--muted-foreground)]">
            Crie um app em{" "}
            <a
              href="https://portaldevs.contaazul.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-[color:var(--primary)] underline"
            >
              portaldevs.contaazul.com
            </a>{" "}
            e cole abaixo Client ID e Client Secret.
          </p>
        </div>
      </div>

      {/* Toggle modo dev */}
      <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-[color:var(--border)] bg-[color:var(--background)] p-3">
        <input
          type="checkbox"
          checked={devMode}
          onChange={(e) => setDevMode(e.target.checked)}
          className="mt-0.5 h-4 w-4 cursor-pointer"
        />
        <div className="flex-1 text-sm">
          <span className="font-medium">App em modo desenvolvimento</span>
          <p className="mt-0.5 text-xs text-[color:var(--muted-foreground)]">
            Marque se você criou o app em <strong>portaldevs.contaazul.com</strong> (o redirect_uri
            é fixo em <code className="text-[11px]">https://contaazul.com</code>). Em produção,
            desmarque.
          </p>
        </div>
      </label>

      {!devMode && (
        <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--background)] p-3">
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-[color:var(--muted-foreground)]">
            Redirect URI (cadastre exatamente este valor no portal)
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 truncate rounded bg-[color:var(--muted)] px-2 py-1 font-mono text-xs">
              {data.redirect_uri}
            </code>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={copyRedirect}
              className="shrink-0"
            >
              <Copy className="mr-1.5 h-3 w-3" />
              {copied ? "Copiado!" : "Copiar"}
            </Button>
          </div>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor="client_id">Client ID</Label>
          <Input
            id="client_id"
            required
            placeholder="ex: 3sqstulr053aqoupif48h8jbja"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="client_secret">Client Secret</Label>
          <div className="relative">
            <Input
              id="client_secret"
              required
              type={showSecret ? "text" : "password"}
              placeholder={data.has_credentials ? "Cole o novo secret (não exibimos o atual)" : "Cole o secret"}
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              autoComplete="off"
              spellCheck={false}
              className="pr-10"
            />
            <button
              type="button"
              onClick={() => setShowSecret((v) => !v)}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-[color:var(--muted-foreground)] hover:bg-[color:var(--muted)]"
              aria-label={showSecret ? "Ocultar" : "Mostrar"}
            >
              {showSecret ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            </button>
          </div>
          <p className="text-xs text-[color:var(--muted-foreground)]">
            O secret é criptografado em repouso e nunca é exibido depois de salvo.
          </p>
        </div>

        {saveMutation.error instanceof ApiError && (
          <Banner kind="error">
            <AlertCircle className="h-4 w-4" />
            {saveMutation.error.message}
          </Banner>
        )}

        <div className="flex gap-2 pt-1">
          <Button
            type="submit"
            disabled={saveMutation.isPending || !clientId || !clientSecret}
          >
            {saveMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Salvar credenciais
          </Button>
          {editing && (
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setEditing(false);
                setClientSecret("");
              }}
            >
              Cancelar
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}

// ============================================================
// Modo dev — Card 1: paste do code
// ============================================================
function ExchangeCodeCard() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(true);
  const [code, setCode] = useState("");

  const mutation = useMutation({
    mutationFn: exchangeContaAzulCode,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contaazul", "status"] });
      setCode("");
    },
  });

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const value = code.trim();
    if (!value) return;
    // Aceita URL completa ou só o code
    let finalCode = value;
    try {
      const url = new URL(value);
      const c = url.searchParams.get("code");
      if (c) finalCode = c;
    } catch {
      // não era URL, usa como está
    }
    mutation.mutate(finalCode);
  }

  return (
    <details className="group rounded-xl border border-[color:var(--border)] bg-[color:var(--card)]" open={open} onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}>
      <summary className="flex cursor-pointer items-center justify-between gap-3 p-4">
        <span className="flex items-center gap-3 text-sm font-medium">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
            <KeyRound className="h-4 w-4" />
          </span>
          Caminho A: colar o <code className="rounded bg-[color:var(--muted)] px-1 text-xs">code</code> após autorização
        </span>
        {open ? <ChevronDown className="h-4 w-4 opacity-50" /> : <ChevronRight className="h-4 w-4 opacity-50" />}
      </summary>
      <div className="space-y-3 p-4 pt-0 text-sm">
        <ol className="ml-5 list-decimal space-y-1 text-[color:var(--muted-foreground)]">
          <li>Clique em <strong>Abrir URL de autorização</strong> acima.</li>
          <li>Faça login na Conta Azul e clique em autorizar.</li>
          <li>Você será redirecionado para <code className="text-xs">https://contaazul.com/?code=XXX&amp;state=YYY</code>.</li>
          <li>Copie tudo da barra de endereço (ou apenas o valor de <code>code</code>) e cole abaixo.</li>
        </ol>
        <form onSubmit={onSubmit} className="space-y-2">
          <Label htmlFor="code">Code (válido por 3 minutos)</Label>
          <Input
            id="code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Cole o code OU a URL completa"
            autoComplete="off"
            spellCheck={false}
          />
          {mutation.error instanceof ApiError && (
            <Banner kind="error">
              <AlertCircle className="h-4 w-4" />
              {mutation.error.message}
            </Banner>
          )}
          {mutation.isSuccess && (
            <Banner kind="success">
              <CheckCircle2 className="h-4 w-4" />
              Tokens recebidos e armazenados. Conexão ativa.
            </Banner>
          )}
          <Button type="submit" disabled={mutation.isPending || !code.trim()}>
            {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Trocar code por tokens
          </Button>
        </form>
      </div>
    </details>
  );
}

// ============================================================
// Modo dev — Card 2: paste do access_token direto
// ============================================================
function ManualTokenCard() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [accessToken, setAccessToken] = useState("");
  const [refreshToken, setRefreshToken] = useState("");
  const [expiresIn, setExpiresIn] = useState(3600);

  const mutation = useMutation({
    mutationFn: injectContaAzulToken,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contaazul", "status"] });
      setAccessToken("");
      setRefreshToken("");
    },
  });

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!accessToken.trim()) return;
    mutation.mutate({
      access_token: accessToken.trim(),
      refresh_token: refreshToken.trim() || undefined,
      expires_in: Number(expiresIn) || 3600,
    });
  }

  return (
    <details className="group rounded-xl border border-[color:var(--border)] bg-[color:var(--card)]" open={open} onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}>
      <summary className="flex cursor-pointer items-center justify-between gap-3 p-4">
        <span className="flex items-center gap-3 text-sm font-medium">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600">
            <Zap className="h-4 w-4" />
          </span>
          Caminho B: colar <code className="rounded bg-[color:var(--muted)] px-1 text-xs">access_token</code> direto (mais rápido)
        </span>
        {open ? <ChevronDown className="h-4 w-4 opacity-50" /> : <ChevronRight className="h-4 w-4 opacity-50" />}
      </summary>
      <div className="space-y-3 p-4 pt-0 text-sm">
        <p className="text-[color:var(--muted-foreground)]">
          O portal de devs entrega um <code>access_token</code> de teste já válido (vale ~1h).
          Cole abaixo para sincronizar agora — sem refresh_token, você terá que renovar depois.
        </p>
        <form onSubmit={onSubmit} className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="access_token">Access Token</Label>
            <textarea
              id="access_token"
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              className="w-full rounded-lg border border-[color:var(--border)] bg-[color:var(--background)] p-2 font-mono text-xs"
              rows={3}
              placeholder="eyJraWQiOi..."
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="refresh_token">Refresh Token (opcional)</Label>
              <Input
                id="refresh_token"
                value={refreshToken}
                onChange={(e) => setRefreshToken(e.target.value)}
                placeholder="se você tiver"
                autoComplete="off"
                spellCheck={false}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="expires_in">Expira em (segundos)</Label>
              <Input
                id="expires_in"
                type="number"
                value={expiresIn}
                onChange={(e) => setExpiresIn(Number(e.target.value))}
                min={60}
                max={86400}
              />
            </div>
          </div>
          {mutation.error instanceof ApiError && (
            <Banner kind="error">
              <AlertCircle className="h-4 w-4" />
              {mutation.error.message}
            </Banner>
          )}
          {mutation.isSuccess && (
            <Banner kind="success">
              <CheckCircle2 className="h-4 w-4" />
              Token armazenado. Conexão ativa — pode sincronizar.
            </Banner>
          )}
          <Button type="submit" disabled={mutation.isPending || !accessToken.trim()}>
            {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Salvar e conectar
          </Button>
        </form>
      </div>
    </details>
  );
}

// ============================================================
// Componentes auxiliares
// ============================================================
function StatusBadge({ status }: { status: ContaAzulStatus["status"] }) {
  const map = {
    connected: { label: "Conectado", cls: "bg-green-500/10 text-green-600 border-green-500/30" },
    disconnected: {
      label: "Desconectado",
      cls: "bg-[color:var(--muted)] text-[color:var(--muted-foreground)] border-[color:var(--border)]",
    },
    error: { label: "Erro", cls: "bg-red-500/10 text-red-600 border-red-500/30" },
    revoked: { label: "Revogado", cls: "bg-amber-500/10 text-amber-600 border-amber-500/30" },
  } as const;
  const it = map[status];
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${it.cls}`}
    >
      {it.label}
    </span>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <>
      <dt className="text-[color:var(--muted-foreground)]">{label}</dt>
      <dd className={mono ? "font-mono text-xs" : ""}>{value}</dd>
    </>
  );
}

function fmt(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
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
    <div className={`flex items-center gap-2 rounded-lg border px-4 py-3 text-sm ${cls}`}>
      {children}
    </div>
  );
}
