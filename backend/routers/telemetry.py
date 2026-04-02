from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
from database import get_db
from security import get_current_user
import models
import services.settings as settings_service
import services.telemetry as telemetry_service

logger = logging.getLogger(__name__)

def require_admin(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


router = APIRouter(
    prefix="/admin/telemetry",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("")
def get_telemetry_status(db: Session = Depends(get_db)):
    suppressed = telemetry_service.is_suppressed()
    enabled = settings_service.get(db, "telemetry_enabled") == "true"
    telemetry_id = settings_service.get(db, "telemetry_id") if enabled else None
    last_sent   = settings_service.get(db, "telemetry_last_sent")
    last_packet = settings_service.get(db, "telemetry_last_packet")

    return {
        "suppressed": suppressed,
        "enabled":    enabled,
        "id":         telemetry_id,
        "last_sent":  last_sent,
        "last_packet": last_packet,
    }


@router.post("/enable")
def enable_telemetry(db: Session = Depends(get_db)):
    if telemetry_service.is_suppressed():
        raise HTTPException(
            status_code=403,
            detail="Telemetry is disabled at the server level via the NOTEL environment variable.",
        )

    settings_service.set_value(db, "telemetry_enabled", "true")
    telemetry_id = telemetry_service.get_or_create_id(db)

    if (telemetry_service.within_min_gap(db)):
        logger.info(
            "Telemetry: last heartbeat within 23 h, sending new UUID heartbeat anyways"
        )
        telemetry_service.send_heartbeat(db, telemetry_id)
    else:
        telemetry_service.send_heartbeat(db, telemetry_id)

    return {"enabled": True, "id": telemetry_id}


@router.post("/disable")
def disable_telemetry(db: Session = Depends(get_db)):
    settings_service.set_value(db, "telemetry_enabled", "false")
    telemetry_service.delete_id(db)

    return {"enabled": False}
