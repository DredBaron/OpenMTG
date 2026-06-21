from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import services.settings as settings_service

router = APIRouter(prefix="/scanner", tags=["scanner"])


@router.get("/status")
def scanner_status(db: Session = Depends(get_db)):
    return {"enabled": settings_service.get(db, "scanner_enabled") != "false"}
