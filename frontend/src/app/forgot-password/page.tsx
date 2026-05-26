"use client";
import Link from "next/link";
import { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Logo } from "@/components/logo";
import { ApiError } from "@/lib/api";
import { requestPasswordReset } from "@/lib/auth";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await requestPasswordReset(email);
      setSubmitted(true);
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
            {submitted ? (
              <div className="space-y-4 text-center">
                <span className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-full bg-green-500/10 text-green-600">
                  <CheckCircle2 className="h-6 w-6" />
                </span>
                <h1 className="text-xl font-semibold tracking-tight">Verifique seu e-mail</h1>
                <p className="text-sm text-[color:var(--muted-foreground)]">
                  Se houver uma conta com <strong>{email}</strong>, enviamos um link para
                  redefinir sua senha. O link expira em 60 minutos.
                </p>
                <p className="text-xs text-[color:var(--muted-foreground)]">
                  Não chegou? Confira o spam ou{" "}
                  <button
                    onClick={() => setSubmitted(false)}
                    className="font-medium text-[color:var(--primary)] hover:underline"
                  >
                    tente outro e-mail
                  </button>
                  .
                </p>
                <Link
                  href="/login"
                  className="block pt-2 text-sm font-medium text-[color:var(--primary)]"
                >
                  Voltar para o login
                </Link>
              </div>
            ) : (
              <>
                <h1 className="text-xl font-semibold tracking-tight">Esqueci minha senha</h1>
                <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
                  Digite seu e-mail e enviaremos um link de redefinição.
                </p>
                <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="email">E-mail</Label>
                    <Input
                      id="email"
                      type="email"
                      required
                      autoFocus
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="voce@empresa.com.br"
                    />
                  </div>
                  {error && (
                    <p className="rounded-lg border border-[color:var(--destructive)] bg-[color:var(--destructive)]/10 px-3 py-2 text-sm text-[color:var(--destructive)]">
                      {error}
                    </p>
                  )}
                  <Button type="submit" className="w-full" disabled={loading}>
                    {loading ? "Enviando..." : "Enviar link de redefinição"}
                  </Button>
                </form>
                <p className="mt-6 text-center text-sm text-[color:var(--muted-foreground)]">
                  Lembrou da senha?{" "}
                  <Link href="/login" className="font-medium text-[color:var(--primary)]">
                    Voltar ao login
                  </Link>
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
