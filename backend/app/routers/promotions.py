from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/promotions", tags=["促销活动"])


@router.get("", response_model=list[schemas.PromotionOut])
def get_promotions(db: Session = Depends(get_db)):
    return crud.list_promotions(db)


@router.post("", response_model=schemas.PromotionOut, status_code=201)
def add_promotion(payload: schemas.PromotionCreate, db: Session = Depends(get_db)):
    return crud.create_promotion(db, payload)


@router.put("/{promotion_id}", response_model=schemas.PromotionOut)
def edit_promotion(promotion_id: int, payload: schemas.PromotionUpdate, db: Session = Depends(get_db)):
    return crud.update_promotion(db, promotion_id, payload)


@router.put("/{promotion_id}/status", response_model=schemas.PromotionOut)
def change_promotion_status(promotion_id: int, payload: schemas.StatusUpdate, db: Session = Depends(get_db)):
    return crud.update_promotion_status(db, promotion_id, payload.status)
