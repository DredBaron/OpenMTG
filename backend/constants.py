CONDITION_MULTIPLIERS = {
    "NM":  1.0,
    "LP":  0.75,
    "MP":  0.50,
    "HP":  0.25,
    "DMG": 0.10,
}

PRICE_FIELDS: dict[str, tuple[str, str]] = {
    "usd": ("price_usd", "price_usd_foil"),
    "eur": ("price_eur", "price_eur_foil"),
}

VERSIONS = {
    "API_VERSION": "1.6.0",
    "APPLICATION_VERSION": "1.6.0",
}

API_RATES = {
    "RATE_LIMIT_RPS": "2",
    "RATE_LIMIT_GAP": "0.5",
    "ERROR_429_BACKOFF": "60",
    "CALLER_TIMEOUT": "30",
}