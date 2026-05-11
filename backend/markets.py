from services.market_scryfall import ScryfallMarket

MARKETS = {
    "usd": {
        "symbol":           "$",
        "display":          "USD",
        "adapter":          ScryfallMarket,
        "supports_history": False,
    },
    "eur": {
        "symbol":           "€",
        "display":          "EUR",
        "adapter":          ScryfallMarket,
        "supports_history": False,
    },
}
