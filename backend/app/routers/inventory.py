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
