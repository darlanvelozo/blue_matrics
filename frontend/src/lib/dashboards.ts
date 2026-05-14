import { apiFetch } from "./api";

export type Preset =
  | "last_30d"
  | "last_90d"
  | "this_month"
  | "last_month"
  | "ytd"
  | "last_12m";

export type Comparison = "prev_period" | "yoy";

export interface KpiWithChange {
  current: number;
  previous: number;
  change_pct: number | null;
}

export interface RevenueByMonth {
  month: string; // YYYY-MM
  revenue: number;
  sales_count: number;
}

export interface CashflowByMonth {
  month: string;
  in: number;
  out: number;
  net: number;
}

export interface TopCustomer {
  customer_id: number;
  name: string;
  total: number;
  sales: number;
}

export interface TopProduct {
  product_id: number;
  name: string;
  total: number;
  quantity: number;
}

export interface BySalesperson {
  salesperson_id: number;
  name: string;
  total: number;
  sales: number;
}

export interface ExecutiveDashboard {
  has_data: boolean;
  period: { start: string; end: string };
  comparison_mode: Comparison;
  revenue: KpiWithChange;
  net_profit: KpiWithChange;
  avg_ticket: KpiWithChange;
  num_sales: KpiWithChange;
  overdue_rate: number;
  revenue_by_month: RevenueByMonth[];
  top_customers: TopCustomer[];
  top_products: TopProduct[];
}

export interface FinancialDashboard {
  has_data: boolean;
  period: { start: string; end: string };
  comparison_mode: Comparison;
  cash_in: KpiWithChange;
  cash_out: KpiWithChange;
  net_profit: KpiWithChange;
  overdue_rate: number;
  cashflow_by_month: CashflowByMonth[];
  dre_monthly: CashflowByMonth[];
}

export interface CommercialDashboard {
  has_data: boolean;
  period: { start: string; end: string };
  comparison_mode: Comparison;
  revenue: KpiWithChange;
  num_sales: KpiWithChange;
  avg_ticket: KpiWithChange;
  revenue_by_month: RevenueByMonth[];
  top_customers: TopCustomer[];
  top_products: TopProduct[];
  by_salesperson: BySalesperson[];
}

function buildQuery(opts: { preset?: Preset; comparison?: Comparison } = {}) {
  const params = new URLSearchParams();
  if (opts.preset) params.set("preset", opts.preset);
  if (opts.comparison) params.set("comparison", opts.comparison);
  return params.toString() ? `?${params}` : "";
}

export function getExecutive(opts: { preset?: Preset; comparison?: Comparison } = {}) {
  return apiFetch<ExecutiveDashboard>(`/api/dashboards/executive${buildQuery(opts)}`);
}
export function getFinancial(opts: { preset?: Preset; comparison?: Comparison } = {}) {
  return apiFetch<FinancialDashboard>(`/api/dashboards/financial${buildQuery(opts)}`);
}
export function getCommercial(opts: { preset?: Preset; comparison?: Comparison } = {}) {
  return apiFetch<CommercialDashboard>(`/api/dashboards/commercial${buildQuery(opts)}`);
}
