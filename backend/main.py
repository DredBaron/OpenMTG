from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from routers import auth, cards, collections, decks, export, admin, settings
from limiter import limiter
from services.price_refresh import start_scheduler
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="OpenMTG")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.on_event("startup")
def startup():
    start_scheduler()


app.include_router(auth.router)
app.include_router(cards.router)
app.include_router(collections.router)
app.include_router(decks.router)
app.include_router(export.router)
app.include_router(admin.router)
app.include_router(settings.router)


@app.get("/health")
def health():
    return {"status": "ok"}
