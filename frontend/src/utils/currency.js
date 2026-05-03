export const CURRENCY_SYMBOLS = { usd: '$', eur: '€' }

export function formatPrice(value, currency = 'usd') {
  if (value == null) return '—'
  const symbol = CURRENCY_SYMBOLS[currency] || currency.toUpperCase()
  return `${symbol}${Number(value).toFixed(2)}`
}

export function resolvePrice(card, currency, foil = false) {
  if (currency === 'eur') {
    return foil ? card.price_eur_foil : card.price_eur
  }
  return foil ? card.price_usd_foil : card.price_usd
}
