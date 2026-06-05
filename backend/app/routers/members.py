from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/members", tags=["会员与营销管理"])


@router.get("", response_model=list[schemas.MemberOut])
def get_members(db: Session = Depends(get_db)):
    return crud.list_members(db)


@router.post("", response_model=schemas.MemberOut, status_code=201)
def add_member(payload: schemas.MemberCreate, db: Session = Depends(get_db)):
    return crud.create_member(db, payload)


@router.get("/rfm", response_model=list[schemas.RFMOut])
def get_member_rfm(db: Session = Depends(get_db)):
    return crud.list_member_rfm(db)


@router.post("/rfm/recalculate", response_model=list[schemas.RFMOut])
def recalculate_member_rfm(db: Session = Depends(get_db)):
    return crud.recalculate_member_rfm(db)


@router.get("/marketing-touches", response_model=list[schemas.MarketingTouchOut])
def get_marketing_touches(db: Session = Depends(get_db)):
    return crud.list_marketing_touches(db)


@router.post("/marketing-touches", response_model=schemas.MarketingTouchOut, status_code=201)
def add_marketing_touch(payload: schemas.MarketingTouchCreate, db: Session = Depends(get_db)):
    return crud.create_marketing_touch(db, payload)


@router.get("/repurchase-analysis", response_model=schemas.RepurchaseAnalysisOut)
def get_repurchase_analysis(db: Session = Depends(get_db)):
    return crud.repurchase_analysis(db)


@router.get("/{member_id}", response_model=schemas.MemberOut)
def get_member(member_id: int, db: Session = Depends(get_db)):
    member = db.get(models.Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="会员不存在")
    return member


@router.put("/{member_id}", response_model=schemas.MemberOut)
def edit_member(member_id: int, payload: schemas.MemberUpdate, db: Session = Depends(get_db)):
    return crud.update_member(db, member_id, payload)


@router.put("/{member_id}/status", response_model=schemas.MemberOut)
def change_member_status(member_id: int, payload: schemas.MemberStatusUpdate, db: Session = Depends(get_db)):
    return crud.update_member_status(db, member_id, payload.status)


@router.get("/{member_id}/profile", response_model=schemas.MemberProfileOut)
def get_member_profile(member_id: int, db: Session = Depends(get_db)):
    return crud.get_member_profile(db, member_id)
