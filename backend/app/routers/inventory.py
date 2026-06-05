from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/inventory", tags=["库存补货"])


@router.get("", response_model=list[schemas.InventoryOut])
def get_inventory(db: Session = Depends(get_db)):
    return crud.list_inventory(db)


@router.get("/low-stock", response_model=list[schemas.InventoryOut])
def get_low_stock(db: Session = Depends(get_db)):
    return crud.list_low_stock(db)


@router.put("/{inventory_id}/safety-stock", response_model=schemas.InventoryOut)
def edit_safety_stock(
    inventory_id: int,
    payload: schemas.InventorySafetyStockUpdate,
    db: Session = Depends(get_db),
):
    return crud.update_inventory_safety_stock(db, inventory_id, payload)


@router.get("/replenishments", response_model=list[schemas.ReplenishmentOut])
def get_replenishments(db: Session = Depends(get_db)):
    return crud.list_replenishments(db)


@router.post("/replenishments", response_model=schemas.ReplenishmentOut, status_code=201)
def add_replenishment(payload: schemas.ReplenishmentCreate, db: Session = Depends(get_db)):
    return crud.create_replenishment(db, payload)


@router.put("/replenishments/{request_id}/approve", response_model=schemas.ReplenishmentOut)
def approve_replenishment(request_id: int, db: Session = Depends(get_db)):
    return crud.approve_replenishment(db, request_id)


@router.put("/replenishments/{request_id}/reject", response_model=schemas.ReplenishmentOut)
def reject_replenishment(request_id: int, db: Session = Depends(get_db)):
    return crud.reject_replenishment(db, request_id)


@router.get("/transfers", response_model=list[schemas.TransferOut])
def get_transfers(db: Session = Depends(get_db)):
    return crud.list_transfers(db)


@router.post("/transfers", response_model=schemas.TransferOut, status_code=201)
def add_transfer(payload: schemas.TransferCreate, db: Session = Depends(get_db)):
    return crud.create_transfer(db, payload)


@router.put("/transfers/{transfer_id}/arrival", response_model=schemas.TransferOut)
def mark_arrival(transfer_id: int, db: Session = Depends(get_db)):
    return crud.mark_transfer_arrival(db, transfer_id)
