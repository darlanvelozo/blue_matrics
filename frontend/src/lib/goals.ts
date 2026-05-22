import { apiFetch } from "./api";

export type GoalKind = "revenue" | "net_profit" | "num_sales" | "avg_ticket";
export type GoalPeriod = "month" | "quarter" | "year";

export interface GoalProgress {
  current: number;
  target: number;
  progress_pct: number;
  achieved: boolean;
  period_start: string;
  period_end: string;
}

export interface Goal {
  id: number;
  name: string;
  kind: GoalKind;
  period: GoalPeriod;
  target_value: number;
  starts_on: string;
  is_active: boolean;
  created_at: string;
  progress?: GoalProgress;
}

export const GOAL_KIND_LABELS: Record<GoalKind, string> = {
  revenue: "Faturamento",
  net_profit: "Lucro líquido",
  num_sales: "Nº de vendas",
  avg_ticket: "Ticket médio",
};

export const GOAL_PERIOD_LABELS: Record<GoalPeriod, string> = {
  month: "Mensal",
  quarter: "Trimestral",
  year: "Anual",
};

export interface CreateGoalPayload {
  name: string;
  kind: GoalKind;
  period: GoalPeriod;
  target_value: number;
}

export type UpdateGoalPayload = Partial<CreateGoalPayload> & { is_active?: boolean };

export function listGoals() {
  return apiFetch<{ goals: Goal[] }>("/api/goals/");
}

export function createGoal(payload: CreateGoalPayload) {
  return apiFetch<Goal>("/api/goals/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateGoal(id: number, payload: UpdateGoalPayload) {
  return apiFetch<Goal>(`/api/goals/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteGoal(id: number) {
  return apiFetch<void>(`/api/goals/${id}`, { method: "DELETE" });
}
