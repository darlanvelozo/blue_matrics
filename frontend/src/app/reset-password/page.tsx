"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Logo } from "@/components/logo";
import { ApiError } from "@/lib/api";
import { confirmPasswordReset } from "@/lib/auth";

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="p-12 text-center text-sm">Carregando…</div>}>
      <ResetInner />
    </Suspense>
  );
}

function ResetInner() {
  const router = useRouter();
  const params = useSearchParams();
  const uid = params.get("uid") || "";
  const token = params.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const missingParams = !uid || !token;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("A senha precisa ter pelo menos 8 caracteres.");
      return;
    }
    if (password !== confirm) {
      setError("As senhas não conferem.");
      return;
    }
    setLoading(true);
    try {
      await confirmPasswordReset({ uid, token, new_password: password });
      setDone(true);
      setTimeout(() => router.push("/login"), 2500);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Erro inesperado. Tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[color:var(--background)] px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex justify-center">
          <Logo />
        </div>
        <Card>
          <CardContent className="p-6">
            {missingParams ? (
              <div className="space-y-3 text-center">
                <span className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-full bg-amber-500/10 text-amber-600">
                  <AlertCircle className="h-6 w-6" />
                </span>
                <h1 className="text-xl font-semibold tracking-tight">Link inválido</h1>
                <p className="text-sm text-[color:var(--muted-foreground)]">
                  O link de redefinição está incompleto. Solicite um novo abaixo.
                </p>
                <Link
                  href="/forgot-password"
                  className="block pt-2 text-sm font-medium text-[color:var(--primary)]"
                >
                  Solicitar novo link
                </Link>
              </div>
            ) : done ? (
              <div className="space-y-3 text-center">
                <span className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-full bg-green-500/10 text-green-600">
                  <CheckCircle2 className="h-6 w-6" />
                </span>
                <h1 className="text-xl font-semibold tracking-tight">Senha redefinida</h1>
                <p className="text-sm text-[color:var(--muted-foreground)]">
                  Pronto. Redirecionando para o login…
                </p>
              </div>
            ) : (
              <>
                <h1 className="text-xl font-semibold tracking-tight">Criar nova senha</h1>
                <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
                  Escolha uma senha forte com pelo menos 8 caracteres.
                </p>
                <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="password">Nova senha</Label>
                    <Input
                      id="password"
                      type="password"
                      required
                      autoFocus
                      minLength={8}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="confirm">Confirmar senha</Label>
                    <Input
                      id="confirm"
                      type="password"
                      required
                      minLength={8}
                      value={confirm}
                      onChange={(e) => setConfirm(e.target.value)}
                      placeholder="••••••••"
                    />
                  </div>
                  {error && (
                    <p className="rounded-lg border border-[color:var(--destructive)] bg-[color:var(--destructive)]/10 px-3 py-2 text-sm text-[color:var(--destructive)]">
                      {error}
                    </p>
                  )}
                  <Button type="submit" className="w-full" disabled={loading}>
                    {loading ? "Salvando..." : "Redefinir senha"}
                  </Button>
                </form>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
