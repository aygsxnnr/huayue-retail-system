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
  promotion?: Promotion | null;
}

export interface SalesOrderItem {
  id: number;
  sku_id: number;
  quantity: number;
  unit_price: number;
  discount_amount: number;
  subtotal: number;
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

export type ProductPayload = Omit<Product, 'id' | 'list_price' | 'cost_price' | 'code'> & { code?: string };

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

export async function fetchSalesOrders() {
  const { data } = await request.get<SalesOrder[]>('/sales/orders', {
    params: { limit: 50 }
  });
  return data;
}
