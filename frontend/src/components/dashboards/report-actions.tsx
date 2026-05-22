"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, FileSpreadsheet, FileText, Link2, Share2, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  type DashboardKind,
  createShare,
  downloadReport,
  listShares,
  publicShareUrl,
  revokeShare,
} from "@/lib/reports";

interface Props {
  dashboard: DashboardKind;
  preset: string;
}

/**
 * Botões "Exportar" (Excel/HTML) e "Compartilhar" (link público).
 * Renderiza inline; dialogs simples controlados por estado local.
 */
export function ReportActions({ dashboard, preset }: Props) {
  const [exportOpen, setExportOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [busy, setBusy] = useState<"excel" | "html" | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const exportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) {
        setExportOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  async function handleExport(fmt: "excel" | "html") {
    setBusy(fmt);
    setErr(null);
    try {
      await downloadReport(dashboard, fmt, preset);
      setExportOpen(false);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Falha ao exportar.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <div className="relative inline-block" ref={exportRef}>
        <Button variant="outline" onClick={() => setExportOpen((v) => !v)}>
          <FileText className="mr-1 h-4 w-4" />
          Exportar
        </Button>
        {exportOpen && (
          <div className="absolute right-0 z-30 mt-1 w-56 overflow-hidden rounded-md border border-[color:var(--border)] bg-[color:var(--card)] shadow-lg">
            <button
              type="button"
              onClick={() => handleExport("excel")}
              disabled={busy === "excel"}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-[color:var(--accent)] disabled:opacity-50"
            >
              <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
              {busy === "excel" ? "Baixando…" : "Baixar Excel (.xlsx)"}
            </button>
            <button
              type="button"
              onClick={() => handleExport("html")}
              disabled={busy === "html"}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-[color:var(--accent)] disabled:opacity-50"
            >
              <FileText className="h-4 w-4 text-blue-600" />
              {busy === "html" ? "Abrindo…" : "Abrir HTML (imprimir PDF)"}
            </button>
            {err && (
              <p className="border-t border-[color:var(--border)] bg-red-50 px-3 py-2 text-xs text-red-700">
                {err}
              </p>
            )}
          </div>
        )}
      </div>

      <Button variant="outline" onClick={() => setShareOpen(true)}>
        <Share2 className="mr-1 h-4 w-4" />
        Compartilhar
      </Button>

      {shareOpen && (
        <ShareDialog
          dashboard={dashboard}
          preset={preset}
          onClose={() => setShareOpen(false)}
        />
      )}
    </>
  );
}

function ShareDialog({
  dashboard,
  preset,
  onClose,
}: {
  dashboard: DashboardKind;
  preset: string;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["shares"], queryFn: listShares });
  const allShares = data?.shares ?? [];
  // Filtra pelo dashboard ativo
  const shares = allShares.filter((s) => s.dashboard === dashboard);

  const [days, setDays] = useState(7);
  const [copied, setCopied] = useState<number | null>(null);

  const create = useMutation({
    mutationFn: () => createShare({ dashboard, preset, days_valid: days }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["shares"] }),
  });

  const revoke = useMutation({
    mutationFn: (id: number) => revokeShare(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["shares"] }),
  });

  async function copyLink(token: string, id: number) {
    try {
      await navigator.clipboard.writeText(publicShareUrl(token));
      setCopied(id);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-lg bg-[color:var(--card)] shadow-xl">
        <div className="flex items-center justify-between border-b border-[color:var(--border)] px-4 py-3">
          <h2 className="text-base font-semibold">Compartilhar relatório</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-[color:var(--muted-foreground)] hover:bg-[color:var(--accent)]"
            aria-label="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 p-4">
          <div>
            <label className="text-sm font-medium" htmlFor="share-days">
              Gerar novo link
            </label>
            <p className="mt-0.5 text-xs text-[color:var(--muted-foreground)]">
              Qualquer pessoa com o link poderá ver o relatório atual (sem login)
              durante o período abaixo. Você pode revogar quando quiser.
            </p>
            <div className="mt-2 flex items-center gap-2">
              <input
                id="share-days"
                type="number"
                min={1}
                max={90}
                value={days}
                onChange={(e) => setDays(Math.max(1, Math.min(90, Number(e.target.value) || 7)))}
                className="w-20 rounded-md border border-[color:var(--border)] bg-[color:var(--background)] px-2 py-1.5 text-sm"
              />
              <span className="text-sm text-[color:var(--muted-foreground)]">dias</span>
              <Button
                type="button"
                onClick={() => create.mutate()}
                disabled={create.isPending}
                className="ml-auto"
              >
                <Link2 className="mr-1 h-4 w-4" />
                {create.isPending ? "Gerando…" : "Gerar link"}
              </Button>
            </div>
          </div>

          <div>
            <h3 className="mb-2 text-sm font-medium">Links existentes</h3>
            {isLoading ? (
              <p className="text-xs text-[color:var(--muted-foreground)]">Carregando…</p>
            ) : shares.length === 0 ? (
              <p className="text-xs text-[color:var(--muted-foreground)]">
                Nenhum link criado para este dashboard ainda.
              </p>
            ) : (
              <ul className="max-h-64 space-y-2 overflow-y-auto">
                {shares.map((s) => (
                  <li
                    key={s.id}
                    className="flex items-center gap-2 rounded-md border border-[color:var(--border)] p-2 text-xs"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-mono">{publicShareUrl(s.token)}</p>
                      <p className="text-[color:var(--muted-foreground)]">
                        {s.is_active
                          ? `Expira em ${new Date(s.expires_at).toLocaleDateString("pt-BR")}`
                          : "Inativo"}
                        {" · "}
                        {s.view_count} visualizações
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => copyLink(s.token, s.id)}
                      className="rounded-md p-1.5 hover:bg-[color:var(--accent)]"
                      aria-label="Copiar link"
                      disabled={!s.is_active}
                    >
                      {copied === s.id ? (
                        <Check className="h-3.5 w-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="h-3.5 w-3.5" />
                      )}
                    </button>
                    {s.is_active && (
                      <button
                        type="button"
                        onClick={() => {
                          if (confirm("Revogar este link? Ele deixará de funcionar.")) {
                            revoke.mutate(s.id);
                          }
                        }}
                        className="rounded-md p-1.5 text-red-500 hover:bg-red-50"
                        aria-label="Revogar"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
