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
