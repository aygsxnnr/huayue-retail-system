from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from . import models, schemas


def list_stores(db: Session) -> list[models.Store]:
    return db.query(models.Store).order_by(models.Store.id).all()


def list_products(db: Session) -> list[models.Product]:
    return db.query(models.Product).order_by(models.Product.id).all()


def list_skus(db: Session) -> list[models.SKU]:
    return db.query(models.SKU).options(joinedload(models.SKU.product)).order_by(models.SKU.id).all()


def search_pos_skus(db: Session, store_id: int, keyword: str = "") -> list[dict]:
    store = db.get(models.Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")

    query = (
        db.query(models.Inventory)
        .join(models.SKU, models.Inventory.sku_id == models.SKU.id)
        .join(models.Product, models.SKU.product_id == models.Product.id)
        .options(
            joinedload(models.Inventory.store),
            joinedload(models.Inventory.sku).joinedload(models.SKU.product),
        )
        .filter(models.Inventory.store_id == store_id)
    )
    if keyword:
        like_keyword = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                models.Product.name.like(like_keyword),
                models.Product.category.like(like_keyword),
                models.SKU.sku_code.like(like_keyword),
                models.SKU.barcode.like(like_keyword),
                models.SKU.color.like(like_keyword),
                models.SKU.size.like(like_keyword),
            )
        )

    inventories = query.order_by(models.Product.category, models.SKU.sku_code).limit(30).all()
    return [
        {
            "sku_id": item.sku_id,
            "sku_code": item.sku.sku_code,
            "barcode": item.sku.barcode,
            "product_name": item.sku.product.name,
            "category": item.sku.product.category,
            "color": item.sku.color,
            "size": item.sku.size,
            "list_price": item.sku.list_price,
            "cost_price": item.sku.cost_price,
            "store_id": item.store_id,
            "store_name": item.store.name,
            "inventory_quantity": item.quantity,
            "safety_stock": item.safety_stock,
        }
        for item in inventories
    ]


def list_promotions(db: Session) -> list[models.Promotion]:
    return db.query(models.Promotion).order_by(models.Promotion.id).all()


def list_members(db: Session) -> list[models.Member]:
    return db.query(models.Member).order_by(models.Member.id).all()


def search_members(db: Session, keyword: str) -> list[models.Member]:
    if not keyword.strip():
        return []
    like_keyword = f"%{keyword.strip()}%"
    return (
        db.query(models.Member)
        .filter(
            or_(
                models.Member.name.like(like_keyword),
                models.Member.phone.like(like_keyword),
                models.Member.member_no.like(like_keyword),
            )
        )
        .order_by(models.Member.id)
        .limit(10)
        .all()
    )


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
    inventories = (
        db.query(models.Inventory)
        .options(
            joinedload(models.Inventory.store),
            joinedload(models.Inventory.sku).joinedload(models.SKU.product),
        )
        .order_by(models.Inventory.store_id, models.Inventory.sku_id)
        .all()
    )
    return [_inventory_with_replenishment_metrics(db, item) for item in inventories]


def list_low_stock(db: Session) -> list[models.Inventory]:
    inventories = (
        db.query(models.Inventory)
        .options(
            joinedload(models.Inventory.store),
            joinedload(models.Inventory.sku).joinedload(models.SKU.product),
        )
        .filter(models.Inventory.quantity <= models.Inventory.safety_stock)
        .order_by(models.Inventory.quantity)
        .all()
    )
    return [_inventory_with_replenishment_metrics(db, item) for item in inventories]


def _recent_7d_sales(db: Session, store_id: int, sku_id: int) -> int:
    since = datetime.utcnow() - timedelta(days=7)
    return (
        db.query(func.coalesce(func.sum(models.SalesOrderItem.quantity), 0))
        .join(models.SalesOrder, models.SalesOrderItem.order_id == models.SalesOrder.id)
        .filter(
            models.SalesOrder.store_id == store_id,
            models.SalesOrderItem.sku_id == sku_id,
            models.SalesOrder.order_time >= since,
        )
        .scalar()
        or 0
    )


def _inventory_status(quantity: int, safety_stock: int, has_pending_replenishment: bool = False) -> str:
    if has_pending_replenishment:
        return "待补货"
    if quantity <= 0:
        return "缺货预警"
    if quantity < safety_stock:
        return "低库存"
    return "正常"


def _suggested_qty(safety_stock: int, recent_7d_sales: int, quantity: int, in_transit: int) -> int:
    return max(safety_stock * 2 + recent_7d_sales - quantity - in_transit, 0)


def _inventory_with_replenishment_metrics(db: Session, inventory: models.Inventory) -> dict:
    recent_7d_sales = _recent_7d_sales(db, inventory.store_id, inventory.sku_id)
    has_pending_replenishment = (
        db.query(models.ReplenishmentRequest)
        .filter(
            models.ReplenishmentRequest.inventory_id == inventory.id,
            models.ReplenishmentRequest.status.in_(["待审核", "已审核", "待调拨", "在途"]),
        )
        .first()
        is not None
    )
    return {
        "id": inventory.id,
        "store_id": inventory.store_id,
        "sku_id": inventory.sku_id,
        "quantity": inventory.quantity,
        "safety_stock": inventory.safety_stock,
        "in_transit": inventory.in_transit,
        "updated_at": inventory.updated_at,
        "store": inventory.store,
        "sku": inventory.sku,
        "recent_7d_sales": recent_7d_sales,
        "suggested_qty": _suggested_qty(
            inventory.safety_stock,
            recent_7d_sales,
            inventory.quantity,
            inventory.in_transit,
        ),
        "inventory_status": _inventory_status(
            inventory.quantity,
            inventory.safety_stock,
            has_pending_replenishment,
        ),
    }


def list_replenishments(db: Session) -> list[models.ReplenishmentRequest]:
    return (
        db.query(models.ReplenishmentRequest)
        .options(
            joinedload(models.ReplenishmentRequest.store),
            joinedload(models.ReplenishmentRequest.sku).joinedload(models.SKU.product),
        )
        .order_by(models.ReplenishmentRequest.created_at.desc())
        .all()
    )


def create_replenishment(
    db: Session,
    payload: schemas.ReplenishmentCreate,
) -> models.ReplenishmentRequest:
    inventory = (
        db.query(models.Inventory)
        .options(joinedload(models.Inventory.sku).joinedload(models.SKU.product))
        .filter(models.Inventory.id == payload.inventory_id)
        .first()
    )
    if not inventory:
        raise HTTPException(status_code=404, detail="库存记录不存在")

    recent_7d_sales = _recent_7d_sales(db, inventory.store_id, inventory.sku_id)
    request = models.ReplenishmentRequest(
        inventory_id=inventory.id,
        store_id=inventory.store_id,
        sku_id=inventory.sku_id,
        current_quantity=inventory.quantity,
        safety_stock=inventory.safety_stock,
        in_transit=inventory.in_transit,
        recent_7d_sales=recent_7d_sales,
        suggested_qty=_suggested_qty(
            inventory.safety_stock,
            recent_7d_sales,
            inventory.quantity,
            inventory.in_transit,
        ),
        request_qty=payload.request_qty,
        reason=payload.reason,
        applicant=payload.applicant,
        status="待审核",
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def approve_replenishment(db: Session, request_id: int) -> models.ReplenishmentRequest:
    request = db.get(models.ReplenishmentRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="补货申请不存在")
    if request.status not in {"待审核", "已驳回"}:
        raise HTTPException(status_code=400, detail="当前状态不能审核通过")
    request.status = "已审核"
    request.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(request)
    return request


def reject_replenishment(db: Session, request_id: int) -> models.ReplenishmentRequest:
    request = db.get(models.ReplenishmentRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="补货申请不存在")
    if request.status not in {"待审核", "已审核"}:
        raise HTTPException(status_code=400, detail="当前状态不能驳回")
    request.status = "已驳回"
    request.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(request)
    return request


def list_transfers(db: Session) -> list[models.TransferRecord]:
    return (
        db.query(models.TransferRecord)
        .options(
            joinedload(models.TransferRecord.request),
            joinedload(models.TransferRecord.store),
            joinedload(models.TransferRecord.sku).joinedload(models.SKU.product),
        )
        .order_by(models.TransferRecord.shipped_at.desc(), models.TransferRecord.id.desc())
        .all()
    )


def create_transfer(db: Session, payload: schemas.TransferCreate) -> models.TransferRecord:
    request = db.get(models.ReplenishmentRequest, payload.request_id)
    if not request:
        raise HTTPException(status_code=404, detail="补货申请不存在")
    if request.status != "已审核":
        raise HTTPException(status_code=400, detail="只能对已审核补货申请生成调拨单")

    inventory = db.get(models.Inventory, request.inventory_id)
    if not inventory:
        raise HTTPException(status_code=404, detail="库存记录不存在")

    transfer_qty = payload.transfer_qty or request.request_qty
    transfer = models.TransferRecord(
        request_id=request.id,
        inventory_id=request.inventory_id,
        store_id=request.store_id,
        sku_id=request.sku_id,
        source_location=payload.source_location,
        transfer_qty=transfer_qty,
        in_transit_qty=transfer_qty,
        status="在途",
        shipped_at=datetime.utcnow(),
        expected_arrival_at=datetime.utcnow() + timedelta(days=3),
    )
    request.status = "在途"
    request.updated_at = datetime.utcnow()
    inventory.in_transit += transfer_qty
    inventory.updated_at = datetime.utcnow()

    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    return transfer


def mark_transfer_arrival(db: Session, transfer_id: int) -> models.TransferRecord:
    transfer = db.get(models.TransferRecord, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="调拨记录不存在")
    if transfer.status == "已到货":
        return transfer

    inventory = db.get(models.Inventory, transfer.inventory_id)
    if not inventory:
        raise HTTPException(status_code=404, detail="库存记录不存在")
    request = db.get(models.ReplenishmentRequest, transfer.request_id)

    arrived_qty = transfer.in_transit_qty
    inventory.quantity += arrived_qty
    inventory.in_transit = max(inventory.in_transit - arrived_qty, 0)
    inventory.updated_at = datetime.utcnow()
    transfer.status = "已到货"
    transfer.in_transit_qty = 0
    transfer.arrived_at = datetime.utcnow()
    if request:
        request.status = "已完成"
        request.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(transfer)
    return transfer


def list_orders(db: Session, limit: int | None = None) -> list[models.SalesOrder]:
    query = (
        db.query(models.SalesOrder)
        .options(
            joinedload(models.SalesOrder.items)
            .joinedload(models.SalesOrderItem.sku)
            .joinedload(models.SKU.product)
        )
        .order_by(models.SalesOrder.order_time.desc())
    )
    if limit:
        query = query.limit(limit)
    return query.all()


def list_recent_orders(db: Session, limit: int = 8) -> list[models.SalesOrder]:
    return (
        db.query(models.SalesOrder)
        .options(
            joinedload(models.SalesOrder.items)
            .joinedload(models.SalesOrderItem.sku)
            .joinedload(models.SKU.product)
        )
        .order_by(models.SalesOrder.order_time.desc())
        .limit(limit)
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
