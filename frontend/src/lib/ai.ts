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

export interface AgentToolCall {
  name: string;
  args: Record<string, unknown>;
  ok: boolean;
}

export interface AskResponse {
  session_id: number;
  session_title: string;
  answer: string;
  intent: string;
  blueprint: AnalysisBlueprint;
  used_llm: boolean;
  provider: string;
  llm_error?: "quota_exceeded" | "rate_limited" | "unknown" | "agent_fallback" | null;
  suggestions: string[];
  agent?: {
    tools_called: AgentToolCall[];
    iterations: number;
  } | null;
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
  session_id?: number;
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

// ----------------------------------------------------------------------------
// Histórico de conversas (chat sessions)
// ----------------------------------------------------------------------------
export interface ChatSessionSummary {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatSessionMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  blueprint: AnalysisBlueprint | null;
  tools_called: AgentToolCall[] | null;
  used_llm: boolean;
  llm_provider: string;
  llm_error: string | null;
  created_at: string;
}

export interface ChatSessionDetail extends ChatSessionSummary {
  messages: ChatSessionMessage[];
}

export function listChatSessions(): Promise<{ sessions: ChatSessionSummary[] }> {
  return apiFetch("/api/insights/chats");
}

export function getChatSession(id: number): Promise<ChatSessionDetail> {
  return apiFetch(`/api/insights/chats/${id}`);
}

export function createChatSession(title?: string): Promise<ChatSessionSummary> {
  return apiFetch("/api/insights/chats", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(title ? { title } : {}),
  });
}

export function renameChatSession(id: number, title: string): Promise<ChatSessionSummary> {
  return apiFetch(`/api/insights/chats/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export function deleteChatSession(id: number): Promise<void> {
  return apiFetch(`/api/insights/chats/${id}`, { method: "DELETE" });
}
