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

export interface DashboardQuery {
  preset?: Preset;
  start?: string; // YYYY-MM-DD (custom range; ignora preset se setado)
  end?: string;
  comparison?: Comparison;
  /** Filtros granulares — null/undefined = sem filtro */
  salesperson?: number | null;
  customer?: number | null;
  product?: number | null;
  category?: number | null;
}

function buildQuery(opts: DashboardQuery = {}): string {
  const params = new URLSearchParams();
  if (opts.start && opts.end) {
    params.set("start", opts.start);
    params.set("end", opts.end);
  } else if (opts.preset) {
    params.set("preset", opts.preset);
  }
  if (opts.comparison) params.set("comparison", opts.comparison);
  if (opts.salesperson) params.set("salesperson", String(opts.salesperson));
  if (opts.customer) params.set("customer", String(opts.customer));
  if (opts.product) params.set("product", String(opts.product));
  if (opts.category) params.set("category", String(opts.category));
  return params.toString() ? `?${params}` : "";
}

export function getExecutive(opts: DashboardQuery = {}) {
  return apiFetch<ExecutiveDashboard & { filters_applied?: boolean }>(
    `/api/dashboards/executive${buildQuery(opts)}`,
  );
}
export function getFinancial(opts: DashboardQuery = {}) {
  return apiFetch<FinancialDashboard & { filters_applied?: boolean }>(
    `/api/dashboards/financial${buildQuery(opts)}`,
  );
}
export function getCommercial(opts: DashboardQuery = {}) {
  return apiFetch<CommercialDashboard & { filters_applied?: boolean }>(
    `/api/dashboards/commercial${buildQuery(opts)}`,
  );
}
