from contextlib import asynccontextmanager
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from routers import auth, cards, collections, decks, export, admin, settings, telemetry
from limiter import limiter
from services.price_refresh import start_scheduler as start_price_scheduler
from services.telemetry import start_scheduler as start_telemetry_scheduler
import logging

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_price_scheduler()
    yield


app = FastAPI(title="OpenMTG", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router)
app.include_router(cards.router)
app.include_router(collections.router)
app.include_router(decks.router)
app.include_router(export.router)
app.include_router(admin.router)
app.include_router(settings.router)
app.include_router(telemetry.router)

@app.get("/health")
def health():
    return {"status": "ok"}
