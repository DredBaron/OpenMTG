from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("TRADES_DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only!")

from database import Base, get_db
from database_trades import TradesBase, get_trades_db

patch("services.price_refresh.start_scheduler", lambda: None).start()
patch("services.telemetry.start_scheduler", lambda: None).start()
patch("services.trade_recovery.recover_processing_trades_on_startup", lambda: None).start()

from main import app
import models
import models.trade  # noqa: F401 (registers Trade/TradeItem on TradesBase)
from security import hash_password, create_user_token

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

trades_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingTradesSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=trades_engine)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    TradesBase.metadata.drop_all(bind=trades_engine)
    TradesBase.metadata.create_all(bind=trades_engine)
    yield
    Base.metadata.drop_all(bind=engine)
    TradesBase.metadata.drop_all(bind=trades_engine)


@pytest.fixture(autouse=True)
def isolate_config_path(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_PATH", str(tmp_path))


@pytest.fixture(autouse=True)
def reset_settings_cache():
    import services.settings as settings_service
    settings_service._cache = None
    yield
    settings_service._cache = None


@pytest.fixture(autouse=True)
def reset_rate_limits():
    from limiter import limiter
    limiter.reset()
    yield
    limiter.reset()


FAKE_PUBLIC_IP = "192.0.2.10"


@pytest.fixture(autouse=True)
def fake_dns(monkeypatch):
    """Tests never do real DNS for webhook targets. IP literals (in any form the system resolver
    accepts) resolve to themselves; host names resolve to FAKE_PUBLIC_IP unless the test adds an
    entry: a list of addresses, an exception to raise, or a callable returning a list."""
    import socket
    import services.webhook_target as webhook_target

    records = {}

    def resolve(host, port):
        try:
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, flags=socket.AI_NUMERICHOST)
            return list(dict.fromkeys(info[4][0] for info in infos))
        except socket.gaierror:
            pass
        answer = records.get(host.lower().rstrip("."), [FAKE_PUBLIC_IP])
        if isinstance(answer, BaseException):
            raise answer
        return list(answer() if callable(answer) else answer)

    monkeypatch.setattr(webhook_target, "_resolve", resolve)
    return records


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def trades_db():
    session = TestingTradesSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db, trades_db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_trades_db():
        try:
            yield trades_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_trades_db] = override_get_trades_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# helper: create a user directly in the DB

def make_user(db, username="testuser", password="password123",
              email="test@example.com", is_admin=False, is_active=True):
    user = models.User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        is_admin=is_admin,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(user):
    token = create_user_token(user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def regular_user(db):
    return make_user(db)


@pytest.fixture()
def admin_user(db):
    return make_user(db, username="admin", email="admin@example.com", is_admin=True)


@pytest.fixture()
def regular_headers(regular_user):
    return auth_headers(regular_user)


@pytest.fixture()
def admin_headers(admin_user):
    return auth_headers(admin_user)


# helper: minimal Card ORM object

def make_card(db, scryfall_id="abc-123", name="Lightning Bolt",
              set_code="M11", set_name="Magic 2011",
              collector_number="149", rarity="common",
              price_usd=0.25, price_usd_foil=1.00,
              color_identity="R", type_line="Instant",
              image_uri="https://example.com/bolt.jpg"):
    card = models.Card(
        scryfall_id=scryfall_id,
        name=name,
        set_code=set_code,
        set_name=set_name,
        collector_number=collector_number,
        rarity=rarity,
        price_usd=price_usd,
        price_usd_foil=price_usd_foil,
        color_identity=color_identity,
        type_line=type_line,
        image_uri=image_uri,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card
