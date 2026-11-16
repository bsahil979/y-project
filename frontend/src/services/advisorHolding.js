/** Match owned symbols, including company-name prefixes such as Reliance. */
export function holdingAnswer(query, snapshot, currency) {
  const tokens = query.toUpperCase().match(/[A-Z][A-Z0-9.-]*/g) || [];
  const matches = (snapshot?.holdings || []).filter((holding) => holding.currency === currency &&
    tokens.some((token) => token === holding.ticker || token === holding.ticker.replace(/\.(NS|BO)$/, '')));
  if (!matches.length) return null;
  const total = snapshot.valuation.groups[currency]?.market;
  return matches.map((holding) => {
    const money = (value) => Number.isFinite(value) ? new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format(value) : 'unavailable';
    const weight = total > 0 && holding.market_value != null ? ` It represents ${(holding.market_value / total * 100).toFixed(1)}% of your ${currency} holdings.` : '';
    return `${holding.ticker}: You own ${holding.quantity} shares at an average purchase cost of ${money(holding.average_cost)}. Current market value: ${money(holding.market_value)}. Unrealized profit/loss: ${money(holding.pnl)}.${weight}`;
  }).join('\n\n') + '\n\nThis is a recorded-holding summary. The language model is unavailable or turned off, so I cannot provide an LLM explanation.';
}
