import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from security import get_current_user
import models
import services.settings as settings_service
import services.webhooks as webhooks

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookCredentialCreate(BaseModel):
    label: str
    target_url: str | None = None
    verify_tls: bool = True


class WebhookCredentialUpdate(BaseModel):
    label: str | None = None
    target_url: str | None = None
    enabled: bool | None = None
    verify_tls: bool | None = None


def _require_enabled(db: Session) -> None:
    if settings_service.get(db, "home_assistant_integration_enabled") != "true":
        raise HTTPException(status_code=403, detail="Home Assistant integration is disabled")


def _get_own_credential(credential_id: int, current_user: models.User, db: Session) -> models.WebhookCredential:
    cred = (
        db.query(models.WebhookCredential)
        .filter_by(id=credential_id, user_id=current_user.id)
        .first()
    )
    if not cred:
        raise HTTPException(status_code=404, detail="Webhook credential not found")
    return cred


def _validate_target_url(target_url: str | None) -> None:
    if target_url and not target_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Target URL must start with http:// or https://")


def _serialize(cred: models.WebhookCredential) -> dict:
    return {
        "id":           cred.id,
        "label":        cred.label,
        "webhook_id":   cred.webhook_id,
        "target_url":   cred.target_url,
        "enabled":      cred.enabled,
        "verify_tls":   cred.verify_tls,
        "created_at":   cred.created_at.isoformat() if cred.created_at else None,
        "last_used_at": cred.last_used_at.isoformat() if cred.last_used_at else None,
    }


@router.get("/status")
def webhook_status(db: Session = Depends(get_db)):
    return {
        "enabled":      settings_service.get(db, "home_assistant_integration_enabled") == "true",
        "max_per_user": settings_service.get_int(db, "home_assistant_max_credentials_per_user"),
    }


@router.get("")
def list_credentials(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    creds = (
        db.query(models.WebhookCredential)
        .filter_by(user_id=current_user.id)
        .order_by(models.WebhookCredential.created_at.desc())
        .all()
    )
    return [_serialize(c) for c in creds]


@router.post("", status_code=201)
def create_credential(
    body: WebhookCredentialCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _require_enabled(db)
    _validate_target_url(body.target_url)

    max_per_user = settings_service.get_int(db, "home_assistant_max_credentials_per_user")
    existing = db.query(models.WebhookCredential).filter_by(user_id=current_user.id).count()
    if existing >= max_per_user:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {max_per_user} webhook credentials reached",
        )

    if not body.label.strip():
        raise HTTPException(status_code=400, detail="Label is required")

    secret = secrets.token_urlsafe(32)
    cred = models.WebhookCredential(
        user_id=current_user.id,
        label=body.label.strip(),
        webhook_id=secrets.token_urlsafe(24),
        secret_hash=hashlib.sha256(secret.encode()).hexdigest(),
        target_url=body.target_url or None,
        verify_tls=body.verify_tls,
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)

    return {
        **_serialize(cred),
        "secret": secret,
        "inbound_url": f"/api/webhook/{current_user.username}/{cred.webhook_id}/stats",
    }


@router.patch("/{credential_id}")
def update_credential(
    credential_id: int,
    body: WebhookCredentialUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    cred = _get_own_credential(credential_id, current_user, db)

    if body.target_url is not None:
        _validate_target_url(body.target_url)
        cred.target_url = body.target_url or None
    if body.label is not None:
        if not body.label.strip():
            raise HTTPException(status_code=400, detail="Label is required")
        cred.label = body.label.strip()
    if body.enabled is not None:
        cred.enabled = body.enabled
    if body.verify_tls is not None:
        cred.verify_tls = body.verify_tls

    db.commit()
    db.refresh(cred)
    return _serialize(cred)


@router.delete("/{credential_id}", status_code=204)
def delete_credential(
    credential_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    cred = _get_own_credential(credential_id, current_user, db)
    db.delete(cred)
    db.commit()


@router.post("/{credential_id}/regenerate-secret")
def regenerate_secret(
    credential_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    cred = _get_own_credential(credential_id, current_user, db)

    secret = secrets.token_urlsafe(32)
    cred.secret_hash = hashlib.sha256(secret.encode()).hexdigest()
    db.commit()
    db.refresh(cred)

    return {**_serialize(cred), "secret": secret}


@router.post("/{credential_id}/test")
def test_credential(
    credential_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _require_enabled(db)
    cred = _get_own_credential(credential_id, current_user, db)
    if not cred.target_url:
        raise HTTPException(status_code=400, detail="No target URL configured for this credential")

    webhooks.notify_test_event(cred)
    return {"message": "Test event sent"}
