import request from './request';

export interface DashboardSummary {
  sales_amount: number;
  order_count: number;
  average_order_value: number;
  member_sales_ratio: number;
  low_stock_sku_count: number;
  inventory_turnover_days: number;
  gross_profit: number;
}

export interface CategorySales {
  category: string;
  sales_amount: number;
}

export interface LowStockItem {
  id: number;
  quantity: number;
  safety_stock: number;
  in_transit: number;
  store?: {
    name: string;
    city: string;
  };
  sku?: {
    sku_code: string;
    color: string;
    size: string;
    product?: {
      name: string;
      category: string;
    };
  };
}

export interface DashboardData {
  summary: DashboardSummary;
  category_sales: CategorySales[];
  low_stock_items: LowStockItem[];
}

export async function fetchDashboard() {
  const { data } = await request.get<DashboardData>('/dashboard/summary');
  return data;
}
