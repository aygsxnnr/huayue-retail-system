from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/coupons", tags=["优惠券管理"])


@router.get("", response_model=list[schemas.CouponOut])
def get_coupons(db: Session = Depends(get_db)):
    return crud.list_coupons(db)


@router.post("", response_model=schemas.CouponOut, status_code=201)
def add_coupon(payload: schemas.CouponCreate, db: Session = Depends(get_db)):
    return crud.create_coupon(db, payload)


@router.put("/{coupon_id}", response_model=schemas.CouponOut)
def edit_coupon(coupon_id: int, payload: schemas.CouponUpdate, db: Session = Depends(get_db)):
    return crud.update_coupon(db, coupon_id, payload)


@router.put("/{coupon_id}/status", response_model=schemas.CouponOut)
def change_coupon_status(coupon_id: int, payload: schemas.StatusUpdate, db: Session = Depends(get_db)):
    return crud.update_coupon_status(db, coupon_id, payload.status)
