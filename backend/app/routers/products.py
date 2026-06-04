from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/products", tags=["商品与SKU"])


@router.get("", response_model=list[schemas.ProductOut])
def get_products(db: Session = Depends(get_db)):
    return crud.list_products(db)


@router.post("", response_model=schemas.ProductOut, status_code=201)
def add_product(payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db, payload)


@router.get("/skus", response_model=list[schemas.SKUOut])
def get_skus(db: Session = Depends(get_db)):
    return crud.list_skus(db)


@router.post("/skus", response_model=schemas.SKUOut, status_code=201)
def add_sku(payload: schemas.SKUCreate, db: Session = Depends(get_db)):
    return crud.create_sku(db, payload)


@router.post("/skus/generate-code", response_model=schemas.SKUCodePreviewOut)
def generate_sku_code(payload: schemas.SKUCodePreviewRequest, db: Session = Depends(get_db)):
    return crud.generate_sku_code_preview(db, payload)


@router.put("/skus/{sku_id}", response_model=schemas.SKUOut)
def edit_sku(sku_id: int, payload: schemas.SKUUpdate, db: Session = Depends(get_db)):
    return crud.update_sku(db, sku_id, payload)


@router.put("/skus/{sku_id}/status", response_model=schemas.SKUOut)
def change_sku_status(sku_id: int, payload: schemas.StatusUpdate, db: Session = Depends(get_db)):
    return crud.update_sku_status(db, sku_id, payload.status)


@router.put("/{product_id}", response_model=schemas.ProductOut)
def edit_product(product_id: int, payload: schemas.ProductUpdate, db: Session = Depends(get_db)):
    return crud.update_product(db, product_id, payload)


@router.put("/{product_id}/status", response_model=schemas.ProductOut)
def change_product_status(product_id: int, payload: schemas.StatusUpdate, db: Session = Depends(get_db)):
    return crud.update_product_status(db, product_id, payload.status)
