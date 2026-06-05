from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..services.finance_service import get_finance_summary

router = APIRouter(prefix="/finance", tags=["财务对账"])


@router.get("/records", response_model=list[schemas.FinanceRecordViewOut])
def get_records(db: Session = Depends(get_db)):
    return crud.list_finance_records(db)


@router.put("/records/batch-resolve", response_model=schemas.FinanceBatchResolveOut)
def batch_resolve_records(payload: schemas.FinanceBatchResolveIn, db: Session = Depends(get_db)):
    return crud.batch_resolve_finance_records(db, payload.record_ids)


@router.put("/records/batch-reconcile", response_model=schemas.FinanceBatchReconcileOut)
def batch_reconcile_records(payload: schemas.FinanceBatchReconcileIn, db: Session = Depends(get_db)):
    return crud.batch_reconcile_finance_records(db, payload.record_ids)


@router.put("/records/{record_id}/resolve", response_model=schemas.FinanceRecordViewOut)
def resolve_record(record_id: int, db: Session = Depends(get_db)):
    return crud.resolve_finance_record(db, record_id)


@router.put("/records/{record_id}/reconcile", response_model=schemas.FinanceRecordViewOut)
def reconcile_record(record_id: int, db: Session = Depends(get_db)):
    return crud.reconcile_finance_record(db, record_id)


@router.get("/summary", response_model=schemas.FinanceSummaryOut)
def get_summary(db: Session = Depends(get_db)):
    return get_finance_summary(db)


@router.get("/payments", response_model=list[schemas.PaymentRecordViewOut])
def get_payments(db: Session = Depends(get_db)):
    return crud.list_payment_records(db)


@router.get("/profit-trend", response_model=schemas.ProfitTrendOut)
def get_profit_trend(db: Session = Depends(get_db)):
    return crud.finance_profit_trend(db)


@router.get("/store-settlement", response_model=list[schemas.StoreSettlementOut])
def get_store_settlement(db: Session = Depends(get_db)):
    return crud.finance_store_settlement(db)


@router.get("/promotion-loss", response_model=list[schemas.PromotionLossOut])
def get_promotion_loss(db: Session = Depends(get_db)):
    return crud.finance_promotion_loss(db)
