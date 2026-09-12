from services.market_scryfall import ScryfallMarket

MARKETS = {
    "usd": {
        "symbol":  "$",
        "display": "USD",
        "adapter": ScryfallMarket,
    },
    "eur": {
        "symbol":  "€",
        "display": "EUR",
        "adapter": ScryfallMarket,
    },
}


def resolve_base_currency_and_rate(db, currency: str) -> tuple[str, float, str]:
    if currency in MARKETS:
        return currency, 1.0, currency

    from models import ConvertedCurrency
    db_curr = db.query(ConvertedCurrency).filter_by(code=currency.upper()).first()
    if db_curr and db_curr.rate:
        return "usd", db_curr.rate, currency
    return "usd", 1.0, "usd"
