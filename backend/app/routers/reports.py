from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from .. import models
from ..database import get_db

router = APIRouter(prefix="/reports", tags=["报表中心"])


def _date_range(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    end = end_date or datetime.utcnow().date()
    start = start_date or (end - timedelta(days=6))
    if start > end:
        return end, start
    return start, end


def _round(value: float | int | None) -> float:
    return round(float(value or 0), 2)


def _rate(numerator: float, denominator: float) -> float:
    return _round((float(numerator or 0) / float(denominator or 1)) * 100) if denominator else 0


def _order_cost(order: models.SalesOrder) -> float:
    return sum((item.sku.cost_price if item.sku else 0) * item.quantity for item in order.items)


def _payment_amount(order: models.SalesOrder | None) -> float:
    if not order:
        return 0
    return float(order.payment.amount if order.payment else order.paid_amount)


def _difference_amount(record: models.FinanceRecord) -> float:
    order = record.order
    if not order:
        return 0
    return abs(float(order.paid_amount or 0) - _payment_amount(order))


def _status_color(status: str) -> str:
    if status in {"已对账", "已平账", "已处理", "正常", "成功", "进行中"}:
        return "green"
    if status in {"待对账", "未开始"}:
        return "blue"
    if status in {"低库存", "待补货", "待处理"}:
        return "orange"
    if status in {"缺货预警", "存在差异", "已关闭", "失败", "已停用", "已结束"}:
        return "red"
    return "default"


def _finance_priority(status: str) -> int:
    return {
        "存在差异": 1,
        "待处理": 2,
        "待对账": 3,
        "已处理": 4,
        "已对账": 5,
        "已平账": 5,
        "已关闭": 6,
    }.get(status, 7)


def _number_suffix(value: str | None) -> int:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    return int(digits or 0)


def _date_value(value: str | None) -> float:
    if not value or value == "-":
        return 0
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except ValueError:
        return 0


def _orders_query(
    db: Session,
    start: date,
    end: date,
    store_id: int | None,
    category_id: str | None,
):
    query = db.query(models.SalesOrder).options(
        joinedload(models.SalesOrder.store),
        joinedload(models.SalesOrder.payment),
        joinedload(models.SalesOrder.promotion),
        joinedload(models.SalesOrder.items).joinedload(models.SalesOrderItem.sku).joinedload(models.SKU.product),
    )
    query = query.filter(models.SalesOrder.order_time >= datetime.combine(start, datetime.min.time()))
    query = query.filter(models.SalesOrder.order_time <= datetime.combine(end, datetime.max.time()))
    if store_id:
        query = query.filter(models.SalesOrder.store_id == store_id)
    orders = query.all()
    if category_id:
        orders = [
            order
            for order in orders
            if any(item.sku and item.sku.product and item.sku.product.category == category_id for item in order.items)
        ]
    return orders


def _finance_records_query(db: Session, start: date, end: date, store_id: int | None):
    query = db.query(models.FinanceRecord).options(
        joinedload(models.FinanceRecord.order).joinedload(models.SalesOrder.payment),
        joinedload(models.FinanceRecord.order).joinedload(models.SalesOrder.store),
        joinedload(models.FinanceRecord.store),
    )
    query = query.filter(models.FinanceRecord.business_date >= start, models.FinanceRecord.business_date <= end)
    if store_id:
        query = query.filter(models.FinanceRecord.store_id == store_id)
    return query.all()


def _inventory_status(item: models.Inventory) -> str:
    if item.quantity <= 0:
        return "缺货预警"
    if item.quantity < item.safety_stock:
        return "低库存"
    if item.in_transit > 0 and item.quantity < item.safety_stock * 2:
        return "待补货"
    return "正常"


def _suggested_qty(item: models.Inventory) -> int:
    recent_sales = 3
    return max(item.safety_stock * 2 + recent_sales - item.quantity - item.in_transit, 0)


@router.get("/summary")
def get_report_summary(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    store_id: int | None = Query(default=None),
    category_id: str | None = Query(default=None),
    period: str = Query(default="day"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    start, end = _date_range(start_date, end_date)
    orders = _orders_query(db, start, end, store_id, category_id)
    finance_records = _finance_records_query(db, start, end, store_id)
    sales_total = sum(order.paid_amount for order in orders)
    order_count = len(orders)
    cost_total = sum(_order_cost(order) for order in orders)
    gross_profit = sales_total - cost_total
    payment_total = sum(_payment_amount(order) for order in orders)
    difference_amount = sum(abs(float(order.paid_amount or 0) - _payment_amount(order)) for order in orders)
    inventory_query = db.query(models.Inventory)
    if store_id:
        inventory_query = inventory_query.filter(models.Inventory.store_id == store_id)
    inventories = inventory_query.all()
    out_of_stock_count = sum(1 for item in inventories if item.quantity <= 0)
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "period": period,
        "sales_total": _round(sales_total),
        "order_count": order_count,
        "average_order_value": _round(sales_total / order_count if order_count else 0),
        "gross_profit": _round(gross_profit),
        "gross_profit_rate": _rate(gross_profit, sales_total),
        "payment_total": _round(payment_total),
        "difference_amount": _round(difference_amount or sum(_difference_amount(record) for record in finance_records)),
        "out_of_stock_sku_count": out_of_stock_count,
    }


@router.get("/sales-trend")
def get_sales_trend(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    store_id: int | None = Query(default=None),
    category_id: str | None = Query(default=None),
    period: str = Query(default="day"),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    start, end = _date_range(start_date, end_date)
    orders = _orders_query(db, start, end, store_id, category_id)
    days = (end - start).days + 1
    rows = []
    for offset in range(days):
        current = start + timedelta(days=offset)
        day_orders = [order for order in orders if order.order_time.date() == current]
        rows.append(
            {
                "date": current.strftime("%m-%d"),
                "sales_amount": _round(sum(order.paid_amount for order in day_orders)),
                "order_count": len(day_orders),
            }
        )
    return rows


@router.get("/store-performance")
def get_store_performance(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    store_id: int | None = Query(default=None),
    category_id: str | None = Query(default=None),
    period: str = Query(default="day"),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    start, end = _date_range(start_date, end_date)
    stores = db.query(models.Store).order_by(models.Store.code).all()
    rows = []
    for store in stores:
        if store_id and store.id != store_id:
            continue
        orders = _orders_query(db, start, end, store.id, category_id)
        sales_amount = sum(order.paid_amount for order in orders)
        cost_amount = sum(_order_cost(order) for order in orders)
        gross_profit = sales_amount - cost_amount
        finance_records = _finance_records_query(db, start, end, store.id)
        rows.append(
            {
                "rank": 0,
                "store_id": store.id,
                "store_name": store.name,
                "sales_amount": _round(sales_amount),
                "order_count": len(orders),
                "average_order_value": _round(sales_amount / len(orders) if orders else 0),
                "gross_profit": _round(gross_profit),
                "gross_profit_rate": _rate(gross_profit, sales_amount),
                "difference_amount": _round(sum(_difference_amount(record) for record in finance_records)),
            }
        )
    rows.sort(key=lambda item: item["sales_amount"], reverse=True)
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


@router.get("/category-analysis")
def get_category_analysis(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    store_id: int | None = Query(default=None),
    category_id: str | None = Query(default=None),
    period: str = Query(default="day"),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    start, end = _date_range(start_date, end_date)
    orders = _orders_query(db, start, end, store_id, category_id)
    category_map: dict[str, dict[str, Any]] = {}
    for order in orders:
        for item in order.items:
            sku = item.sku
            product = sku.product if sku else None
            category = product.category if product else "未分类"
            row = category_map.setdefault(category, {"category": category, "sales_amount": 0.0, "cost_amount": 0.0, "sales_quantity": 0})
            row["sales_amount"] += float(item.subtotal or 0)
            row["cost_amount"] += float((sku.cost_price if sku else 0) * item.quantity)
            row["sales_quantity"] += item.quantity
    rows = []
    for row in category_map.values():
        gross_profit = row["sales_amount"] - row["cost_amount"]
        rows.append(
            {
                **row,
                "sales_amount": _round(row["sales_amount"]),
                "cost_amount": _round(row["cost_amount"]),
                "gross_profit": _round(gross_profit),
                "gross_profit_rate": _rate(gross_profit, row["sales_amount"]),
            }
        )
    return sorted(rows, key=lambda item: item["sales_amount"], reverse=True)


@router.get("/product-ranking")
def get_product_ranking(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    store_id: int | None = Query(default=None),
    category_id: str | None = Query(default=None),
    period: str = Query(default="day"),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    start, end = _date_range(start_date, end_date)
    orders = _orders_query(db, start, end, store_id, category_id)
    inventory_map: dict[int, int] = {}
    inventory_query = db.query(models.Inventory)
    if store_id:
        inventory_query = inventory_query.filter(models.Inventory.store_id == store_id)
    for item in inventory_query.all():
        inventory_map[item.sku_id] = inventory_map.get(item.sku_id, 0) + item.quantity
    product_map: dict[int, dict[str, Any]] = {}
    for order in orders:
        for item in order.items:
            sku = item.sku
            product = sku.product if sku else None
            key = sku.id if sku else item.id
            row = product_map.setdefault(
                key,
                {
                    "product_code": product.code if product else "-",
                    "product_name": product.name if product else "未知商品",
                    "sku_code": sku.sku_code if sku else "-",
                    "sales_quantity": 0,
                    "sales_amount": 0.0,
                    "cost_amount": 0.0,
                    "current_inventory": inventory_map.get(sku.id, 0) if sku else 0,
                },
            )
            row["sales_quantity"] += item.quantity
            row["sales_amount"] += float(item.subtotal or 0)
            row["cost_amount"] += float((sku.cost_price if sku else 0) * item.quantity)
    rows = []
    for index, row in enumerate(sorted(product_map.values(), key=lambda item: item["sales_amount"], reverse=True), start=1):
        gross_profit = row["sales_amount"] - row["cost_amount"]
        rows.append(
            {
                "rank": index,
                **row,
                "sales_amount": _round(row["sales_amount"]),
                "gross_profit": _round(gross_profit),
                "gross_profit_rate": _rate(gross_profit, row["sales_amount"]),
            }
        )
    return rows[:20]


@router.get("/inventory-health")
def get_inventory_health(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    store_id: int | None = Query(default=None),
    category_id: str | None = Query(default=None),
    period: str = Query(default="day"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    query = db.query(models.Inventory).options(
        joinedload(models.Inventory.store),
        joinedload(models.Inventory.sku).joinedload(models.SKU.product),
    )
    if store_id:
        query = query.filter(models.Inventory.store_id == store_id)
    inventories = query.all()
    if category_id:
        inventories = [item for item in inventories if item.sku and item.sku.product and item.sku.product.category == category_id]
    distribution = {"正常": 0, "低库存": 0, "缺货预警": 0, "待补货": 0}
    alerts = []
    for item in inventories:
        status = _inventory_status(item)
        distribution[status] = distribution.get(status, 0) + 1
        if status != "正常":
            product = item.sku.product if item.sku else None
            alerts.append(
                {
                    "id": item.id,
                    "store_name": item.store.name if item.store else "-",
                    "product_name": product.name if product else "-",
                    "sku_code": item.sku.sku_code if item.sku else "-",
                    "quantity": item.quantity,
                    "safety_stock": item.safety_stock,
                    "in_transit": item.in_transit,
                    "inventory_status": status,
                    "suggested_qty": _suggested_qty(item),
                }
            )
    return {
        "distribution": [{"status": key, "count": value, "color": _status_color(key)} for key, value in distribution.items()],
        "alerts": sorted(alerts, key=lambda item: (item["quantity"], item["store_name"], item["sku_code"]))[:30],
    }


@router.get("/promotion-effect")
def get_promotion_effect(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    store_id: int | None = Query(default=None),
    category_id: str | None = Query(default=None),
    period: str = Query(default="day"),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    start, end = _date_range(start_date, end_date)
    promotions = db.query(models.Promotion).order_by(models.Promotion.id).all()
    rows = []
    for promotion in promotions:
        orders = [
            order
            for order in _orders_query(db, start, end, store_id, category_id)
            if order.promotion_id == promotion.id
        ]
        original_amount = sum(order.total_amount for order in orders)
        discount_amount = sum(order.discount_amount for order in orders)
        paid_amount = sum(order.paid_amount for order in orders)
        cost_amount = sum(_order_cost(order) for order in orders)
        gross_profit = paid_amount - cost_amount
        rows.append(
            {
                "promotion_id": promotion.id,
                "promotion_code": f"PR{promotion.id:05d}",
                "promotion_name": promotion.name,
                "promotion_type": promotion.promotion_type,
                "order_count": len(orders),
                "discount_amount": _round(discount_amount),
                "paid_amount": _round(paid_amount),
                "gross_profit": _round(gross_profit),
                "gross_profit_rate": _rate(gross_profit, paid_amount),
                "status": promotion.status,
                "original_amount": _round(original_amount),
            }
        )
    return sorted(rows, key=lambda item: item["paid_amount"], reverse=True)


@router.get("/finance-overview")
def get_finance_overview(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    store_id: int | None = Query(default=None),
    category_id: str | None = Query(default=None),
    period: str = Query(default="day"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    start, end = _date_range(start_date, end_date)
    records = _finance_records_query(db, start, end, store_id)
    distribution: dict[str, int] = {}
    rows = []
    for record in records:
        order = record.order
        payment = order.payment if order else None
        status = record.reconcile_status or "待对账"
        distribution[status] = distribution.get(status, 0) + 1
        rows.append(
            {
                "id": record.id,
                "record_no": record.record_no,
                "order_no": order.order_no if order else "-",
                "store_name": (record.store.name if record.store else (order.store.name if order and order.store else "-")),
                "order_amount": _round(order.paid_amount if order else record.sales_amount),
                "payment_amount": _round(payment.amount if payment else record.sales_amount),
                "difference_amount": _round(_difference_amount(record)),
                "status": status,
                "reconciliation_time": record.business_date.isoformat() if record.business_date else "-",
            }
        )
    rows.sort(key=lambda item: (_finance_priority(item["status"]), -_date_value(item["reconciliation_time"]), -_number_suffix(item["record_no"])))
    return {
        "distribution": [{"status": key, "count": value, "color": _status_color(key)} for key, value in distribution.items()],
        "records": rows,
    }
