from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .utils.code_generator import parse_sku_code


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    city: Mapped[str] = mapped_column(String(50))
    address: Mapped[str] = mapped_column(String(200))
    manager: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="营业中")

    inventories = relationship("Inventory", back_populates="store")
    orders = relationship("SalesOrder", back_populates="store")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    season: Mapped[str] = mapped_column(String(20))
    brand: Mapped[str] = mapped_column(String(50), default="华悦")
    status: Mapped[str] = mapped_column(String(20), default="在售")
    launch_date: Mapped[date] = mapped_column(Date, default=date.today)
    lifecycle_status: Mapped[str] = mapped_column(String(20), default="新品")

    skus = relationship("SKU", back_populates="product")

    @property
    def list_price(self) -> float:
        prices = [sku.list_price for sku in self.skus]
        return min(prices) if prices else 0

    @property
    def cost_price(self) -> float:
        prices = [sku.cost_price for sku in self.skus]
        return min(prices) if prices else 0


class SKU(Base):
    __tablename__ = "skus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sku_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    color: Mapped[str] = mapped_column(String(30))
    size: Mapped[str] = mapped_column(String(20))
    list_price: Mapped[float] = mapped_column(Float)
    cost_price: Mapped[float] = mapped_column(Float)
    barcode: Mapped[str] = mapped_column(String(60), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="在售")

    product = relationship("Product", back_populates="skus")
    inventories = relationship("Inventory", back_populates="sku")
    order_items = relationship("SalesOrderItem", back_populates="sku")

    @property
    def product_code(self) -> str:
        return parse_sku_code(self.sku_code).product_code

    @property
    def main_color_code(self) -> str:
        return parse_sku_code(self.sku_code).main_color_code

    @property
    def sub_color_code(self) -> str:
        return parse_sku_code(self.sku_code).sub_color_code

    @property
    def size_code(self) -> str:
        return parse_sku_code(self.sku_code).size_code

    @property
    def is_standard_code(self) -> bool:
        return parse_sku_code(self.sku_code).is_valid


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    promotion_type: Mapped[str] = mapped_column(String(30))
    discount_rate: Mapped[float] = mapped_column(Float, default=1.0)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="进行中")
    description: Mapped[str] = mapped_column(Text, default="")
    applicable_scope: Mapped[str] = mapped_column(String(100), default="全部商品")
    approval_status: Mapped[str] = mapped_column(String(20), default="已审批")

    orders = relationship("SalesOrder", back_populates="promotion")
    coupons = relationship("Coupon", back_populates="promotion")


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    coupon_type: Mapped[str] = mapped_column(String(30))
    promotion_id: Mapped[int | None] = mapped_column(ForeignKey("promotions.id"), nullable=True)
    discount_amount: Mapped[float] = mapped_column(Float, default=0)
    discount_rate: Mapped[float] = mapped_column(Float, default=1.0)
    threshold_amount: Mapped[float] = mapped_column(Float, default=0)
    valid_start: Mapped[date] = mapped_column(Date)
    valid_end: Mapped[date] = mapped_column(Date)
    target_group: Mapped[str] = mapped_column(String(100), default="全部会员")
    issued_count: Mapped[int] = mapped_column(Integer, default=0)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="可用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    promotion = relationship("Promotion", back_populates="coupons")
    marketing_touches = relationship("MarketingTouch", back_populates="coupon")


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    member_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(50), index=True)
    phone: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    level: Mapped[str] = mapped_column(String(20), default="普通会员")
    tags: Mapped[str] = mapped_column(String(200), default="")
    points: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[float] = mapped_column(Float, default=0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    last_purchase_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="正常")
    registered_store: Mapped[str] = mapped_column(String(100), default="华悦线上会员中心")
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    orders = relationship("SalesOrder", back_populates="member")
    tag_profile = relationship("MemberTag", back_populates="member", uselist=False, cascade="all, delete-orphan")
    marketing_touches = relationship("MarketingTouch", back_populates="member", cascade="all, delete-orphan")

    @property
    def member_tags(self) -> list[str]:
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]

    @property
    def available_coupons(self) -> list[str]:
        coupons = ["满299减40券"]
        if self.level in {"银卡会员", "金卡会员"}:
            coupons.append("会员专享9折券")
        if self.points >= 800:
            coupons.append("积分兑换20元券")
        return coupons

    @property
    def current_points(self) -> int:
        return self.points

    @property
    def total_amount(self) -> float:
        return self.total_spent

    @property
    def last_purchase_date(self) -> datetime | None:
        return self.last_purchase_at


class MemberTag(Base):
    __tablename__ = "member_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), unique=True, index=True)
    r_score: Mapped[int] = mapped_column(Integer, default=3)
    f_score: Mapped[int] = mapped_column(Integer, default=3)
    m_score: Mapped[int] = mapped_column(Integer, default=3)
    member_group: Mapped[str] = mapped_column(String(50), default="潜力会员")
    preference_tag: Mapped[str] = mapped_column(String(80), default="新品敏感")
    price_sensitive_tag: Mapped[str] = mapped_column(String(80), default="价格适中")
    activity_tag: Mapped[str] = mapped_column(String(80), default="普通活跃")
    risk_tag: Mapped[str] = mapped_column(String(80), default="稳定")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    member = relationship("Member", back_populates="tag_profile")


class MarketingTouch(Base):
    __tablename__ = "marketing_touches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    coupon_id: Mapped[int | None] = mapped_column(ForeignKey("coupons.id"), nullable=True)
    promotion_id: Mapped[int | None] = mapped_column(ForeignKey("promotions.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(30), default="微信")
    touch_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    participation_status: Mapped[str] = mapped_column(String(30), default="未参与")
    writeoff_status: Mapped[str] = mapped_column(String(30), default="未核销")
    remark: Mapped[str] = mapped_column(Text, default="")

    member = relationship("Member", back_populates="marketing_touches")
    coupon = relationship("Coupon", back_populates="marketing_touches")
    promotion = relationship("Promotion")


class Inventory(Base):
    __tablename__ = "inventories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    safety_stock: Mapped[int] = mapped_column(Integer, default=5)
    in_transit: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    store = relationship("Store", back_populates="inventories")
    sku = relationship("SKU", back_populates="inventories")
    replenishment_requests = relationship("ReplenishmentRequest", back_populates="inventory")
    transfer_records = relationship("TransferRecord", back_populates="inventory")


class ReplenishmentRequest(Base):
    __tablename__ = "replenishment_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id"))
    current_quantity: Mapped[int] = mapped_column(Integer, default=0)
    safety_stock: Mapped[int] = mapped_column(Integer, default=0)
    in_transit: Mapped[int] = mapped_column(Integer, default=0)
    recent_7d_sales: Mapped[int] = mapped_column(Integer, default=0)
    suggested_qty: Mapped[int] = mapped_column(Integer, default=0)
    request_qty: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text, default="")
    applicant: Mapped[str] = mapped_column(String(50), default="门店店长")
    status: Mapped[str] = mapped_column(String(20), default="待审核")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    inventory = relationship("Inventory", back_populates="replenishment_requests")
    store = relationship("Store")
    sku = relationship("SKU")
    transfer_records = relationship("TransferRecord", back_populates="request")


class TransferRecord(Base):
    __tablename__ = "transfer_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("replenishment_requests.id"))
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id"))
    source_location: Mapped[str] = mapped_column(String(100), default="华悦中央仓")
    transfer_qty: Mapped[int] = mapped_column(Integer)
    in_transit_qty: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="在途")
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expected_arrival_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    request = relationship("ReplenishmentRequest", back_populates="transfer_records")
    inventory = relationship("Inventory", back_populates="transfer_records")
    store = relationship("Store")
    sku = relationship("SKU")


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id"), nullable=True)
    promotion_id: Mapped[int | None] = mapped_column(ForeignKey("promotions.id"), nullable=True)
    order_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    total_amount: Mapped[float] = mapped_column(Float, default=0)
    discount_amount: Mapped[float] = mapped_column(Float, default=0)
    paid_amount: Mapped[float] = mapped_column(Float, default=0)
    payment_method: Mapped[str] = mapped_column(String(30), default="模拟支付")
    status: Mapped[str] = mapped_column(String(20), default="已完成")

    store = relationship("Store", back_populates="orders")
    member = relationship("Member", back_populates="orders")
    promotion = relationship("Promotion", back_populates="orders")
    items = relationship("SalesOrderItem", back_populates="order", cascade="all, delete-orphan")
    payment = relationship("PaymentRecord", back_populates="order", uselist=False)
    finance_record = relationship("FinanceRecord", back_populates="order", uselist=False)


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    discount_amount: Mapped[float] = mapped_column(Float, default=0)
    subtotal: Mapped[float] = mapped_column(Float)

    order = relationship("SalesOrder", back_populates="items")
    sku = relationship("SKU", back_populates="order_items")


class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    amount: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(30))
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(20), default="支付成功")

    order = relationship("SalesOrder", back_populates="payment")


class FinanceRecord(Base):
    __tablename__ = "finance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    record_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    sales_amount: Mapped[float] = mapped_column(Float)
    cost_amount: Mapped[float] = mapped_column(Float)
    gross_profit: Mapped[float] = mapped_column(Float)
    promotion_loss: Mapped[float] = mapped_column(Float, default=0)
    reconcile_status: Mapped[str] = mapped_column(String(20), default="已对账")
    business_date: Mapped[date] = mapped_column(Date, default=date.today)

    order = relationship("SalesOrder", back_populates="finance_record")
    store = relationship("Store")
