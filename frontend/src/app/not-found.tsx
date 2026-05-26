import Link from "next/link";
import { Compass, HelpCircle, Home } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/logo";

export const metadata = {
  title: "Página não encontrada — BI AZUL",
};

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col bg-[color:var(--background)]">
      <header className="border-b border-[color:var(--border)]">
        <div className="mx-auto flex max-w-5xl items-center px-4 py-4">
          <Link href="/" aria-label="Voltar para a home">
            <Logo />
          </Link>
        </div>
      </header>
      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="max-w-md text-center">
          <span className="inline-flex h-14 w-14 items-center justify-center rounded-full bg-blue-500/10 text-blue-500">
            <Compass className="h-7 w-7" />
          </span>
          <h1 className="mt-6 text-3xl font-bold tracking-tight">
            Não achamos essa página
          </h1>
          <p className="mt-2 text-sm text-[color:var(--muted-foreground)]">
            O link pode ter sido atualizado, expirado ou digitado incorretamente.
            Tente um dos atalhos abaixo.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link href="/">
              <Button>
                <Home className="mr-2 h-4 w-4" />
                Página inicial
              </Button>
            </Link>
            <Link href="/help">
              <Button variant="outline">
                <HelpCircle className="mr-2 h-4 w-4" />
                Central de ajuda
              </Button>
            </Link>
          </div>
          <p className="mt-10 text-xs text-[color:var(--muted-foreground)]">
            Acha que isso é um erro?{" "}
            <a href="mailto:suporte@biazul.com" className="text-[color:var(--primary)] hover:underline">
              suporte@biazul.com
            </a>
          </p>
        </div>
      </main>
    </div>
  );
}
