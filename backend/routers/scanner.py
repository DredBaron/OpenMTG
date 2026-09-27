from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from features import is_enabled

# Card search has no endpoints of its own: the page uses the shared /cards and /collection
# endpoints that Add Card also needs, so only its status lives here. If card-search-only endpoints
# are ever added, put them on a router with Depends(require_feature("card_search_enabled")).
router = APIRouter(prefix="/card-search", tags=["card-search"])


@router.get("/status")
def card_search_status(db: Session = Depends(get_db)):
    return {"enabled": is_enabled(db, "card_search_enabled")}
