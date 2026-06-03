from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/products", tags=["商品与SKU"])


@router.get("", response_model=list[schemas.ProductOut])
def get_products(db: Session = Depends(get_db)):
    return crud.list_products(db)


@router.get("/skus", response_model=list[schemas.SKUOut])
def get_skus(db: Session = Depends(get_db)):
    return crud.list_skus(db)
