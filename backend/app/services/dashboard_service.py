from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from .. import models


def _to_float(value) -> float:
    return float(value or 0)


def get_dashboard(db: Session) -> dict:
    sales_amount = _to_float(
        db.query(func.coalesce(func.sum(models.SalesOrder.paid_amount), 0)).scalar()
    )

    order_count = int(
        db.query(func.count(models.SalesOrder.id)).scalar() or 0
    )

    member_sales_amount = _to_float(
        db.query(func.coalesce(func.sum(models.SalesOrder.paid_amount), 0))
        .filter(models.SalesOrder.member_id.isnot(None))
        .scalar()
    )

    member_sales_ratio = (
        round(member_sales_amount / sales_amount, 4)
        if sales_amount
        else 0.0
    )

    gross_profit = _to_float(
        db.query(func.coalesce(func.sum(models.FinanceRecord.gross_profit), 0)).scalar()
    )

    inventory_quantity = int(
        db.query(func.coalesce(func.sum(models.Inventory.quantity), 0)).scalar() or 0
    )

    sold_quantity = int(
        db.query(func.coalesce(func.sum(models.SalesOrderItem.quantity), 0)).scalar() or 0
    )

    low_stock_sku_count = int(
        db.query(func.count(models.Inventory.id))
        .filter(models.Inventory.quantity <= models.Inventory.safety_stock)
        .scalar()
        or 0
    )

    category_rows = (
        db.query(
            models.Product.category,
            func.coalesce(func.sum(models.SalesOrderItem.subtotal), 0).label("sales_amount"),
        )
        .join(models.SKU, models.SKU.product_id == models.Product.id)
        .join(models.SalesOrderItem, models.SalesOrderItem.sku_id == models.SKU.id)
        .group_by(models.Product.category)
        .order_by(func.sum(models.SalesOrderItem.subtotal).desc())
        .all()
    )

    turnover_days = 0.0
    if sold_quantity:
        turnover_days = round((inventory_quantity / sold_quantity) * 30, 1)

    low_stock_items = (
        db.query(models.Inventory)
        .options(
            joinedload(models.Inventory.store),
            joinedload(models.Inventory.sku).joinedload(models.SKU.product),
        )
        .filter(models.Inventory.quantity <= models.Inventory.safety_stock)
        .order_by(models.Inventory.quantity.asc())
        .limit(8)
        .all()
    )

    return {
        "summary": {
            "sales_amount": round(sales_amount, 2),
            "order_count": order_count,
            "average_order_value": round(sales_amount / order_count, 2) if order_count else 0,
            "member_sales_ratio": member_sales_ratio,
            "low_stock_sku_count": low_stock_sku_count,
            "inventory_turnover_days": turnover_days,
            "gross_profit": round(gross_profit, 2),
        },
        "category_sales": [
            {
                "category": row.category,
                "sales_amount": round(_to_float(row.sales_amount), 2),
            }
            for row in category_rows
        ],
        "low_stock_items": low_stock_items,
    }
