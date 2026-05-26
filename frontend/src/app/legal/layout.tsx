import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { Logo } from "@/components/logo";

const NAV = [
  { href: "/legal/termos", label: "Termos de Uso" },
  { href: "/legal/privacidade", label: "Política de Privacidade" },
  { href: "/legal/cancelamento", label: "Cancelamento e Reembolso" },
  { href: "/legal/cookies", label: "Política de Cookies" },
];

export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[color:var(--background)]">
      <header className="border-b border-[color:var(--border)]">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <Link href="/" aria-label="BI AZUL — voltar pra home">
            <Logo />
          </Link>
          <Link
            href="/"
            className="inline-flex items-center gap-1 text-sm text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)]"
          >
            <ChevronLeft className="h-4 w-4" /> Voltar para o site
          </Link>
        </div>
      </header>
      <div className="mx-auto grid max-w-5xl gap-8 px-4 py-10 lg:grid-cols-[220px_1fr]">
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[color:var(--muted-foreground)]">
            Documentos legais
          </h2>
          <nav className="flex flex-col gap-1 text-sm">
            {NAV.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="rounded-md px-3 py-1.5 text-[color:var(--muted-foreground)] hover:bg-[color:var(--muted)] hover:text-[color:var(--foreground)]"
              >
                {l.label}
              </Link>
            ))}
          </nav>
          <p className="mt-6 text-xs text-[color:var(--muted-foreground)]">
            Dúvidas?{" "}
            <a
              href="mailto:legal@biazul.com"
              className="text-[color:var(--primary)] hover:underline"
            >
              legal@biazul.com
            </a>
          </p>
        </aside>
        <main className="prose prose-sm max-w-none dark:prose-invert
                        prose-h1:text-2xl prose-h1:tracking-tight
                        prose-h2:mt-8 prose-h2:text-lg
                        prose-h3:mt-6 prose-h3:text-base
                        prose-p:leading-relaxed prose-li:my-0.5
                        prose-a:text-[color:var(--primary)]">
          {children}
        </main>
      </div>
    </div>
  );
}
