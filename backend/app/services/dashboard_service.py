from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from .. import crud, models
from .member_service import calculate_member_sales_ratio


def get_dashboard(db: Session) -> dict:
    sales_amount = db.query(func.coalesce(func.sum(models.SalesOrder.paid_amount), 0)).scalar()
    order_count = db.query(models.SalesOrder).count()
    orders = (
        db.query(models.SalesOrder)
        .options(joinedload(models.SalesOrder.items).joinedload(models.SalesOrderItem.sku).joinedload(models.SKU.product))
        .all()
    )
    gross_profit = sum(float(order.paid_amount or 0) - sum(_order_item_cost(item) for item in order.items) for order in orders)
    inventory_quantity = db.query(func.coalesce(func.sum(models.Inventory.quantity), 0)).scalar()
    sold_quantity = db.query(func.coalesce(func.sum(models.SalesOrderItem.quantity), 0)).scalar()
    low_stock_items = crud.list_low_stock(db)

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

    return {
        "summary": {
            "sales_amount": round(sales_amount or 0, 2),
            "order_count": order_count,
            "average_order_value": round((sales_amount or 0) / order_count, 2) if order_count else 0,
            "member_sales_ratio": calculate_member_sales_ratio(db),
            "low_stock_sku_count": len(low_stock_items),
            "inventory_turnover_days": turnover_days,
            "gross_profit": round(gross_profit or 0, 2),
        },
        "category_sales": [
            {"category": row.category, "sales_amount": round(row.sales_amount, 2)}
            for row in category_rows
        ],
        "low_stock_items": (
            db.query(models.Inventory)
            .options(
                joinedload(models.Inventory.store),
                joinedload(models.Inventory.sku).joinedload(models.SKU.product),
            )
            .filter(models.Inventory.quantity <= models.Inventory.safety_stock)
            .order_by(models.Inventory.quantity)
            .limit(8)
            .all()
        ),
}


def _sku_cost_price(sku: models.SKU | None) -> float:
    if not sku:
        return 0
    if sku.cost_price is not None and sku.cost_price > 0:
        return float(sku.cost_price)
    product = sku.product
    if product and product.cost_price is not None and product.cost_price > 0:
        return float(product.cost_price)
    return 0


def _order_item_cost(item: models.SalesOrderItem) -> float:
    if item.cost_amount is not None and item.cost_amount > 0:
        return float(item.cost_amount)
    if item.unit_cost is not None and item.unit_cost > 0:
        return float(item.unit_cost) * item.quantity
    return _sku_cost_price(item.sku) * item.quantity
