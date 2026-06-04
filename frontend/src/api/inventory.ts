import request from './request';

export interface InventoryItem {
  id: number;
  store_id: number;
  sku_id: number;
  quantity: number;
  safety_stock: number;
  in_transit: number;
  updated_at: string;
  recent_7d_sales: number;
  suggested_qty: number;
  inventory_status: '正常' | '低库存' | '缺货预警' | '待补货';
  store?: {
    id: number;
    code: string;
    name: string;
    city: string;
    address: string;
    manager: string;
    status: string;
  };
  sku?: {
    id: number;
    sku_code: string;
    color: string;
    size: string;
    list_price: number;
    cost_price: number;
    barcode: string;
    product?: {
      id: number;
      code: string;
      name: string;
      category: string;
      season: string;
      brand: string;
      status: string;
    };
  };
}

export interface ReplenishmentRequest {
  id: number;
  inventory_id: number;
  store_id: number;
  sku_id: number;
  current_quantity: number;
  safety_stock: number;
  in_transit: number;
  recent_7d_sales: number;
  suggested_qty: number;
  request_qty: number;
  reason: string;
  applicant: string;
  status: '待审核' | '已审核' | '已驳回' | '待调拨' | '在途' | '已完成';
  created_at: string;
  updated_at: string;
  store?: InventoryItem['store'];
  sku?: InventoryItem['sku'];
}

export interface TransferRecord {
  id: number;
  request_id: number;
  inventory_id: number;
  store_id: number;
  sku_id: number;
  source_location: string;
  transfer_qty: number;
  in_transit_qty: number;
  status: '未发货' | '在途' | '已到货' | '异常';
  shipped_at?: string | null;
  expected_arrival_at?: string | null;
  arrived_at?: string | null;
  request?: ReplenishmentRequest;
  store?: InventoryItem['store'];
  sku?: InventoryItem['sku'];
}

export interface CreateReplenishmentPayload {
  inventory_id: number;
  request_qty: number;
  reason: string;
  applicant?: string;
}

export interface CreateTransferPayload {
  request_id: number;
  source_location?: string;
  transfer_qty?: number;
}

export async function fetchInventory() {
  const { data } = await request.get<InventoryItem[]>('/inventory');
  return data;
}

export async function fetchLowStockInventory() {
  const { data } = await request.get<InventoryItem[]>('/inventory/low-stock');
  return data;
}

export async function fetchReplenishments() {
  const { data } = await request.get<ReplenishmentRequest[]>('/inventory/replenishments');
  return data;
}

export async function createReplenishment(payload: CreateReplenishmentPayload) {
  const { data } = await request.post<ReplenishmentRequest>('/inventory/replenishments', payload);
  return data;
}

export async function approveReplenishment(id: number) {
  const { data } = await request.put<ReplenishmentRequest>(`/inventory/replenishments/${id}/approve`);
  return data;
}

export async function rejectReplenishment(id: number) {
  const { data } = await request.put<ReplenishmentRequest>(`/inventory/replenishments/${id}/reject`);
  return data;
}

export async function fetchTransfers() {
  const { data } = await request.get<TransferRecord[]>('/inventory/transfers');
  return data;
}

export async function createTransfer(payload: CreateTransferPayload) {
  const { data } = await request.post<TransferRecord>('/inventory/transfers', payload);
  return data;
}

export async function markTransferArrival(id: number) {
  const { data } = await request.put<TransferRecord>(`/inventory/transfers/${id}/arrival`);
  return data;
}
