from pydantic import BaseModel, EmailStr, ConfigDict
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
    model_config = ConfigDict(from_attributes=True)

# --- Admin ---

class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    is_admin: bool = False

class UpdateUserRequest(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None
    password: str | None = None


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
    colors: str | None
    image_uri: str | None
    price_usd: float | None
    price_usd_foil: float | None
    model_config = ConfigDict(from_attributes=True)


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
    model_config = ConfigDict(from_attributes=True)

class AddCardRequest(BaseModel):
    scryfall_id: str
    quantity: int = 1
    foil: bool = False
    condition: str = "NM"
    language: str = "en"
    notes: str | None = None

class UpdateCardRequest(BaseModel):
    quantity: int | None = None
    foil: bool | None = None
    condition: str | None = None
    language: str | None = None
    notes: str | None = None
    scryfall_id: str | None = None
    is_favorite: bool | None = None

class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]

class ImportRequest(BaseModel):
    list_text: str
    condition: str = "NM"
    foil: bool = False

# --- Decks ---

class DeckOut(BaseModel):
    id: int
    name: str
    format: str | None
    description: str | None
    is_public: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DeckCardOut(BaseModel):
    id: int
    quantity: int
    is_sideboard: bool
    is_commander: bool
    card: CardOut
    model_config = ConfigDict(from_attributes=True)


class DeckDetailOut(BaseModel):
    id: int
    name: str
    format: str | None
    description: str | None
    is_public: bool
    created_at: datetime
    cards: list[DeckCardOut]
    model_config = ConfigDict(from_attributes=True)

class CreateDeckRequest(BaseModel):
    name: str
    format: str | None = None
    description: str | None = None
    is_public: bool = False

class UpdateDeckRequest(BaseModel):
    name: str | None = None
    format: str | None = None
    description: str | None = None
    is_public: bool | None = None

class AddDeckCardRequest(BaseModel):
    scryfall_id: str
    quantity: int = 1
    is_sideboard: bool = False
    is_commander: bool = False

class UpdateDeckCardRequest(BaseModel):
    quantity: int | None = None
    is_sideboard: bool | None = None
    is_commander: bool | None = None

# --- Settings ---

class SettingsUpdate(BaseModel):
    price_refresh_hours: int | None = None
    scryfall_rps:        int | None = None