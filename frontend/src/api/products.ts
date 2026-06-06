import request from './request';

export interface Product {
  id: number;
  code: string;
  product_code?: string;
  product_name?: string;
  name: string;
  category: string;
  season: string;
  brand: string;
  status: string;
  launch_date: string;
  lifecycle_status: string;
  sale_price: number;
  list_price: number;
  cost_price: number;
}

export interface SKU {
  id: number;
  code?: string;
  sku_code: string;
  product_id: number;
  color: string;
  size: string;
  list_price: number;
  sale_price?: number;
  price?: number;
  cost_price: number;
  barcode: string;
  status: string;
  product?: Product;
  product_code?: string;
  main_color_code?: string;
  sub_color_code?: string;
  size_code?: string;
  is_standard_code?: boolean;
  created_inventory_count?: number;
}

export interface SKUCodePreview {
  product_code: string;
  main_color_code: string;
  sub_color_code: string;
  size_code: string;
  sku_code: string;
  barcode: string;
  color_match_note: string;
  size_match_note: string;
  duplicate_sku: boolean;
}

export interface Promotion {
  id: number;
  name: string;
  promotion_type: string;
  discount_rate: number;
  start_date: string;
  end_date: string;
  status: string;
  description: string;
  applicable_scope: string;
  approval_status: string;
}

export interface Coupon {
  id: number;
  code: string;
  name: string;
  coupon_type: string;
  promotion_id: number | null;
  discount_amount: number;
  discount_rate: number;
  threshold_amount: number;
  valid_start: string;
  valid_end: string;
  target_group: string;
  issued_count: number;
  used_count: number;
  status: string;
  created_at: string;
  per_member_limit?: number | null;
  per_order_use_limit?: number | null;
  stackable?: boolean;
  total_issue_limit?: number | null;
  total_redeem_limit?: number | null;
  applicable_category_ids?: string;
  applicable_product_ids?: string;
  applicable_seasons?: string;
  applicable_member_levels?: string;
  applicable_member_groups?: string;
  applicable_store_ids?: string;
  target_tags?: string;
  issue_mode?: string;
  auto_issue_enabled?: boolean;
  promotion?: Promotion | null;
}

export interface CouponMatchedMember {
  id: number;
  name: string;
  phone: string;
  level: string;
  member_group: string;
  registered_store: string;
  registered_store_text?: string;
  registered_store_names?: string[];
  account_status?: string;
  lifecycle_status?: string;
  last_purchase_at?: string | null;
  match_reason: string;
}

export interface CouponMatchResult {
  matched_count: number;
  matched_members: CouponMatchedMember[];
}

export interface CouponIssueResult {
  created_count: number;
  skipped_count: number;
  failed_items: Array<{ member_id: number; reason: string }>;
}

export interface SalesOrderItem {
  id: number;
  sku_id: number;
  quantity: number;
  unit_price: number;
  unit_cost?: number;
  discount_amount: number;
  subtotal: number;
  cost_amount?: number;
  sku?: SKU;
}

export interface SalesOrder {
  id: number;
  order_no: string;
  store_id: number;
  member_id: number | null;
  promotion_id: number | null;
  order_time: string;
  total_amount: number;
  discount_amount: number;
  paid_amount: number;
  payment_method: string;
  status: string;
  items: SalesOrderItem[];
}

export type ProductPayload = Omit<Product, 'id' | 'list_price' | 'code'> & { code?: string };

export interface SKUPayload {
  product_id?: number;
  sku_code?: string;
  code?: string;
  color?: string;
  size?: string;
  barcode?: string;
  list_price?: number;
  sale_price?: number;
  price?: number;
  cost_price?: number | null;
  status?: string;
}

export type PromotionPayload = Omit<Promotion, 'id'>;

export type CouponPayload = Omit<Coupon, 'id' | 'created_at' | 'promotion'>;

export async function fetchProducts() {
  const { data } = await request.get<Product[]>('/products');
  return data;
}

export async function createProduct(payload: ProductPayload) {
  const { data } = await request.post<Product>('/products', payload);
  return data;
}

export async function updateProduct(id: number, payload: Partial<ProductPayload>) {
  const { data } = await request.put<Product>(`/products/${id}`, payload);
  return data;
}

export async function updateProductStatus(id: number, status: string) {
  const { data } = await request.put<Product>(`/products/${id}/status`, { status });
  return data;
}

export async function fetchSkus() {
  const { data } = await request.get<SKU[]>('/products/skus');
  return data;
}

export async function createSku(payload: SKUPayload) {
  const { data } = await request.post<SKU>('/products/skus', payload);
  return data;
}

export async function generateSkuCode(payload: { product_id: number; color: string; size: string }) {
  const { data } = await request.post<SKUCodePreview>('/products/skus/generate-code', payload);
  return data;
}

export async function updateSku(id: number, payload: SKUPayload) {
  const { data } = await request.put<SKU>(`/products/skus/${id}`, payload);
  return data;
}

export async function updateSkuStatus(id: number, status: string) {
  const { data } = await request.put<SKU>(`/products/skus/${id}/status`, { status });
  return data;
}

export async function fetchPromotions() {
  const { data } = await request.get<Promotion[]>('/promotions');
  return data;
}

export async function createPromotion(payload: PromotionPayload) {
  const { data } = await request.post<Promotion>('/promotions', payload);
  return data;
}

export async function updatePromotion(id: number, payload: Partial<PromotionPayload>) {
  const { data } = await request.put<Promotion>(`/promotions/${id}`, payload);
  return data;
}

export async function updatePromotionStatus(id: number, status: string) {
  const { data } = await request.put<Promotion>(`/promotions/${id}/status`, { status });
  return data;
}

export async function fetchCoupons() {
  const { data } = await request.get<Coupon[]>('/coupons');
  return data;
}

export async function createCoupon(payload: CouponPayload) {
  const { data } = await request.post<Coupon>('/coupons', payload);
  return data;
}

export async function updateCoupon(id: number, payload: Partial<CouponPayload>) {
  const { data } = await request.put<Coupon>(`/coupons/${id}`, payload);
  return data;
}

export async function updateCouponStatus(id: number, status: string) {
  const { data } = await request.put<Coupon>(`/coupons/${id}/status`, { status });
  return data;
}

export async function matchCouponMembers(
  id: number,
  payload: {
    extra_member_ids?: number[];
    exclude_member_ids?: number[];
    conditions?: {
      member_levels?: string[];
      member_groups?: string[];
      tags?: string[];
      store_ids?: number[];
      account_statuses?: string[];
      lifecycle_statuses?: string[];
      recent_purchase_start?: string | null;
      recent_purchase_end?: string | null;
      min_total_spent?: number | null;
      max_total_spent?: number | null;
      min_points?: number | null;
      max_points?: number | null;
    };
  }
) {
  const { data } = await request.post<CouponMatchResult>(`/coupons/${id}/match-members`, payload);
  return data;
}

export async function generateCouponCode() {
  const { data } = await request.get<{ code: string }>('/coupons/generate-code');
  return data;
}

export async function issueCouponToMembers(
  id: number,
  payload: { member_ids: number[]; channels: string[]; remark?: string }
) {
  const { data } = await request.post<CouponIssueResult>(`/coupons/${id}/issue-to-members`, payload);
  return data;
}

export async function fetchSalesOrders() {
  const { data } = await request.get<SalesOrder[]>('/sales/orders', {
    params: { limit: 50 }
  });
  return data;
}
