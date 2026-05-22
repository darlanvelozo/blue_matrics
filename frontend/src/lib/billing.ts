import { apiFetch } from "./api";

export type PlanCode = "starter" | "growth" | "business";

export type SubscriptionStatus =
  | "trialing"
  | "active"
  | "past_due"
  | "canceled"
  | "incomplete";

export type InvoiceStatus = "draft" | "open" | "paid" | "void" | "uncollectible";

export interface Plan {
  code: PlanCode;
  name: string;
  description: string;
  price_monthly: number;
  currency: string;
  max_users: number;
  features: string[];
  sort_order: number;
}

export interface SubscriptionData {
  plan: Plan;
  status: SubscriptionStatus;
  is_active: boolean;
  is_trialing: boolean;
  trial_expired: boolean;
  trial_ends_at: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  canceled_at: string | null;
}

export interface InvoiceData {
  id: number;
  amount: number;
  currency: string;
  status: InvoiceStatus;
  period_start: string | null;
  period_end: string | null;
  paid_at: string | null;
  hosted_invoice_url: string;
  invoice_pdf_url: string;
  created_at: string;
}

export function listPlans(): Promise<{ plans: Plan[] }> {
  return apiFetch("/api/billing/plans", { skipAuth: true });
}

export function getSubscription(): Promise<{
  subscription: SubscriptionData;
  invoices: InvoiceData[];
  provider: "mock" | "stripe";
}> {
  return apiFetch("/api/billing/subscription");
}

export function startCheckout(plan_code: PlanCode): Promise<{ url: string; session_id: string }> {
  return apiFetch("/api/billing/checkout", {
    method: "POST",
    body: JSON.stringify({ plan_code }),
  });
}

export function cancelSubscription(): Promise<SubscriptionData> {
  return apiFetch("/api/billing/cancel", { method: "POST" });
}

export function reactivateSubscription(): Promise<SubscriptionData> {
  return apiFetch("/api/billing/reactivate", { method: "POST" });
}
