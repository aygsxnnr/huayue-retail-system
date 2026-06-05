import request from './request';

export interface FinanceSummary {
  today_order_amount: number;
  today_payment_amount: number;
  today_difference_amount: number;
  pending_difference_count: number;
  settled_count: number;
  gross_profit: number;
  gross_profit_rate: number;
  promotion_discount_amount: number;
}

export interface FinanceRecord {
  id: number;
  record_no: string;
  order_no: string;
  store_name: string;
  cashier_name: string;
  order_amount: number;
  payment_amount: number;
  discount_amount: number;
  difference_amount: number;
  payment_method: string;
  status: string;
  reconciliation_time: string;
}

export interface PaymentRecord {
  id: number;
  payment_no: string;
  order_no: string;
  store_name: string;
  payment_method: string;
  payable_amount: number;
  paid_amount: number;
  payment_status: string;
  payment_time: string;
  third_party_no: string;
  cashier_name?: string;
  finance_record_no?: string;
  difference_amount?: number;
  remark?: string;
}

export interface BatchResolveResult {
  success_count: number;
  failed_count: number;
  failed_items: Array<{
    id: number;
    reason: string;
  }>;
}

export interface FinanceTrendPoint {
  date: string;
  order_amount: number;
  payment_amount: number;
  difference_amount: number;
  sales_amount: number;
  cost_amount: number;
  gross_profit: number;
}

export interface ProductProfitRank {
  rank: number;
  product_name: string;
  sku_code: string;
  sales_quantity: number;
  sales_amount: number;
  cost_amount: number;
  gross_profit: number;
  gross_profit_rate: number;
}

export interface CategoryProfit {
  category: string;
  sales_amount: number;
  cost_amount: number;
  gross_profit: number;
  gross_profit_rate: number;
}

export interface ProfitTrend {
  trend: FinanceTrendPoint[];
  product_profit_rank: ProductProfitRank[];
  category_profit: CategoryProfit[];
}

export interface PromotionLoss {
  promotion_id: number;
  promotion_code: string;
  promotion_name: string;
  promotion_type: string;
  order_count: number;
  original_amount: number;
  discount_amount: number;
  paid_amount: number;
  cost_amount: number;
  gross_profit: number;
  gross_profit_rate: number;
  status: string;
}

export interface StoreSettlement {
  store_id: number;
  store_name: string;
  sales_amount: number;
  order_count: number;
  average_order_value: number;
  cost_amount: number;
  gross_profit: number;
  gross_profit_rate: number;
  promotion_discount_amount: number;
  difference_amount: number;
  settlement_status: string;
}

export async function fetchFinanceSummary() {
  const { data } = await request.get<FinanceSummary>('/finance/summary');
  return data;
}

export async function fetchFinanceRecords() {
  const { data } = await request.get<FinanceRecord[]>('/finance/records');
  return data;
}

export async function resolveFinanceRecord(id: number) {
  const { data } = await request.put<FinanceRecord>(`/finance/records/${id}/resolve`);
  return data;
}

export async function reconcileFinanceRecord(id: number) {
  const { data } = await request.put<FinanceRecord>(`/finance/records/${id}/reconcile`);
  return data;
}

export async function batchResolveFinanceRecords(recordIds: number[]) {
  const { data } = await request.put<BatchResolveResult>('/finance/records/batch-resolve', {
    record_ids: recordIds
  });
  return data;
}

export async function batchReconcileFinanceRecords(recordIds: number[]) {
  const { data } = await request.put<BatchResolveResult>('/finance/records/batch-reconcile', {
    record_ids: recordIds
  });
  return data;
}

export async function fetchPaymentRecords() {
  const { data } = await request.get<PaymentRecord[]>('/finance/payments');
  return data;
}

export async function fetchProfitTrend() {
  const { data } = await request.get<ProfitTrend>('/finance/profit-trend');
  return data;
}

export async function fetchStoreSettlement() {
  const { data } = await request.get<StoreSettlement[]>('/finance/store-settlement');
  return data;
}

export async function fetchPromotionLoss() {
  const { data } = await request.get<PromotionLoss[]>('/finance/promotion-loss');
  return data;
}
