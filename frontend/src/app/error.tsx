"use client";

import Link from "next/link";
import { useEffect } from "react";
import { AlertTriangle, Home, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";

// Global error boundary do App Router. Pega exceptions não tratadas em
// qualquer Server/Client Component da árvore. Precisa ser "use client".

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Em prod com Sentry configurado, isso vira capture automaticamente.
    // Aqui só logamos no console em dev.
    if (process.env.NODE_ENV !== "production") {
      // eslint-disable-next-line no-console
      console.error("[GlobalError]", error);
    }
  }, [error]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4 py-12">
      <div className="max-w-md text-center">
        <span className="inline-flex h-14 w-14 items-center justify-center rounded-full bg-red-500/10 text-red-500">
          <AlertTriangle className="h-7 w-7" />
        </span>
        <h1 className="mt-6 text-3xl font-bold tracking-tight">
          Algo deu errado por aqui
        </h1>
        <p className="mt-2 text-sm text-[color:var(--muted-foreground)]">
          Já registramos o ocorrido. Tente novamente — se persistir, fale com a gente.
        </p>
        {error.digest && (
          <p className="mt-3 inline-block rounded bg-[color:var(--muted)] px-2 py-1 text-[10px] font-mono text-[color:var(--muted-foreground)]">
            ref: {error.digest}
          </p>
        )}
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Button onClick={reset}>
            <RotateCw className="mr-2 h-4 w-4" />
            Tentar de novo
          </Button>
          <Link href="/">
            <Button variant="outline">
              <Home className="mr-2 h-4 w-4" />
              Voltar para home
            </Button>
          </Link>
        </div>
        <p className="mt-10 text-xs text-[color:var(--muted-foreground)]">
          Precisa de ajuda?{" "}
          <a href="mailto:suporte@biazul.com" className="text-[color:var(--primary)] hover:underline">
            suporte@biazul.com
          </a>
        </p>
      </div>
    </div>
  );
}
