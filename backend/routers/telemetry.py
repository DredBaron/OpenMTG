from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from security import get_current_user
import models
import services.settings as settings_service
import services.telemetry as telemetry_service


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

    return {
        "suppressed": suppressed,
        "enabled":    enabled,
        "id":         telemetry_id,
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

    telemetry_service.send_heartbeat(telemetry_id)

    return {"enabled": True, "id": telemetry_id}


@router.post("/disable")
def disable_telemetry(db: Session = Depends(get_db)):
    settings_service.set_value(db, "telemetry_enabled", "false")
    telemetry_service.delete_id(db)

    return {"enabled": False}
