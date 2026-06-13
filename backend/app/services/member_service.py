from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models


def calculate_member_sales_ratio(db: Session) -> float:
    total_amount = float(
        db.query(func.coalesce(func.sum(models.SalesOrder.paid_amount), 0)).scalar()
        or 0
    )

    if not total_amount:
        return 0.0

    member_amount = float(
        db.query(func.coalesce(func.sum(models.SalesOrder.paid_amount), 0))
        .filter(models.SalesOrder.member_id.isnot(None))
        .scalar()
        or 0
    )

    return round(member_amount / total_amount, 4)
