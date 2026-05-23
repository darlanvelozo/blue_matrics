import { apiFetch } from "./api";

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface PagedResponse<T> {
  results: T[];
  meta: PaginationMeta;
}

export interface CustomerListItem {
  id: number;
  external_id: string;
  name: string;
  document: string;
  email: string;
  phone: string;
  is_active: boolean;
  /** "Cliente", "Fornecedor", "Cliente · Fornecedor" ou "—". */
  type: string;
  /** Total recebido deste cliente (sum FinancialEntry direction=receivable). */
  total_received: number;
  /** Total pago a este fornecedor (sum FinancialEntry direction=payable). */
  total_paid: number;
  received_count: number;
  paid_count: number;
  /** ISO datetime da última transação (recebimento ou pagamento). */
  last_transaction: string | null;
  /** Vendas formais via módulo Sale (raras na maioria dos tenants). */
  sales_count: number;
  total_spent_sales: number;
}

export interface CustomerListSummary {
  total_received: number;
  total_paid: number;
}

export interface ProductListItem {
  id: number;
  external_id: string;
  sku: string;
  name: string;
  price: number;
  cost: number;
  stock_balance: number;
  stock_value: number;
  margin_pct: number;
  is_active: boolean;
}

export interface ProductListSummary {
  total_stock_value: number;
  total_stock_qty: number;
}

export interface SaleListItem {
  id: number;
  external_id: string;
  number: string;
  status: "draft" | "open" | "closed" | "canceled";
  customer: { id: number; name: string } | null;
  salesperson: { id: number; name: string } | null;
  issued_at: string | null;
  total: number;
  discount: number;
}

export interface SaleDetail extends SaleListItem {
  items: Array<{
    id: number;
    description: string;
    product: { id: number; name: string } | null;
    quantity: number;
    unit_price: number;
    total: number;
  }>;
}

export interface FinancialListItem {
  id: number;
  external_id: string;
  direction: "receivable" | "payable";
  status: "pending" | "paid" | "overdue" | "canceled";
  description: string;
  amount: number;
  due_date: string | null;
  paid_at: string | null;
  category: { id: number; name: string; kind: string } | null;
  customer: { id: number; name: string } | null;
}

export interface FilterOptions {
  salespeople: Array<{ id: number; name: string }>;
  categories: Array<{ id: number; name: string; kind: string }>;
  customers: Array<{ id: number; name: string }>;
  products: Array<{ id: number; name: string }>;
}

// ---------- API helpers ----------
export interface SalesQuery {
  start?: string;
  end?: string;
  customer?: number | null;
  salesperson?: number | null;
  product?: number | null;
  status?: string;
  q?: string;
  page?: number;
  page_size?: number;
}

function buildQS(q: Record<string, unknown>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) {
    if (v === null || v === undefined || v === "") continue;
    p.set(k, String(v));
  }
  return p.toString() ? `?${p}` : "";
}

export function listCustomers(
  q: {
    q?: string;
    page?: number;
    page_size?: number;
    type?: "all" | "customer" | "supplier" | "active";
  } = {},
) {
  return apiFetch<PagedResponse<CustomerListItem> & { summary: CustomerListSummary }>(
    `/api/explorer/customers${buildQS(q)}`,
  );
}

export function listProducts(q: { q?: string; page?: number; page_size?: number } = {}) {
  return apiFetch<PagedResponse<ProductListItem> & { summary: ProductListSummary }>(
    `/api/explorer/products${buildQS(q)}`,
  );
}

export function listSales(q: SalesQuery = {}) {
  return apiFetch<PagedResponse<SaleListItem> & { summary: { total_value: number } }>(
    `/api/explorer/sales${buildQS(q as Record<string, unknown>)}`,
  );
}

export function getSaleDetail(id: number) {
  return apiFetch<SaleDetail>(`/api/explorer/sales/${id}`);
}

export interface FinancialQuery {
  direction?: "receivable" | "payable";
  status?: string;
  start?: string;
  end?: string;
  category?: number | null;
  customer?: number | null;
  page?: number;
  page_size?: number;
}

export function listFinancial(q: FinancialQuery = {}) {
  return apiFetch<PagedResponse<FinancialListItem> & { summary: { total_value: number } }>(
    `/api/explorer/financial${buildQS(q as Record<string, unknown>)}`,
  );
}

export function getFilterOptions() {
  return apiFetch<FilterOptions>("/api/explorer/filter-options");
}
