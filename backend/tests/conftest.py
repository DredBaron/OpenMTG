from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import Base, get_db

patch("services.price_refresh.start_scheduler", lambda: None).start()

from main import app
import models
from security import hash_password, create_access_token

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
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
    token = create_access_token({"sub": user.username})
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
