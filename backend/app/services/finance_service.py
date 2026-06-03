from sqlalchemy.orm import Session

from .. import crud


def get_finance_summary(db: Session) -> dict:
    return crud.finance_summary(db)
