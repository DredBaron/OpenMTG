export function formatPrice(value, currency, market) {
  if (value == null) return '-'
  const symbol = market?.symbol || currency.toUpperCase()
  return `${symbol}${Number(value).toFixed(2)}`
}

export function resolvePrice(card, currency, foil = false, market = null) {
  const direct = card?.[`price_${currency}${foil ? '_foil' : ''}`]
  if (direct != null) return direct
  if (market?.convert_from && market?.rate != null) {
    const base = card?.[`price_${market.convert_from}${foil ? '_foil' : ''}`]
    if (base != null) return parseFloat((base * market.rate).toFixed(6))
  }
  return null
}
