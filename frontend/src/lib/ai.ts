import { apiFetch } from "./api";

export interface AnalysisKpi {
  label: string;
  value: number;
  format?: "currency" | "number" | "percent";
  suffix?: string;
}

export interface AnalysisTable {
  title: string;
  headers: string[];
  rows: Array<Array<string | number>>;
  /** Índices das colunas que devem ser formatadas como moeda. */
  value_columns?: number[];
}

export interface AnalysisChart {
  title: string;
  type: "bar" | "cashflow";
  data: Array<{ label?: string; value?: number } & Record<string, unknown>>;
}

export interface AnalysisBlueprint {
  title: string;
  summary: string;
  intent: string;
  period_days: number;
  kpis: AnalysisKpi[];
  tables: AnalysisTable[];
  charts: AnalysisChart[];
}

export interface AskResponse {
  answer: string;
  intent: string;
  blueprint: AnalysisBlueprint;
  used_llm: boolean;
  provider: string;
  llm_error?: "quota_exceeded" | "rate_limited" | "unknown" | null;
  suggestions: string[];
}

export interface AnalyzeResponse {
  blueprint: AnalysisBlueprint;
  interpretation: {
    intent: string;
    window_days: number;
    limit: number;
  };
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export function askAi(payload: {
  question: string;
  history?: ChatMessage[];
}): Promise<AskResponse> {
  return apiFetch("/api/insights/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function analyzeAi(payload: { question: string }): Promise<AnalyzeResponse> {
  return apiFetch("/api/insights/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
