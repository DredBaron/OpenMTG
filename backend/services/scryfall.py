import httpx
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models.models as models

SCRYFALL_BASE = "https://api.scryfall.com"
CACHE_TTL_DAYS = 7  # Refresh card data after 7 days


def _card_from_scryfall(data: dict) -> dict:
    """Pull only the fields we care about from a Scryfall card object."""
    prices = data.get("prices", {})
    image_uris = data.get("image_uris", {})

    # Double-faced cards store images differently
    if not image_uris and "card_faces" in data:
        image_uris = data["card_faces"][0].get("image_uris", {})

    colors = data.get("colors", [])
    color_identity = data.get("color_identity", [])

    return {
        "scryfall_id":       data["id"],
        "name":              data.get("name", ""),
        "set_code":          data.get("set", ""),
        "set_name":          data.get("set_name", ""),
        "collector_number":  data.get("collector_number", ""),
        "rarity":            data.get("rarity", ""),
        "type_line":         data.get("type_line", ""),
        "oracle_text":       data.get("oracle_text", ""),
        "mana_cost":         data.get("mana_cost", ""),
        "colors":            "".join(colors),
        "color_identity":    "".join(color_identity),
        "image_uri":         image_uris.get("normal", ""),
        "image_uri_small":   image_uris.get("small", ""),
        "price_usd":         float(prices["usd"]) if prices.get("usd") else None,
        "price_usd_foil":    float(prices["usd_foil"]) if prices.get("usd_foil") else None,
        "price_eur":         float(prices["eur"]) if prices.get("eur") else None,
        "last_fetched":      datetime.utcnow(),
    }


def _upsert_card(db: Session, scryfall_data: dict) -> models.Card:
    """Insert or update a card in our local cache."""
    fields = _card_from_scryfall(scryfall_data)
    card = db.query(models.Card).filter(
        models.Card.scryfall_id == fields["scryfall_id"]
    ).first()

    if card:
        for k, v in fields.items():
            setattr(card, k, v)
    else:
        card = models.Card(**fields)
        db.add(card)

    db.commit()
    db.refresh(card)
    return card


def search_cards(query: str, db: Session) -> list[dict]:
    """Search Scryfall and cache any results we get back."""
    with httpx.Client() as client:
        r = client.get(
            f"{SCRYFALL_BASE}/cards/search",
            params={"q": query, "order": "name"},
            timeout=10,
        )
    if r.status_code == 404:
        return []  # No results found
    r.raise_for_status()

    cards = []
    for card_data in r.json().get("data", []):
        card = _upsert_card(db, card_data)
        cards.append(card)
    return cards


def get_card_by_scryfall_id(scryfall_id: str, db: Session) -> models.Card | None:
    """Get a card by Scryfall ID, using local cache if fresh enough."""
    card = db.query(models.Card).filter(
        models.Card.scryfall_id == scryfall_id
    ).first()

    # Return cached version if fetched recently
    if card and card.last_fetched:
        age = datetime.utcnow() - card.last_fetched.replace(tzinfo=None)
        if age < timedelta(days=CACHE_TTL_DAYS):
            return card

    # Otherwise fetch fresh from Scryfall
    with httpx.Client() as client:
        r = client.get(f"{SCRYFALL_BASE}/cards/{scryfall_id}", timeout=10)
    if r.status_code == 404:
        return None
    r.raise_for_status()

    return _upsert_card(db, r.json())


def get_card_by_name(name: str, db: Session) -> models.Card | None:
    """Fuzzy name lookup — great for scanner results."""
    with httpx.Client() as client:
        r = client.get(
            f"{SCRYFALL_BASE}/cards/named",
            params={"fuzzy": name},
            timeout=10,
        )
    if r.status_code == 404:
        return None
    r.raise_for_status()

    return _upsert_card(db, r.json())

def get_card_printings(card_name: str) -> list[dict]:
    """
    Fetch all printings of a card by exact name.
    Returns a slim list with just the fields needed for the set picker.
    """
    with httpx.Client() as client:
        r = client.get(
            f"{SCRYFALL_BASE}/cards/search",
            params={
                "q": f'!"{card_name}"',
                "unique": "prints",
                "order": "released",
                "dir": "desc",
            },
            timeout=10,
        )
    if r.status_code == 404:
        return []
    r.raise_for_status()

    printings = []
    for card in r.json().get("data", []):
        prices = card.get("prices", {})
        image_uris = card.get("image_uris", {})
        if not image_uris and "card_faces" in card:
            image_uris = card["card_faces"][0].get("image_uris", {})
        printings.append({
            "scryfall_id":      card["id"],
            "set_code":         card["set"],
            "set_name":         card["set_name"],
            "collector_number": card["collector_number"],
            "rarity":           card["rarity"],
            "released_at":      card.get("released_at", ""),
            "image_uri":        image_uris.get("normal", ""),
            "price_usd":        float(prices["usd"]) if prices.get("usd") else None,
            "price_usd_foil":   float(prices["usd_foil"]) if prices.get("usd_foil") else None,
        })
    return printings
