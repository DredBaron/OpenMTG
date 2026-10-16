import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from features import is_enabled, require_feature
from limiter import limiter, user_or_ip_key
from security import get_current_user
import models
import services.settings as settings_service
import services.webhook_target as webhook_target
import services.webhooks as webhooks

# /status stays reachable while the feature is off; main.py registers it before `router`.
# Authentication runs before the feature check so an anonymous caller still gets 401.
status_router = APIRouter(prefix="/webhooks", tags=["webhooks"])
router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
    dependencies=[
        Depends(get_current_user),
        Depends(require_feature("home_assistant_integration_enabled")),
    ],
)


class WebhookCredentialCreate(BaseModel):
    label: str
    target_url: str | None = None
    verify_tls: bool = True


class WebhookCredentialUpdate(BaseModel):
    label: str | None = None
    target_url: str | None = None
    enabled: bool | None = None
    verify_tls: bool | None = None


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
    if not target_url:
        return
    try:
        webhook_target.validate(target_url)
    except webhook_target.UnsafeTargetError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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


@status_router.get("/status")
def webhook_status(db: Session = Depends(get_db)):
    return {
        "enabled":      is_enabled(db, "home_assistant_integration_enabled"),
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


TEST_PUSH_RATE_LIMIT = "5/minute"


@router.post("/{credential_id}/test")
@limiter.limit(TEST_PUSH_RATE_LIMIT, key_func=user_or_ip_key)
def test_credential(
    request: Request,
    credential_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    cred = _get_own_credential(credential_id, current_user, db)
    if not cred.target_url:
        raise HTTPException(status_code=400, detail="No target URL configured for this credential")
    # Report a bad URL (e.g. one saved before targets were validated) instead of failing silently.
    _validate_target_url(cred.target_url)

    webhooks.notify_test_event(cred)
    return {"message": "Test event sent"}
