from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/sales", tags=["POS销售"])


@router.get("/orders", response_model=list[schemas.SalesOrderOut])
def get_orders(
    limit: int | None = Query(default=None, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return crud.list_orders(db, limit=limit)


@router.get("/orders/recent", response_model=list[schemas.SalesOrderOut])
def get_recent_orders(
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return crud.list_recent_orders(db, limit=limit)


@router.post("/orders", response_model=schemas.SalesOrderOut, status_code=201)
def add_order(payload: schemas.OrderCreate, db: Session = Depends(get_db)):
    return crud.create_order(db, payload)


@router.get("/stores", response_model=list[schemas.StoreOut])
def get_stores(db: Session = Depends(get_db)):
    return crud.list_stores(db)


@router.get("/pos/skus", response_model=list[schemas.POSSkuOut])
def search_pos_skus(
    store_id: int = Query(..., description="当前收银门店ID"),
    keyword: str = Query(default="", description="商品名、SKU、条码、颜色或尺码"),
    db: Session = Depends(get_db),
):
    return crud.search_pos_skus(db, store_id=store_id, keyword=keyword)


@router.get("/members/search", response_model=list[schemas.MemberOut])
def search_members(
    keyword: str = Query(..., description="会员手机号、会员编号或姓名"),
    db: Session = Depends(get_db),
):
    return crud.search_members(db, keyword=keyword)
