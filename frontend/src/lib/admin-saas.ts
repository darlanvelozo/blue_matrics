import { apiFetch } from "./api";

export interface SaasSummary {
  mrr: number;
  arr: number;
  total_tenants: number;
  active_subscribers: number;
  trialing: number;
  expired_trials: number;
  churn_30d_pct: number;
  trial_to_paid_pct: number;
  mau_30d: number;
  revenue_30d: number;
  mrr_by_plan: Array<{
    plan_code: string;
    plan_name: string;
    subscribers: number;
    mrr: number;
  }>;
  signups_30d: Array<{ date: string; count: number }>;
}

export interface AdminTenantListItem {
  id: number;
  public_id: string;
  name: string;
  slug: string;
  cnpj: string;
  status: string;
  trial_ends_at: string | null;
  created_at: string;
  subscription: {
    plan: string | null;
    status: string | null;
    current_period_end: string | null;
  } | null;
  users_count: number;
}

export interface AdminTenantDetail {
  tenant: {
    id: number;
    public_id: string;
    name: string;
    slug: string;
    cnpj: string;
    status: string;
    trial_ends_at: string | null;
    created_at: string;
  };
  subscription: {
    plan: string;
    status: string;
    trial_ends_at: string | null;
    current_period_end: string | null;
    cancel_at_period_end: boolean;
  } | null;
  users: Array<{
    id: number;
    email: string;
    full_name: string;
    role: string;
    last_login: string | null;
  }>;
  invoices_count: number;
  invoices_total: number;
}

export function getSaasSummary(): Promise<SaasSummary> {
  return apiFetch("/api/admin-saas/summary");
}

export function listAdminTenants(q?: string): Promise<{
  tenants: AdminTenantListItem[];
  total: number;
}> {
  const qs = q ? `?q=${encodeURIComponent(q)}` : "";
  return apiFetch(`/api/admin-saas/tenants${qs}`);
}

export function getAdminTenantDetail(id: number): Promise<AdminTenantDetail> {
  return apiFetch(`/api/admin-saas/tenants/${id}`);
}
