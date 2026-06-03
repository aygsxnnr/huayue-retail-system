from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/promotions", tags=["促销活动"])


@router.get("", response_model=list[schemas.PromotionOut])
def get_promotions(db: Session = Depends(get_db)):
    return crud.list_promotions(db)
