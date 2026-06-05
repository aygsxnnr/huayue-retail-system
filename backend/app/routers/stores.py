from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/stores", tags=["门店管理"])


@router.get("", response_model=list[schemas.StoreOut])
def get_stores(db: Session = Depends(get_db)):
    return crud.list_stores(db)


@router.post("", response_model=schemas.StoreOut, status_code=201)
def add_store(payload: schemas.StoreCreate, db: Session = Depends(get_db)):
    return crud.create_store(db, payload)


@router.put("/{store_id}", response_model=schemas.StoreOut)
def edit_store(store_id: int, payload: schemas.StoreUpdate, db: Session = Depends(get_db)):
    return crud.update_store(db, store_id, payload)


@router.put("/{store_id}/status", response_model=schemas.StoreOut)
def change_store_status(store_id: int, payload: schemas.StatusUpdate, db: Session = Depends(get_db)):
    return crud.update_store_status(db, store_id, payload.status)
