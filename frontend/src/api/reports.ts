import request from './request';

export interface ReportQuery {
  start_date?: string;
  end_date?: string;
  store_id?: number;
  category_id?: string;
  period?: string;
}

export interface ReportSummary {
  start_date: string;
  end_date: string;
  period: string;
  sales_total: number;
  order_count: number;
  average_order_value: number;
  gross_profit: number;
  gross_profit_rate: number;
  payment_total: number;
  difference_amount: number;
  out_of_stock_sku_count: number;
}

export interface SalesTrendPoint {
  date: string;
  sales_amount: number;
  order_count: number;
}

export interface StorePerformance {
  rank: number;
  store_id: number;
  store_name: string;
  sales_amount: number;
  order_count: number;
  average_order_value: number;
  gross_profit: number;
  gross_profit_rate: number;
  difference_amount: number;
}

export interface CategoryAnalysis {
  category: string;
  sales_quantity: number;
  sales_amount: number;
  cost_amount: number;
  gross_profit: number;
  gross_profit_rate: number;
}

export interface ProductRanking {
  rank: number;
  product_code: string;
  product_name: string;
  sku_code: string;
  sales_quantity: number;
  sales_amount: number;
  gross_profit: number;
  gross_profit_rate: number;
  current_inventory: number;
}

export interface InventoryDistribution {
  status: string;
  count: number;
  color: string;
}

export interface InventoryAlert {
  id: number;
  store_name: string;
  product_name: string;
  sku_code: string;
  quantity: number;
  safety_stock: number;
  in_transit: number;
  inventory_status: string;
  suggested_qty: number;
}

export interface InventoryHealth {
  distribution: InventoryDistribution[];
  alerts: InventoryAlert[];
}

export interface PromotionEffect {
  promotion_id: number;
  promotion_code: string;
  promotion_name: string;
  promotion_type: string;
  order_count: number;
  discount_amount: number;
  paid_amount: number;
  gross_profit: number;
  gross_profit_rate: number;
  status: string;
  original_amount: number;
}

export interface FinanceOverviewRecord {
  id: number;
  record_no: string;
  order_no: string;
  store_name: string;
  order_amount: number;
  payment_amount: number;
  difference_amount: number;
  status: string;
  reconciliation_time: string;
}

export interface FinanceOverview {
  distribution: InventoryDistribution[];
  records: FinanceOverviewRecord[];
}

function params(query: ReportQuery) {
  return {
    start_date: query.start_date,
    end_date: query.end_date,
    store_id: query.store_id,
    category_id: query.category_id,
    period: query.period
  };
}

export async function fetchReportSummary(query: ReportQuery) {
  const { data } = await request.get<ReportSummary>('/reports/summary', { params: params(query) });
  return data;
}

export async function fetchSalesTrend(query: ReportQuery) {
  const { data } = await request.get<SalesTrendPoint[]>('/reports/sales-trend', { params: params(query) });
  return data;
}

export async function fetchStorePerformance(query: ReportQuery) {
  const { data } = await request.get<StorePerformance[]>('/reports/store-performance', { params: params(query) });
  return data;
}

export async function fetchCategoryAnalysis(query: ReportQuery) {
  const { data } = await request.get<CategoryAnalysis[]>('/reports/category-analysis', { params: params(query) });
  return data;
}

export async function fetchProductRanking(query: ReportQuery) {
  const { data } = await request.get<ProductRanking[]>('/reports/product-ranking', { params: params(query) });
  return data;
}

export async function fetchInventoryHealth(query: ReportQuery) {
  const { data } = await request.get<InventoryHealth>('/reports/inventory-health', { params: params(query) });
  return data;
}

export async function fetchPromotionEffect(query: ReportQuery) {
  const { data } = await request.get<PromotionEffect[]>('/reports/promotion-effect', { params: params(query) });
  return data;
}

export async function fetchFinanceOverview(query: ReportQuery) {
  const { data } = await request.get<FinanceOverview>('/reports/finance-overview', { params: params(query) });
  return data;
}
