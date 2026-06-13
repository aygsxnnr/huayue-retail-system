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


class StoreCreate(BaseModel):
    code: str
    name: str
    city: str = ""
    address: str = ""
    manager: str = ""
    status: str = "正常营业"


class StoreUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    city: str | None = None
    address: str | None = None
    manager: str | None = None
    status: str | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    category: str
    season: str
    brand: str
    status: str
    launch_date: date
    lifecycle_status: str
    sale_price: float = 0
    list_price: float = 0
    cost_price: float = 0


class ProductCreate(BaseModel):
    code: str | None = None
    name: str
    category: str
    season: str
    brand: str = "华悦"
    status: str = "在售"
    launch_date: date | None = None
    lifecycle_status: str = "新品"
    sale_price: float = Field(default=0, ge=0)
    cost_price: float = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    category: str | None = None
    season: str | None = None
    brand: str | None = None
    status: str | None = None
    launch_date: date | None = None
    lifecycle_status: str | None = None
    sale_price: float | None = Field(default=None, ge=0)
    cost_price: float | None = Field(default=None, ge=0)


class StatusUpdate(BaseModel):
    status: str


class MemberStatusUpdate(BaseModel):
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
    status: str
    product: ProductOut | None = None
    product_code: str = ""
    main_color_code: str = ""
    sub_color_code: str = ""
    size_code: str = ""
    is_standard_code: bool = False
    created_inventory_count: int = 0


class SKUCodePreviewRequest(BaseModel):
    product_id: int
    color: str
    size: str


class SKUCodePreviewOut(BaseModel):
    product_code: str
    main_color_code: str
    sub_color_code: str
    size_code: str
    sku_code: str
    barcode: str
    color_match_note: str
    size_match_note: str
    duplicate_sku: bool = False


class SKUCreate(BaseModel):
    product_id: int
    sku_code: str | None = None
    code: str | None = None
    color: str
    size: str
    barcode: str | None = None
    list_price: float | None = Field(default=None, gt=0)
    sale_price: float | None = Field(default=None, gt=0)
    price: float | None = Field(default=None, gt=0)
    cost_price: float | None = Field(default=None, ge=0)
    status: str = "启用"


class SKUUpdate(BaseModel):
    sku_code: str | None = None
    code: str | None = None
    color: str | None = None
    size: str | None = None
    barcode: str | None = None
    list_price: float | None = Field(default=None, gt=0)
    sale_price: float | None = Field(default=None, gt=0)
    price: float | None = Field(default=None, gt=0)
    cost_price: float | None = Field(default=None, ge=0)
    status: str | None = None


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
    applicable_scope: str
    approval_status: str


class PromotionCreate(BaseModel):
    name: str
    promotion_type: str
    discount_rate: float = Field(default=1.0, ge=0, le=1)
    start_date: date
    end_date: date
    status: str = "未开始"
    description: str = ""
    applicable_scope: str = "全部商品"
    approval_status: str = "已审批"


class PromotionUpdate(BaseModel):
    name: str | None = None
    promotion_type: str | None = None
    discount_rate: float | None = Field(default=None, ge=0, le=1)
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    description: str | None = None
    applicable_scope: str | None = None
    approval_status: str | None = None


class CouponOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    coupon_type: str
    promotion_id: int | None
    discount_amount: float
    discount_rate: float
    threshold_amount: float
    valid_start: date
    valid_end: date
    target_group: str
    issued_count: int
    used_count: int
    status: str
    created_at: datetime
    per_member_limit: int | None = None
    per_order_use_limit: int | None = None
    stackable: bool = False
    total_issue_limit: int | None = None
    total_redeem_limit: int | None = None
    applicable_category_ids: str = ""
    applicable_product_ids: str = ""
    applicable_seasons: str = ""
    applicable_member_levels: str = ""
    applicable_member_groups: str = ""
    applicable_store_ids: str = ""
    target_tags: str = ""
    issue_mode: str = "手动发放"
    auto_issue_enabled: bool = False
    promotion: PromotionOut | None = None


class CouponCreate(BaseModel):
    code: str | None = None
    name: str
    coupon_type: str
    promotion_id: int | None = None
    discount_amount: float = Field(default=0, ge=0)
    discount_rate: float = Field(default=1.0, ge=0, le=1)
    threshold_amount: float = Field(default=0, ge=0)
    valid_start: date
    valid_end: date
    target_group: str = "全部会员"
    issued_count: int = Field(default=0, ge=0)
    used_count: int = Field(default=0, ge=0)
    status: str = "可用"
    per_member_limit: int | None = Field(default=None, ge=0)
    per_order_use_limit: int | None = Field(default=None, ge=0)
    stackable: bool = False
    total_issue_limit: int | None = Field(default=None, ge=0)
    total_redeem_limit: int | None = Field(default=None, ge=0)
    applicable_category_ids: str = ""
    applicable_product_ids: str = ""
    applicable_seasons: str = ""
    applicable_member_levels: str = ""
    applicable_member_groups: str = ""
    applicable_store_ids: str = ""
    target_tags: str = ""
    issue_mode: str = "手动发放"
    auto_issue_enabled: bool = False


class CouponUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    coupon_type: str | None = None
    promotion_id: int | None = None
    discount_amount: float | None = Field(default=None, ge=0)
    discount_rate: float | None = Field(default=None, ge=0, le=1)
    threshold_amount: float | None = Field(default=None, ge=0)
    valid_start: date | None = None
    valid_end: date | None = None
    target_group: str | None = None
    issued_count: int | None = Field(default=None, ge=0)
    used_count: int | None = Field(default=None, ge=0)
    status: str | None = None
    per_member_limit: int | None = Field(default=None, ge=0)
    per_order_use_limit: int | None = Field(default=None, ge=0)
    stackable: bool | None = None
    total_issue_limit: int | None = Field(default=None, ge=0)
    total_redeem_limit: int | None = Field(default=None, ge=0)
    applicable_category_ids: str | None = None
    applicable_product_ids: str | None = None
    applicable_seasons: str | None = None
    applicable_member_levels: str | None = None
    applicable_member_groups: str | None = None
    applicable_store_ids: str | None = None
    target_tags: str | None = None
    issue_mode: str | None = None
    auto_issue_enabled: bool | None = None


class CouponMatchConditions(BaseModel):
    member_levels: list[str] = Field(default_factory=list)
    member_groups: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    store_ids: list[int] = Field(default_factory=list)
    member_statuses: list[str] = Field(default_factory=list)
    account_statuses: list[str] = Field(default_factory=list)
    lifecycle_statuses: list[str] = Field(default_factory=list)
    recent_purchase_start: date | None = None
    recent_purchase_end: date | None = None
    min_total_spent: float | None = Field(default=None, ge=0)
    max_total_spent: float | None = Field(default=None, ge=0)
    min_points: int | None = Field(default=None, ge=0)
    max_points: int | None = Field(default=None, ge=0)
    # Backward compatibility only. These are normalized to lifecycle_statuses in crud.
    is_new_member: bool | None = None
    is_sleeping_member: bool | None = None
    is_churn_risk: bool | None = None


class CouponMatchRequest(BaseModel):
    extra_member_ids: list[int] = Field(default_factory=list)
    exclude_member_ids: list[int] = Field(default_factory=list)
    conditions: CouponMatchConditions = Field(default_factory=CouponMatchConditions)


class MatchedCouponMemberOut(BaseModel):
    id: int
    name: str
    phone: str
    level: str
    member_group: str = "-"
    registered_store: str = "-"
    registered_store_text: str = "-"
    registered_store_names: list[str] = Field(default_factory=list)
    account_status: str = "-"
    lifecycle_status: str = "-"
    last_purchase_at: datetime | None = None
    match_reason: str = "-"


class CouponCodeOut(BaseModel):
    code: str


class CouponMatchOut(BaseModel):
    matched_count: int
    matched_members: list[MatchedCouponMemberOut]


class CouponIssueRequest(BaseModel):
    member_ids: list[int] = Field(min_length=1)
    channels: list[str] = Field(min_length=1)
    remark: str = "优惠券一键匹配发放"


class CouponIssueFailedItem(BaseModel):
    member_id: int
    reason: str


class CouponIssueOut(BaseModel):
    created_count: int
    skipped_count: int
    failed_items: list[CouponIssueFailedItem] = Field(default_factory=list)


class MemberCreate(BaseModel):
    name: str
    phone: str
    level: str = "普通会员"
    tags: str = ""
    points: int = Field(default=0, ge=0)
    total_spent: float = Field(default=0, ge=0)
    total_orders: int = Field(default=0, ge=0)
    status: str = "正常"
    registered_store: str = "华悦线上会员中心"


class MemberUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    level: str | None = None
    tags: str | None = None
    points: int | None = Field(default=None, ge=0)
    total_spent: float | None = Field(default=None, ge=0)
    total_orders: int | None = Field(default=None, ge=0)
    status: str | None = None
    registered_store: str | None = None


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
    total_orders: int = 0
    last_purchase_at: datetime | None = None
    current_points: int = 0
    total_amount: float = 0
    last_purchase_date: datetime | None = None
    status: str = "正常"
    registered_store: str = "华悦线上会员中心"
    joined_at: datetime


class MemberTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    r_score: int
    f_score: int
    m_score: int
    member_group: str
    preference_tag: str
    price_sensitive_tag: str
    activity_tag: str
    risk_tag: str
    updated_at: datetime
    member: MemberOut | None = None


class MemberProfileOut(BaseModel):
    member: MemberOut
    tag_profile: MemberTagOut | None = None
    recent_products: list[str] = Field(default_factory=list)
    preferred_categories: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class RFMOut(BaseModel):
    member_id: int
    member_no: str
    name: str
    r_score: int
    f_score: int
    m_score: int
    member_group: str
    main_tags: list[str] = Field(default_factory=list)
    strategy: str


class MarketingTouchCreate(BaseModel):
    member_id: int
    coupon_id: int | None = None
    promotion_id: int | None = None
    channel: str = "微信"
    participation_status: str = "未参与"
    writeoff_status: str = "未核销"
    remark: str = ""


class MarketingTouchBatchCreate(BaseModel):
    member_ids: list[int] = Field(min_length=1)
    coupon_ids: list[int] = Field(min_length=1)
    channels: list[str] = Field(min_length=1)
    remark: str = "手动发放"


class MarketingTouchBatchOut(BaseModel):
    created_count: int
    skipped_count: int


class MarketingTouchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    coupon_id: int | None = None
    promotion_id: int | None = None
    channel: str
    touch_time: datetime
    participation_status: str
    writeoff_status: str
    remark: str
    member: MemberOut | None = None
    coupon: CouponOut | None = None
    promotion: PromotionOut | None = None


class RepurchaseRankOut(BaseModel):
    rank: int
    member_id: int
    member_no: str
    name: str
    total_orders: int
    total_spent: float
    last_purchase_at: datetime | None = None
    level: str
    repurchase_tag: str


class LevelDistributionOut(BaseModel):
    level: str
    count: int


class MarketingEffectOut(BaseModel):
    name: str
    touched_count: int
    clicked_count: int
    participated_count: int
    writeoff_count: int
    writeoff_rate: float
    driven_sales_amount: float


class RepurchaseAnalysisOut(BaseModel):
    repurchase_ranking: list[RepurchaseRankOut]
    level_distribution: list[LevelDistributionOut]
    lifecycle_distribution: list[LevelDistributionOut] = Field(default_factory=list)
    marketing_effects: list[MarketingEffectOut]


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
    recent_7d_sales: int = 0
    suggested_qty: int = 0
    inventory_status: str = "正常"


class InventorySafetyStockUpdate(BaseModel):
    safety_stock: int = Field(ge=0)


class ReplenishmentCreate(BaseModel):
    inventory_id: int
    request_qty: int = Field(gt=0)
    reason: str = ""
    applicant: str = "门店店长"


class ReplenishmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    inventory_id: int
    store_id: int
    sku_id: int
    current_quantity: int
    safety_stock: int
    in_transit: int
    recent_7d_sales: int
    suggested_qty: int
    request_qty: int
    reason: str
    applicant: str
    status: str
    created_at: datetime
    updated_at: datetime
    store: StoreOut | None = None
    sku: SKUOut | None = None


class TransferCreate(BaseModel):
    request_id: int
    transfer_qty: int | None = Field(default=None, gt=0)
    source_location: str = "华悦中央仓"


class TransferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    inventory_id: int
    store_id: int
    sku_id: int
    source_location: str
    transfer_qty: int
    in_transit_qty: int
    status: str
    shipped_at: datetime | None = None
    expected_arrival_at: datetime | None = None
    arrived_at: datetime | None = None
    request: ReplenishmentOut | None = None
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
    unit_cost: float = 0
    discount_amount: float
    subtotal: float
    cost_amount: float = 0
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


class FinanceSummaryOut(BaseModel):
    today_order_amount: float
    today_payment_amount: float
    today_difference_amount: float
    pending_difference_count: int
    settled_count: int
    gross_profit: float
    gross_profit_rate: float
    promotion_discount_amount: float


class FinanceRecordViewOut(BaseModel):
    id: int
    record_no: str
    order_no: str
    store_name: str
    cashier_name: str
    order_amount: float
    payment_amount: float
    discount_amount: float
    difference_amount: float
    payment_method: str
    status: str
    reconciliation_time: date


class FinanceBatchResolveIn(BaseModel):
    record_ids: list[int]


class FinanceBatchReconcileIn(BaseModel):
    record_ids: list[int]


class FinanceBatchResolveFailedItem(BaseModel):
    id: int
    reason: str


class FinanceBatchResolveOut(BaseModel):
    success_count: int
    failed_count: int
    failed_items: list[FinanceBatchResolveFailedItem]


class FinanceBatchReconcileOut(BaseModel):
    success_count: int
    failed_count: int
    failed_items: list[FinanceBatchResolveFailedItem]


class PaymentRecordViewOut(BaseModel):
    id: int
    payment_no: str
    order_no: str
    store_name: str
    payment_method: str
    payable_amount: float
    paid_amount: float
    payment_status: str
    payment_time: datetime
    third_party_no: str
    cashier_name: str = "-"
    finance_record_no: str = "-"
    difference_amount: float = 0
    remark: str = "-"


class FinanceTrendPoint(BaseModel):
    date: str
    order_amount: float = 0
    payment_amount: float = 0
    difference_amount: float = 0
    sales_amount: float = 0
    cost_amount: float = 0
    gross_profit: float = 0


class ProductProfitRankOut(BaseModel):
    rank: int
    product_name: str
    sku_code: str
    sales_quantity: int
    sales_amount: float
    cost_amount: float
    gross_profit: float
    gross_profit_rate: float


class CategoryProfitOut(BaseModel):
    category: str
    sales_amount: float
    cost_amount: float
    gross_profit: float
    gross_profit_rate: float


class ProfitTrendOut(BaseModel):
    trend: list[FinanceTrendPoint]
    product_profit_rank: list[ProductProfitRankOut]
    category_profit: list[CategoryProfitOut]


class PromotionLossOut(BaseModel):
    promotion_id: int
    promotion_code: str
    promotion_name: str
    promotion_type: str
    order_count: int
    original_amount: float
    discount_amount: float
    paid_amount: float
    cost_amount: float
    gross_profit: float
    gross_profit_rate: float
    status: str


class StoreSettlementOut(BaseModel):
    store_id: int
    store_name: str
    sales_amount: float
    order_count: int
    average_order_value: float
    cost_amount: float
    gross_profit: float
    gross_profit_rate: float
    promotion_discount_amount: float
    difference_amount: float
    settlement_status: str


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


class UserBase(BaseModel):
    username: str
    real_name: str
    role: str
    store_id: int | None = None
    status: str = "启用"


class UserCreate(UserBase):
    password: str = "123456"


class UserUpdate(BaseModel):
    real_name: str | None = None
    role: str | None = None
    store_id: int | None = None
    status: str | None = None
    password: str | None = None


class UserStatusUpdate(BaseModel):
    status: str


class UserOut(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class CurrentUserResponse(BaseModel):
    user: UserOut


class RoleOut(BaseModel):
    label: str
    value: str
    menus: list[str] = []


class OperationLogOut(BaseModel):
    id: int
    operator_id: int | None = None
    operator_name: str
    role: str
    module: str
    action: str
    target_type: str
    target_id: str
    before_data: str
    after_data: str
    created_at: datetime
    remark: str

    model_config = ConfigDict(from_attributes=True)
