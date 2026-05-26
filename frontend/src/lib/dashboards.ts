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

export interface TopCategory {
  category_id: number;
  name: string;
  total: number;
  count: number;
}

export interface TopFinancialCustomer {
  customer_id: number;
  name: string;
  total: number;
  count: number;
}

export interface AmountWithCount {
  total: number;
  count: number;
}

export interface UpcomingWindow {
  days: number;
  total: number;
  count: number;
}

// Compartilhados v2 (overview + dashboards premium)
export interface MonthlyGrowthPoint {
  month: string;
  revenue: number;
  expense: number;
  profit: number;
  margin_pct: number;
  revenue_growth_mom_pct: number | null;
  profit_growth_mom_pct: number | null;
  cumulative_revenue: number;
  cumulative_profit: number;
}

export interface DreItem {
  category_id: number | null;
  category: string;
  total: number;
  share_pct: number;
}

export interface DreStructured {
  revenues: DreItem[];
  expenses_fixed: DreItem[];
  expenses_variable: DreItem[];
  totals: {
    revenue: number;
    expense_fixed: number;
    expense_variable: number;
    expense_total: number;
    contribution_margin: number;
    net_profit: number;
    net_margin_pct: number;
    ebitda: number;
  };
}

export interface ExpenseBreakdown {
  fixed: number;
  variable: number;
  total: number;
}

export type FinancialAlertSeverity = "info" | "warning" | "critical";
export interface FinancialAlert {
  kind: string;
  severity: FinancialAlertSeverity;
  title: string;
  message: string;
  value?: number;
}

export interface ExecutiveDashboard {
  has_data: boolean;
  period: { start: string; end: string };
  comparison_mode: Comparison;
  revenue: KpiWithChange;
  cash_in: KpiWithChange;
  cash_out: KpiWithChange;
  net_profit: KpiWithChange;
  avg_ticket: KpiWithChange;
  num_sales: KpiWithChange;
  overdue_rate: number;
  overdue_receivables: AmountWithCount;
  overdue_payables: AmountWithCount;
  upcoming_receivables_30d: UpcomingWindow;
  upcoming_payables_30d: UpcomingWindow;
  revenue_by_month: RevenueByMonth[];
  cashflow_by_month: CashflowByMonth[];
  top_customers: TopCustomer[];
  top_products: TopProduct[];
  top_receivable_categories: TopCategory[];
  top_payable_categories: TopCategory[];
  // v2 additions
  ebitda_month: { current: number };
  ebitda_period: { current: number };
  net_margin_pct_period: number;
  roi_operational_pct: number;
  breakeven: BreakevenInfo;
  forecast_30d: CashForecastInfo;
  working_capital: WorkingCapitalInfo;
  cash_balance: number;
  burn_rate_monthly: number;
  health_score: HealthScore;
  monthly_growth: MonthlyGrowthPoint[];
}

export interface FinancialDashboard {
  has_data: boolean;
  period: { start: string; end: string };
  comparison_mode: Comparison;
  cash_in: KpiWithChange;
  cash_out: KpiWithChange;
  net_profit: KpiWithChange;
  overdue_rate: number;
  overdue_receivables: AmountWithCount;
  overdue_payables: AmountWithCount;
  upcoming_receivables_30d: UpcomingWindow;
  upcoming_receivables_60d: UpcomingWindow;
  upcoming_receivables_90d: UpcomingWindow;
  upcoming_payables_30d: UpcomingWindow;
  upcoming_payables_60d: UpcomingWindow;
  upcoming_payables_90d: UpcomingWindow;
  cashflow_by_month: CashflowByMonth[];
  dre_monthly: CashflowByMonth[];
  top_receivable_categories: TopCategory[];
  top_payable_categories: TopCategory[];
  top_receivable_customers: TopFinancialCustomer[];
  top_payable_suppliers: TopFinancialCustomer[];
  // v2 additions
  dre: DreStructured;
  expense_breakdown: ExpenseBreakdown;
  contribution_margin_pct: number;
  breakeven: BreakevenInfo;
  working_capital: WorkingCapitalInfo;
  cash_balance: number;
  burn_rate_monthly: number;
  ebitda_period: { current: number };
  ebitda_month: { current: number };
  roi_operational_pct: number;
  forecast_30d: CashForecastInfo;
  monthly_growth: MonthlyGrowthPoint[];
  alerts: FinancialAlert[];
}

export interface CommercialDashboard {
  has_data: boolean;
  period: { start: string; end: string };
  comparison_mode: Comparison;
  revenue: KpiWithChange;
  num_sales: KpiWithChange;
  avg_ticket: KpiWithChange;
  cash_in: KpiWithChange;
  revenue_by_month: RevenueByMonth[];
  top_customers: TopCustomer[];
  top_products: TopProduct[];
  by_salesperson: BySalesperson[];
  top_receivable_customers: TopFinancialCustomer[];
  // v2 additions
  commercial_kpis: CommercialKpis;
  ltv: LtvInfo;
  repurchase_rate: RepurchaseInfo;
  revenue_forecast_30d: RevenueForecast;
  revenue_forecast_90d: RevenueForecast;
  monthly_growth: MonthlyGrowthPoint[];
  abc_curve: AbcCurve;
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

// ============================================================================
// Tipos preditivos (Fase 3)
// ============================================================================
export interface RevenueForecast {
  forecast_total: number;
  forecast_daily_avg: number;
  baseline_avg_monthly: number;
  trend_pct_monthly: number;
  confidence: "high" | "medium" | "low";
  has_seasonality: boolean;
  last_months: Array<{ month: string; revenue: number }>;
  days_ahead: number;
  method?: string;
}

export interface LtvInfo {
  ltv_avg: number;
  total_revenue: number;
  attributable_revenue?: number;
  anonymous_revenue?: number;
  anonymous_pct?: number;
  low_confidence?: boolean;
  source?: "sales" | "financial_entries" | "none";
  unique_customers: number;
  via_sales: number;
  via_financial: number;
  months_back: number;
}

export interface RepurchaseInfo {
  rate_pct: number;
  total_customers: number;
  repurchased: number;
  window_days: number;
}

export interface AbcCurveRow {
  product_id: number;
  name: string;
  sku?: string;
  value: number;
  stock?: number;
  class: "A" | "B" | "C";
  cumulative_pct: number;
}

export interface AbcCurve {
  total: number;
  by: string;
  rows: AbcCurveRow[];
  counts: { A: number; B: number; C: number };
}

export interface CommercialKpis {
  revenue_sale: number;
  revenue_cash: number;
  num_sales: number;
  avg_ticket_sale: number;
  by_salesperson: BySalesperson[];
  top_products: TopProduct[];
  top_customers: TopCustomer[];
  top_revenue_categories: TopCategory[];
}

export interface PredictiveResponse {
  has_data: boolean;
  predictive: {
    revenue_forecast: {
      "30d": RevenueForecast;
      "60d": RevenueForecast;
      "90d": RevenueForecast;
    };
    expense_forecast_30d: {
      forecast_total: number;
      baseline_avg_monthly: number;
      days_ahead: number;
    };
    cash_forecast: {
      "30d": CashForecastInfo;
      "60d": CashForecastInfo;
      "90d": CashForecastInfo;
    };
    overdue_risk: {
      overdue_amount: number;
      open_amount: number;
      risk_pct: number;
    };
    ltv: LtvInfo;
    repurchase: RepurchaseInfo;
  };
  health_score: HealthScore;
  alerts: FinancialAlert[];
}

export function getPredictive() {
  return apiFetch<PredictiveResponse>("/api/dashboards/predictive");
}


export function getExecutive(opts: DashboardQuery = {}) {
  return apiFetch<ExecutiveDashboard & { filters_applied?: boolean }>(
    `/api/dashboards/executive${buildQuery(opts)}`,
  );
}

// ============================================================================
// Overview (Visão Geral premium)
// ============================================================================
export interface OverviewKpi {
  current: number;
  previous?: number;
  change_pct?: number | null;
}

export interface BreakevenInfo {
  breakeven: number;
  revenue: number;
  diff: number;
  above: boolean;
  pct: number;
}

export interface CashForecastInfo {
  current_balance: number;
  expected_in: number;
  expected_out: number;
  projected_balance: number;
  days: number;
  at_risk: boolean;
}

export interface WorkingCapitalInfo {
  receivables_open: number;
  payables_open: number;
  working_capital: number;
}

export interface HealthScore {
  score: number;
  label: string;
  color: "green" | "blue" | "amber" | "red";
  components: {
    margin: number;
    cash_balance: number;
    inadimplencia: number;
    supplier_concentration: number;
  };
  details: {
    net_margin_pct: number;
    projected_balance_30d: number;
    overdue_pct: number;
    top_supplier_pct: number;
  };
}

export type SmartCardSeverity = "info" | "success" | "warning" | "critical";

export interface SmartCard {
  kind: string;
  severity: SmartCardSeverity;
  title: string;
  message: string;
  action?: string;
  metric?: unknown;
}

export interface OverviewResponse {
  has_data: boolean;
  tenant: { id: number; name: string; slug: string };
  period: {
    current_month: { start: string; end: string; label: string };
    previous_month: { start: string; end: string; label: string };
  };
  kpis: {
    revenue_month: OverviewKpi;
    net_profit_month: OverviewKpi;
    net_margin_pct: OverviewKpi;
    ebitda: OverviewKpi;
    cash_balance_now: OverviewKpi;
    burn_rate_monthly: OverviewKpi;
    working_capital: WorkingCapitalInfo;
    breakeven: BreakevenInfo;
    forecast_30d: CashForecastInfo;
  };
  growth: {
    revenue_mom_pct: number | null;
    profit_mom_pct: number | null;
  };
  health_score: HealthScore;
  trend_12m: Array<{ month: string; in: number; out: number; net: number }>;
  rankings: {
    top_revenue_categories: Array<{ category_id: number; name: string; total: number; count: number }>;
    top_expense_categories: Array<{ category_id: number; name: string; total: number; count: number }>;
    top_customers_receivable: Array<{ customer_id: number; name: string; total: number; count: number }>;
    top_suppliers_payable: Array<{ customer_id: number; name: string; total: number; count: number }>;
  };
  smart_cards: SmartCard[];
}

export function getOverview() {
  return apiFetch<OverviewResponse>("/api/dashboards/overview");
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
