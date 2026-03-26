from pydantic import BaseModel, EmailStr
from datetime import datetime


# --- Auth ---

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Cards ---

class CardOut(BaseModel):
    id: int
    scryfall_id: str
    name: str
    set_code: str
    set_name: str | None
    collector_number: str | None
    rarity: str | None
    type_line: str | None
    oracle_text: str | None
    mana_cost: str | None
    image_uri: str | None
    price_usd: float | None
    price_usd_foil: float | None

    class Config:
        from_attributes = True


# --- Collection ---

class CollectionEntryOut(BaseModel):
    id: int
    quantity: int
    foil: bool
    condition: str
    language: str
    notes: str | None
    is_favorite: bool
    card: CardOut

    class Config:
        from_attributes = True


# --- Decks ---

class DeckOut(BaseModel):
    id: int
    name: str
    format: str | None
    description: str | None
    is_public: bool
    created_at: datetime

    class Config:
        from_attributes = True

class DeckCardOut(BaseModel):
    id: int
    quantity: int
    is_sideboard: bool
    is_commander: bool
    card: CardOut

    class Config:
        from_attributes = True


class DeckDetailOut(BaseModel):
    id: int
    name: str
    format: str | None
    description: str | None
    is_public: bool
    created_at: datetime
    cards: list[DeckCardOut]

    class Config:
        from_attributes = True
