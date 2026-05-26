"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { X } from "lucide-react";

const STORAGE_KEY = "biazul_cookie_consent";

export function CookieConsent() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      const consented = window.localStorage.getItem(STORAGE_KEY);
      if (!consented) setOpen(true);
    } catch {
      // localStorage indisponível (modo privado, etc) — silenciar
    }
  }, []);

  const dismiss = (value: "accept" | "essential") => {
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ v: value, t: Date.now() }),
      );
    } catch {
      // ignora
    }
    setOpen(false);
  };

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-label="Aviso de cookies"
      className="fixed inset-x-0 bottom-0 z-50 px-4 pb-4 sm:bottom-4 sm:left-auto sm:right-4 sm:max-w-md"
    >
      <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--background)] p-4 shadow-lg">
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-sm font-semibold">Cookies & Privacidade</h3>
          <button
            type="button"
            aria-label="Fechar"
            onClick={() => dismiss("essential")}
            className="text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-[color:var(--muted-foreground)]">
          Usamos cookies essenciais para manter você logado e proteger sua
          sessão. Não usamos rastreadores de marketing nem vendemos seus dados.
          Mais detalhes na{" "}
          <Link href="/legal/cookies" className="text-[color:var(--primary)] hover:underline">
            Política de Cookies
          </Link>{" "}
          e na{" "}
          <Link href="/legal/privacidade" className="text-[color:var(--primary)] hover:underline">
            Política de Privacidade (LGPD)
          </Link>
          .
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => dismiss("accept")}
            className="inline-flex items-center justify-center rounded-md bg-[color:var(--primary)] px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"
          >
            Entendi e aceito
          </button>
          <Link
            href="/legal/cookies"
            className="inline-flex items-center justify-center rounded-md border border-[color:var(--border)] px-3 py-1.5 text-xs font-medium hover:bg-[color:var(--muted)]"
          >
            Saber mais
          </Link>
        </div>
      </div>
    </div>
  );
}
