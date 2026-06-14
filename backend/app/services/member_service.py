from sqlalchemy.orm import Session

from .. import models


def calculate_member_sales_ratio(db: Session) -> float:
    orders = db.query(models.SalesOrder).all()
    if not orders:
        return 0.0
    member_amount = sum(order.paid_amount for order in orders if order.member_id)
    total_amount = sum(order.paid_amount for order in orders)
    return round(member_amount / total_amount, 4) if total_amount else 0.0
