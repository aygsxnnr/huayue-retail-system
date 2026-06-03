from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/members", tags=["会员管理"])


@router.get("", response_model=list[schemas.MemberOut])
def get_members(db: Session = Depends(get_db)):
    return crud.list_members(db)


@router.post("", response_model=schemas.MemberOut, status_code=201)
def add_member(payload: schemas.MemberCreate, db: Session = Depends(get_db)):
    return crud.create_member(db, payload)
