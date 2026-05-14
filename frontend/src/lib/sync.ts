import { apiFetch } from "./api";

export type SyncStatus = "running" | "success" | "failed" | "partial";

export interface SyncLogEntry {
  id: number;
  resource: string;
  status: SyncStatus;
  started_at: string;
  finished_at: string | null;
  fetched: number;
  upserted: number;
  errors: number;
  message: string;
}

export function listSyncLogs(): Promise<{ logs: SyncLogEntry[] }> {
  return apiFetch<{ logs: SyncLogEntry[] }>("/api/sync/logs");
}

export function runSyncNow(): Promise<{ task_id: string; status: "queued" }> {
  return apiFetch<{ task_id: string; status: "queued" }>("/api/sync/run", {
    method: "POST",
  });
}
