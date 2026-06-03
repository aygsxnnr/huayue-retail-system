from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..services.finance_service import get_finance_summary

router = APIRouter(prefix="/finance", tags=["财务对账"])


@router.get("/records", response_model=list[schemas.FinanceRecordOut])
def get_records(db: Session = Depends(get_db)):
    return crud.list_finance_records(db)


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    return get_finance_summary(db)
