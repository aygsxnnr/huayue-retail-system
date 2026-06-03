from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/sales", tags=["POS销售"])


@router.get("/orders", response_model=list[schemas.SalesOrderOut])
def get_orders(db: Session = Depends(get_db)):
    return crud.list_orders(db)


@router.post("/orders", response_model=schemas.SalesOrderOut, status_code=201)
def add_order(payload: schemas.OrderCreate, db: Session = Depends(get_db)):
    return crud.create_order(db, payload)
