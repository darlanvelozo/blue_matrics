import { apiFetch } from "./api";

export interface AuditEntry {
  id: number;
  action: string;
  actor_email: string;
  tenant_slug: string | null;
  target_type: string;
  target_id: string;
  metadata: Record<string, unknown>;
  ip: string | null;
  created_at: string;
}

export function listAuditLogs(): Promise<{ entries: AuditEntry[] }> {
  return apiFetch("/api/security/audit-logs");
}

export function exportMyData(): Promise<unknown> {
  return apiFetch("/api/security/me/export");
}

export function deleteMyAccount(confirm: string): Promise<{
  deleted: boolean;
  user_email: string;
  tenants_deleted: string[];
}> {
  return apiFetch("/api/security/me/delete", {
    method: "POST",
    body: JSON.stringify({ confirm }),
  });
}
