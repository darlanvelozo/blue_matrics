"use client";
/**
 * Hook que sincroniza o preset de período com `?period=` na URL.
 *
 * Vantagens:
 * - Persiste entre navegação (executivo → financeiro → comercial)
 * - URL é compartilhável ("manda esse link de Q1/2026 pro contador")
 * - localStorage fallback para 1ª visita
 */
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { Preset } from "./dashboards";

const VALID: Preset[] = [
  "this_month",
  "last_month",
  "last_30d",
  "last_90d",
  "ytd",
  "last_12m",
];

const STORAGE_KEY = "bm.period";
const DEFAULT: Preset = "last_12m";

function isValid(v: string | null): v is Preset {
  return v !== null && (VALID as string[]).includes(v);
}

export function usePeriod() {
  const router = useRouter();
  const params = useSearchParams();
  const fromUrl = params.get("period");
  const [preset, setPresetState] = useState<Preset>(() => {
    if (isValid(fromUrl)) return fromUrl;
    if (typeof window !== "undefined") {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (isValid(stored)) return stored;
    }
    return DEFAULT;
  });

  // se URL mudar (deep-link), atualiza estado
  useEffect(() => {
    if (isValid(fromUrl) && fromUrl !== preset) {
      setPresetState(fromUrl);
    }
  }, [fromUrl, preset]);

  const setPreset = useCallback(
    (next: Preset) => {
      setPresetState(next);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, next);
      }
      // atualiza query sem recarregar — mantém outros params intactos
      const search = new URLSearchParams(params.toString());
      search.set("period", next);
      router.replace(`?${search.toString()}`, { scroll: false });
    },
    [params, router],
  );

  return { preset, setPreset } as const;
}
