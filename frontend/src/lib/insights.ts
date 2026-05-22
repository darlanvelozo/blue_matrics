import { apiFetch } from "./api";

export type InsightSeverity = "info" | "success" | "warning" | "critical";

export type InsightKind =
  | "revenue_drop"
  | "revenue_surge"
  | "expense_surge"
  | "top_customer"
  | "top_product"
  | "inactive_customer"
  | "overdue_high"
  | "cash_negative"
  | "ticket_drop"
  | "seasonality";

export interface Insight {
  id: number;
  kind: InsightKind;
  severity: InsightSeverity;
  title: string;
  narrative: string;
  data: Record<string, unknown>;
  period_start: string | null;
  period_end: string | null;
  generated_by: string;
  is_read: boolean;
  created_at: string;
}

export function listInsights(): Promise<{ insights: Insight[]; unread: number; total: number }> {
  return apiFetch("/api/insights/");
}

export function generateInsights(): Promise<{ stats: { candidates: number; created: number; updated: number } }> {
  return apiFetch("/api/insights/generate", { method: "POST" });
}

export function markInsightRead(id: number): Promise<Insight> {
  return apiFetch(`/api/insights/${id}/read`, { method: "POST" });
}

export function dismissInsight(id: number): Promise<{ dismissed: true }> {
  return apiFetch(`/api/insights/${id}/dismiss`, { method: "POST" });
}
