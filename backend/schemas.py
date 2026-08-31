from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator
from datetime import datetime

# Auth

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(min_length=8)

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
    preferred_currency: str
    model_config = ConfigDict(from_attributes=True)

# Admin

class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str = Field(min_length=8)
    is_admin: bool = False

class UpdateUserRequest(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None
    password: str | None = Field(default=None, min_length=8)
    preferred_currency: str | None = None

class CurrencyUpdate(BaseModel):
    preferred_currency: str

# Converted currencies (admin-managed)

class ConvertedCurrencyOut(BaseModel):
    code: str
    symbol: str
    rate: float | None
    rate_updated_at: datetime | None
    model_config = ConfigDict(from_attributes=True)

class AddCurrencyRequest(BaseModel):
    code: str
    symbol: str

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.isalpha() or len(v) != 3:
            raise ValueError("Currency code must be exactly 3 letters")
        return v

class UpdateCurrencyRequest(BaseModel):
    symbol: str

# Cards

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
    price_eur: float | None
    price_usd_foil: float | None
    price_eur_foil: float | None
    model_config = ConfigDict(from_attributes=True)


# Card Photos

class CardPhotoOut(BaseModel):
    side: str
    model_config = ConfigDict(from_attributes=True)

# Collection

class CollectionEntryOut(BaseModel):
    id: int
    quantity: int
    foil: bool
    condition: str
    language: str
    notes: str | None
    is_favorite: bool
    in_showroom: bool
    on_loan: bool
    loaned_to: str | None
    loan_date: datetime | None
    in_decks: int = 0
    photos: list[CardPhotoOut] = []
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
    in_showroom: bool | None = None
    on_loan: bool | None = None
    loaned_to: str | None = None
    loan_date: datetime | None = None

class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]

class ImportRequest(BaseModel):
    list_text: str
    condition: str = "NM"
    foil: bool = False

# Decks

class DeckPreviewCard(BaseModel):
    scryfall_id: str
    is_commander: bool
    model_config = ConfigDict(from_attributes=True)

class DeckOut(BaseModel):
    id: int
    name: str
    format: str | None
    description: str | None
    is_public: bool
    created_at: datetime
    card_count: int = 0
    preview_cards: list[DeckPreviewCard] = []
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

class DeckImportRequest(BaseModel):
    name: str
    format: str | None = None
    description: str | None = None
    list_text: str

class DeckImportResult(BaseModel):
    deck_id: int
    deck_name: str
    imported: int
    skipped: int
    errors: list[str]

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
    scryfall_id: str | None = None

# Showroom

class ShowroomPreviewCard(BaseModel):
    scryfall_id: str
    is_commander: bool
    model_config = ConfigDict(from_attributes=True)

class ShowroomDeckOut(BaseModel):
    id: int
    name: str
    format: str | None
    description: str | None
    card_count: int
    preview_cards: list[ShowroomPreviewCard]
    model_config = ConfigDict(from_attributes=True)

class ShowroomCardOut(BaseModel):
    id: int
    name: str
    image_uri: str | None
    foil: bool
    model_config = ConfigDict(from_attributes=True)

class ShowroomOut(BaseModel):
    decks: list[ShowroomDeckOut]
    cards: list[ShowroomCardOut]

# Trades

class TradeItemIn(BaseModel):
    collection_entry_id: int
    quantity: int = 1

class ProposeTradeRequest(BaseModel):
    counterpart_username: str
    items: list[TradeItemIn]

class UpdateTradeItemsRequest(BaseModel):
    items: list[TradeItemIn]

class TradeItemOut(BaseModel):
    id: int
    user_id: int
    collection_entry_id: int
    quantity: int
    card_snapshot_name: str | None
    card_snapshot_image: str | None
    card_snapshot_price: float | None
    foil: bool
    condition: str
    model_config = ConfigDict(from_attributes=True)

class TradeOut(BaseModel):
    id: int
    initiator_id: int
    counterpart_id: int
    status: str
    initiator_confirmed: bool
    counterpart_confirmed: bool
    last_actor_id: int | None
    my_items: list[TradeItemOut] = []
    their_items: list[TradeItemOut] = []
    initiator_username: str
    counterpart_username: str
    created_at: datetime
    updated_at: datetime | None
    model_config = ConfigDict(from_attributes=True)

class TradeListItemOut(BaseModel):
    id: int
    status: str
    other_username: str
    initiator_confirmed: bool
    counterpart_confirmed: bool
    is_my_turn: bool
    updated_at: datetime | None
    model_config = ConfigDict(from_attributes=True)

# Settings

class SettingsUpdate(BaseModel):
    price_refresh_hours: int | None = None
    price_history_days: int | None = None
    showroom_enabled: bool | None = None
    card_search_enabled: bool | None = None
    trades_enabled: bool | None = None