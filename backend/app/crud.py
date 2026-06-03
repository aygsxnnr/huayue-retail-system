from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from . import models, schemas


def list_stores(db: Session) -> list[models.Store]:
    return db.query(models.Store).order_by(models.Store.id).all()


def list_products(db: Session) -> list[models.Product]:
    return db.query(models.Product).order_by(models.Product.id).all()


def list_skus(db: Session) -> list[models.SKU]:
    return db.query(models.SKU).options(joinedload(models.SKU.product)).order_by(models.SKU.id).all()


def list_promotions(db: Session) -> list[models.Promotion]:
    return db.query(models.Promotion).order_by(models.Promotion.id).all()


def list_members(db: Session) -> list[models.Member]:
    return db.query(models.Member).order_by(models.Member.id).all()


def create_member(db: Session, payload: schemas.MemberCreate) -> models.Member:
    existing = db.query(models.Member).filter(models.Member.phone == payload.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="手机号已存在")

    member = models.Member(
        member_no=f"HY{datetime.utcnow():%Y%m%d}{uuid4().hex[:6].upper()}",
        name=payload.name,
        phone=payload.phone,
        level=payload.level,
        tags=payload.tags,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def list_inventory(db: Session) -> list[models.Inventory]:
    return (
        db.query(models.Inventory)
        .options(
            joinedload(models.Inventory.store),
            joinedload(models.Inventory.sku).joinedload(models.SKU.product),
        )
        .order_by(models.Inventory.store_id, models.Inventory.sku_id)
        .all()
    )


def list_low_stock(db: Session) -> list[models.Inventory]:
    return (
        db.query(models.Inventory)
        .options(
            joinedload(models.Inventory.store),
            joinedload(models.Inventory.sku).joinedload(models.SKU.product),
        )
        .filter(models.Inventory.quantity <= models.Inventory.safety_stock)
        .order_by(models.Inventory.quantity)
        .all()
    )


def list_orders(db: Session) -> list[models.SalesOrder]:
    return (
        db.query(models.SalesOrder)
        .options(joinedload(models.SalesOrder.items).joinedload(models.SalesOrderItem.sku))
        .order_by(models.SalesOrder.order_time.desc())
        .all()
    )


def create_order(db: Session, payload: schemas.OrderCreate) -> models.SalesOrder:
    if not payload.items:
        raise HTTPException(status_code=400, detail="订单明细不能为空")

    store = db.get(models.Store, payload.store_id)
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")

    member = db.get(models.Member, payload.member_id) if payload.member_id else None
    if payload.member_id and not member:
        raise HTTPException(status_code=404, detail="会员不存在")

    promotion = db.get(models.Promotion, payload.promotion_id) if payload.promotion_id else None
    if payload.promotion_id and not promotion:
        raise HTTPException(status_code=404, detail="促销活动不存在")

    discount_rate = promotion.discount_rate if promotion else 1.0
    order = models.SalesOrder(
        order_no=f"SO{datetime.utcnow():%Y%m%d%H%M%S}{uuid4().hex[:4].upper()}",
        store_id=payload.store_id,
        member_id=payload.member_id,
        promotion_id=payload.promotion_id,
        payment_method=payload.payment_method,
    )
    db.add(order)
    db.flush()

    total_amount = 0.0
    discount_amount = 0.0
    cost_amount = 0.0

    for item in payload.items:
        sku = db.get(models.SKU, item.sku_id)
        if not sku:
            raise HTTPException(status_code=404, detail=f"SKU {item.sku_id} 不存在")

        inventory = (
            db.query(models.Inventory)
            .filter(
                models.Inventory.store_id == payload.store_id,
                models.Inventory.sku_id == item.sku_id,
            )
            .first()
        )
        if not inventory or inventory.quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"SKU {sku.sku_code} 库存不足")

        line_total = sku.list_price * item.quantity
        line_paid = round(line_total * discount_rate, 2)
        line_discount = round(line_total - line_paid, 2)
        db.add(
            models.SalesOrderItem(
                order_id=order.id,
                sku_id=item.sku_id,
                quantity=item.quantity,
                unit_price=sku.list_price,
                discount_amount=line_discount,
                subtotal=line_paid,
            )
        )
        inventory.quantity -= item.quantity
        inventory.updated_at = datetime.utcnow()
        total_amount += line_total
        discount_amount += line_discount
        cost_amount += sku.cost_price * item.quantity

    paid_amount = round(total_amount - discount_amount, 2)
    order.total_amount = round(total_amount, 2)
    order.discount_amount = round(discount_amount, 2)
    order.paid_amount = paid_amount

    db.add(
        models.PaymentRecord(
            payment_no=f"PAY{datetime.utcnow():%Y%m%d%H%M%S}{uuid4().hex[:4].upper()}",
            order_id=order.id,
            amount=paid_amount,
            method=payload.payment_method,
        )
    )
    db.add(
        models.FinanceRecord(
            record_no=f"FIN{datetime.utcnow():%Y%m%d%H%M%S}{uuid4().hex[:4].upper()}",
            order_id=order.id,
            store_id=payload.store_id,
            sales_amount=paid_amount,
            cost_amount=round(cost_amount, 2),
            gross_profit=round(paid_amount - cost_amount, 2),
            promotion_loss=round(discount_amount, 2),
        )
    )

    if member:
        member.total_spent = round(member.total_spent + paid_amount, 2)
        member.points += int(paid_amount)

    db.commit()
    return (
        db.query(models.SalesOrder)
        .options(joinedload(models.SalesOrder.items).joinedload(models.SalesOrderItem.sku))
        .filter(models.SalesOrder.id == order.id)
        .one()
    )


def list_finance_records(db: Session) -> list[models.FinanceRecord]:
    return db.query(models.FinanceRecord).order_by(models.FinanceRecord.business_date.desc()).all()


def finance_summary(db: Session) -> dict:
    row = db.query(
        func.coalesce(func.sum(models.FinanceRecord.sales_amount), 0),
        func.coalesce(func.sum(models.FinanceRecord.cost_amount), 0),
        func.coalesce(func.sum(models.FinanceRecord.gross_profit), 0),
        func.coalesce(func.sum(models.FinanceRecord.promotion_loss), 0),
    ).one()
    return {
        "销售额": round(row[0], 2),
        "成本": round(row[1], 2),
        "毛利": round(row[2], 2),
        "促销让利": round(row[3], 2),
    }
