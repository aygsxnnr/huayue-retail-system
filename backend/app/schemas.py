from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    city: str
    address: str
    manager: str
    status: str


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    category: str
    season: str
    brand: str
    status: str


class SKUOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku_code: str
    product_id: int
    color: str
    size: str
    list_price: float
    cost_price: float
    barcode: str
    product: ProductOut | None = None


class PromotionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    promotion_type: str
    discount_rate: float
    start_date: date
    end_date: date
    status: str
    description: str


class MemberCreate(BaseModel):
    name: str
    phone: str
    level: str = "普通会员"
    tags: str = ""


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_no: str
    name: str
    phone: str
    level: str
    tags: str
    member_tags: list[str] = Field(default_factory=list)
    available_coupons: list[str] = Field(default_factory=list)
    points: int
    total_spent: float
    joined_at: datetime


class InventoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    sku_id: int
    quantity: int
    safety_stock: int
    in_transit: int
    updated_at: datetime
    store: StoreOut | None = None
    sku: SKUOut | None = None


class POSSkuOut(BaseModel):
    sku_id: int
    sku_code: str
    barcode: str
    product_name: str
    category: str
    color: str
    size: str
    list_price: float
    cost_price: float
    store_id: int
    store_name: str
    inventory_quantity: int
    safety_stock: int


class OrderItemCreate(BaseModel):
    sku_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    store_id: int
    member_id: int | None = None
    promotion_id: int | None = None
    payment_method: str = "模拟支付"
    items: list[OrderItemCreate]


class SalesOrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku_id: int
    quantity: int
    unit_price: float
    discount_amount: float
    subtotal: float
    sku: SKUOut | None = None


class SalesOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    store_id: int
    member_id: int | None
    promotion_id: int | None
    order_time: datetime
    total_amount: float
    discount_amount: float
    paid_amount: float
    payment_method: str
    status: str
    items: list[SalesOrderItemOut] = []


class PaymentRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_no: str
    order_id: int
    amount: float
    method: str
    paid_at: datetime
    status: str


class FinanceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_no: str
    order_id: int
    store_id: int
    sales_amount: float
    cost_amount: float
    gross_profit: float
    promotion_loss: float
    reconcile_status: str
    business_date: date


class DashboardSummary(BaseModel):
    sales_amount: float
    order_count: int
    average_order_value: float
    member_sales_ratio: float
    low_stock_sku_count: int
    inventory_turnover_days: float
    gross_profit: float


class CategorySales(BaseModel):
    category: str
    sales_amount: float


class DashboardOut(BaseModel):
    summary: DashboardSummary
    category_sales: list[CategorySales]
    low_stock_items: list[InventoryOut]
