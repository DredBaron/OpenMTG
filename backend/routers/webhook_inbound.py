import hashlib
import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from database import get_db
from limiter import limiter
import models
import services.settings as settings_service
from routers.collections import compute_collection_stats

router = APIRouter(prefix="/webhook", tags=["webhook"])


def _authenticate(
    db: Session, username: str, webhook_id: str, authorization: str | None
) -> models.WebhookCredential:
    if settings_service.get(db, "home_assistant_integration_enabled") != "true":
        raise HTTPException(status_code=503, detail="Home Assistant integration is disabled")

    cred = (
        db.query(models.WebhookCredential)
        .options(joinedload(models.WebhookCredential.owner))
        .filter_by(webhook_id=webhook_id)
        .first()
    )
    if not cred or not cred.enabled or not cred.owner or cred.owner.username != username:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    presented = authorization.removeprefix("Bearer ").strip()
    presented_hash = hashlib.sha256(presented.encode()).hexdigest()
    if not hmac.compare_digest(presented_hash, cred.secret_hash):
        raise HTTPException(status_code=401, detail="Invalid bearer token")

    return cred


@router.get("/{username}/{webhook_id}/stats")
@limiter.limit("30/minute")
def pull_stats(
    request: Request,
    username: str,
    webhook_id: str,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    cred = _authenticate(db, username, webhook_id, authorization)

    cred.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return compute_collection_stats(db, cred.owner)
