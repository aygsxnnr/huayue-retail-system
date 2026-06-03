from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..services.dashboard_service import get_dashboard

router = APIRouter(prefix="/dashboard", tags=["经营看板"])


@router.get("/summary", response_model=schemas.DashboardOut)
def get_summary(db: Session = Depends(get_db)):
    return get_dashboard(db)
