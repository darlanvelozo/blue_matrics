import { apiFetch } from "./api";

export type DashboardKind = "executive" | "financial" | "commercial";

export interface SharedReport {
  id: number;
  dashboard: DashboardKind;
  preset: string;
  token: string;
  url_path: string;
  expires_at: string;
  revoked_at: string | null;
  view_count: number;
  is_active: boolean;
  created_at: string;
  created_by_email: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Faz download de XLSX ou abre HTML printable em nova aba.
 * Como o endpoint exige Authorization, não basta usar window.open — temos que
 * baixar via fetch autenticado e injetar como blob.
 */
export async function downloadReport(
  dashboard: DashboardKind,
  fmt: "excel" | "html",
  preset = "last_12m",
): Promise<void> {
  const access = typeof window !== "undefined" ? window.localStorage.getItem("bm.access") : null;
  const url = `${API_URL}/api/reports/export/${dashboard}/${fmt}?preset=${encodeURIComponent(preset)}`;
  const res = await fetch(url, {
    headers: access ? { Authorization: `Bearer ${access}` } : {},
  });
  if (!res.ok) {
    throw new Error(`Falha ao exportar (HTTP ${res.status})`);
  }
  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);

  if (fmt === "html") {
    window.open(blobUrl, "_blank", "noopener,noreferrer");
    // não revogamos imediato — o browser precisa do URL pra carregar
    setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
    return;
  }
  // excel: força download
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = `bluemetrics-${dashboard}-${new Date().toISOString().slice(0, 10)}.xlsx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(blobUrl);
}

export function listShares() {
  return apiFetch<{ shares: SharedReport[] }>("/api/reports/shares");
}

export function createShare(payload: {
  dashboard: DashboardKind;
  preset?: string;
  days_valid?: number;
}) {
  return apiFetch<SharedReport>("/api/reports/shares", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function revokeShare(id: number) {
  return apiFetch<SharedReport>(`/api/reports/shares/${id}`, { method: "DELETE" });
}

export function publicShareUrl(token: string): string {
  return `${API_URL}/r/${token}`;
}
