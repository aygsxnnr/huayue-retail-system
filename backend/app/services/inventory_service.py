from sqlalchemy.orm import Session

from .. import crud, models


def get_low_stock_items(db: Session) -> list[models.Inventory]:
    return crud.list_low_stock(db)
