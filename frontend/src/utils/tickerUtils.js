export function normalizeExchangeSuffix(symbol) {
  return symbol.trim().toUpperCase().replace(/\.NSE$/, '.NS').replace(/\.BSE$/, '.BO');
}

/**
 * Normalize watchlist symbols.
 *
 * The app is designed to support both curated universe assets and any live ticker the
 * user wants to track. We keep the India suffix heuristic for common NSE symbols
 * (e.g. RELIANCE -> RELIANCE.NS), but we never block a valid symbol just because it is
 * not in the curated ML universe.
 */
const COMPANY_ALIASES = {
  'ONE 97 COMMUNICATIONS LTD': 'PAYTM.NS',
  'ONE97 COMMUNICATIONS LTD': 'PAYTM.NS',
  'ONE 97 COMMUNICATIONS': 'PAYTM.NS',
  'ONE97 COMMUNICATIONS': 'PAYTM.NS',
  'PAYTM': 'PAYTM.NS',
  'PAYTM LTD': 'PAYTM.NS',
};

export function normalizeTickerSymbol(input, { readySymbols = [], universeSymbols = [] } = {}) {
  const raw = (input || '').trim();
  if (!raw) return raw;

  const normalizedKey = raw
    .toUpperCase()
    .replace(/&/g, ' AND ')
    .replace(/[^A-Z0-9 ]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  if (COMPANY_ALIASES[normalizedKey]) {
    return COMPANY_ALIASES[normalizedKey];
  }

  const t = normalizeExchangeSuffix(raw);
  const sanitized = t.replace(/[^A-Z0-9.\-]/g, '');
  if (!sanitized) return '';
  if (sanitized.includes('.')) return sanitized;

  const suffixVariants = [`${sanitized}.NS`, `${sanitized}.BO`, `${sanitized}.NSE`, `${sanitized}.BSE`];
  const ready = new Set(readySymbols.map((s) => s.toUpperCase()));
  const universe = new Set(universeSymbols.map((s) => s.toUpperCase()));

  for (const candidate of suffixVariants) {
    if (ready.has(candidate) || universe.has(candidate)) return normalizeExchangeSuffix(candidate);
  }

  return sanitized;
}
