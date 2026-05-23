/**
 * Cliente do BI AZUL Analytics — RFV de clientes, Curva ABC de produtos,
 * produtos parados e sugestões de recompra.
 */
import { apiFetch } from "./api";

// ============================================================================
// Customers Analytics
// ============================================================================
export type RfvSegmentKey =
  | "champions"
  | "loyal"
  | "at_risk"
  | "lost"
  | "new"
  | "high_value";

export interface RfvCustomer {
  customer_id: number;
  name: string;
  total: number;
  count: number;
  last_days: number;
  score_R: number;
  score_F: number;
  score_V: number;
}

export interface RfvData {
  total: number;
  segments: Record<RfvSegmentKey, RfvCustomer[]>;
  counts: Record<RfvSegmentKey, number>;
}

export interface CustomerAtRisk {
  customer_id: number;
  name: string;
  total_purchased: number;
  purchases: number;
  last_purchase: string | null;
  days_inactive: number;
}

export interface CustomersAnalyticsResponse {
  rfv: RfvData;
  at_risk: CustomerAtRisk[];
  ltv: {
    ltv_avg: number;
    total_revenue: number;
    unique_customers: number;
    months_back: number;
  };
  repurchase: {
    rate_pct: number;
    total_customers: number;
    repurchased: number;
    window_days: number;
  };
}

export function getCustomersAnalytics() {
  return apiFetch<CustomersAnalyticsResponse>("/api/dashboards/analytics/customers");
}

// ============================================================================
// Products Analytics
// ============================================================================
export interface AbcRow {
  product_id: number;
  name: string;
  sku?: string;
  value: number;
  stock?: number;
  class: "A" | "B" | "C";
  cumulative_pct: number;
}

export interface AbcData {
  total: number;
  by: string;
  rows: AbcRow[];
  counts: { A: number; B: number; C: number };
}

export interface StagnantProduct {
  product_id: number;
  sku: string;
  name: string;
  stock: number;
  cost: number;
  stuck_value: number;
}

export interface ReorderSuggestion {
  product_id: number;
  sku: string;
  name: string;
  stock: number;
  velocity_per_day: number;
  coverage_days: number;
  suggested_qty: number;
  cost: number;
  reorder_cost_estimate: number;
  sold_in_period: number;
  lookback_days: number;
}

export interface ReorderData {
  suggestions: ReorderSuggestion[];
  total_count: number;
  lookback_days: number;
  target_coverage_days: number;
}

export interface ProductsAnalyticsResponse {
  abc: AbcData;
  stagnant: StagnantProduct[];
  reorder: ReorderData;
}

export function getProductsAnalytics(opts: { by?: "stock_value" | "sales" } = {}) {
  const qs = opts.by ? `?by=${opts.by}` : "";
  return apiFetch<ProductsAnalyticsResponse>(`/api/dashboards/analytics/products${qs}`);
}
