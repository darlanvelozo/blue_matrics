"use client";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Logo } from "@/components/logo";
import { ApiError } from "@/lib/api";
import { registerUser } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    full_name: "",
    company_name: "",
    email: "",
    password: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string[]>>({});

  function update<K extends keyof typeof form>(k: K, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setErrors({});
    try {
      await registerUser(form);
      router.push("/app");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        if (err.details && typeof err.details === "object") {
          setErrors(err.details as Record<string, string[]>);
        }
      } else {
        setError("Erro inesperado. Tente novamente.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Lado visual */}
      <aside className="relative hidden bg-gradient-to-br from-blue-600 to-violet-700 px-12 py-12 text-white lg:flex lg:flex-col lg:justify-between">
        <Logo href="/" className="text-white" />
        <div className="space-y-6 max-w-md">
          <h2 className="text-3xl font-bold leading-tight">
            Comece a tomar decisões com base em dados — não em achismo.
          </h2>
          <ul className="space-y-3 text-white/80">
            {[
              "Trial completo de 7 dias",
              "Sem cartão de crédito",
              "Conexão em 30 segundos",
              "Cancele quando quiser",
            ].map((t) => (
              <li key={t} className="flex items-center gap-3">
                <CheckCircle2 className="h-5 w-5 shrink-0" />
                {t}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-white/60">© BlueMetrics</p>
      </aside>

      {/* Formulário */}
      <div className="flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex justify-center lg:hidden">
            <Logo />
          </div>
          <Card>
            <CardContent className="p-6">
              <h1 className="text-xl font-semibold tracking-tight">Criar conta grátis</h1>
              <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
                7 dias de teste, sem cartão.
              </p>
              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                <Field
                  id="full_name"
                  label="Seu nome"
                  value={form.full_name}
                  onChange={(v) => update("full_name", v)}
                  errors={errors.full_name}
                />
                <Field
                  id="company_name"
                  label="Nome da empresa"
                  required
                  value={form.company_name}
                  onChange={(v) => update("company_name", v)}
                  errors={errors.company_name}
                />
                <Field
                  id="email"
                  type="email"
                  label="E-mail"
                  required
                  value={form.email}
                  onChange={(v) => update("email", v)}
                  errors={errors.email}
                />
                <Field
                  id="password"
                  type="password"
                  label="Senha"
                  required
                  value={form.password}
                  onChange={(v) => update("password", v)}
                  helper="Mínimo 8 caracteres."
                  errors={errors.password}
                />
                {error && !Object.keys(errors).length && (
                  <p className="rounded-lg border border-[color:var(--destructive)] bg-[color:var(--destructive)]/10 px-3 py-2 text-sm text-[color:var(--destructive)]">
                    {error}
                  </p>
                )}
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? "Criando..." : "Criar conta"}
                </Button>
              </form>
              <p className="mt-6 text-center text-sm text-[color:var(--muted-foreground)]">
                Já tem conta?{" "}
                <Link href="/login" className="font-medium text-[color:var(--primary)]">
                  Entrar
                </Link>
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Field({
  id,
  label,
  type = "text",
  value,
  onChange,
  required,
  errors,
  helper,
}: {
  id: string;
  label: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
  errors?: string[];
  helper?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type={type}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      {errors?.length ? (
        <p className="text-xs text-[color:var(--destructive)]">{errors.join(" ")}</p>
      ) : helper ? (
        <p className="text-xs text-[color:var(--muted-foreground)]">{helper}</p>
      ) : null}
    </div>
  );
}
