from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


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

    skus = relationship("SKU", back_populates="product")


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

    product = relationship("Product", back_populates="skus")
    inventories = relationship("Inventory", back_populates="sku")
    order_items = relationship("SalesOrderItem", back_populates="sku")


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

    orders = relationship("SalesOrder", back_populates="promotion")


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
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    orders = relationship("SalesOrder", back_populates="member")

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
