class ScryfallMarket:
    _keys = {
        "usd": ("usd", "usd_foil"),
        "eur": ("eur", "eur_foil"),
    }

    @classmethod
    def extract_prices(cls, prices: dict) -> dict:
        result = {}
        for currency, (key, foil_key) in cls._keys.items():
            result[f"price_{currency}"]      = float(prices[key]) if prices.get(key) else None
            result[f"price_{currency}_foil"] = float(prices[foil_key]) if prices.get(foil_key) else None
        return result
