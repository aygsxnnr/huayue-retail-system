import request from './request';

export interface Store {
  id: number;
  code: string;
  name: string;
  city: string;
  address: string;
  manager: string;
  status: string;
}

export interface POSSku {
  sku_id: number;
  sku_code: string;
  barcode: string;
  product_name: string;
  category: string;
  color: string;
  size: string;
  list_price: number;
  cost_price: number;
  store_id: number;
  store_name: string;
  inventory_quantity: number;
  safety_stock: number;
}

export interface Member {
  id: number;
  member_no: string;
  name: string;
  phone: string;
  level: string;
  tags: string;
  member_tags: string[];
  available_coupons: string[];
  points: number;
  total_spent: number;
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
}

export interface SalesOrderItem {
  id: number;
  sku_id: number;
  quantity: number;
  unit_price: number;
  discount_amount: number;
  subtotal: number;
  sku?: {
    sku_code: string;
    color: string;
    size: string;
    product?: {
      name: string;
    };
  };
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

export interface CreateOrderPayload {
  store_id: number;
  member_id?: number;
  promotion_id?: number;
  payment_method: string;
  items: Array<{
    sku_id: number;
    quantity: number;
  }>;
}

export async function fetchStores() {
  const { data } = await request.get<Store[]>('/sales/stores');
  return data;
}

export async function searchPosSkus(storeId: number, keyword: string) {
  const { data } = await request.get<POSSku[]>('/sales/pos/skus', {
    params: { store_id: storeId, keyword }
  });
  return data;
}

export async function searchMembers(keyword: string) {
  const { data } = await request.get<Member[]>('/sales/members/search', {
    params: { keyword }
  });
  return data;
}

export async function fetchPromotions() {
  const { data } = await request.get<Promotion[]>('/promotions');
  return data;
}

export async function fetchRecentOrders() {
  const { data } = await request.get<SalesOrder[]>('/sales/orders/recent', {
    params: { limit: 8 }
  });
  return data;
}

export async function createSalesOrder(payload: CreateOrderPayload) {
  const { data } = await request.post<SalesOrder>('/sales/orders', payload);
  return data;
}
