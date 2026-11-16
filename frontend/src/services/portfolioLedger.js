export const currencyForTicker = (ticker, currency = 'USD') => {
  const normalizedTicker = String(ticker || '').toUpperCase().trim();
  return normalizedTicker.endsWith('.NS') || normalizedTicker.endsWith('.BO') ? 'INR' : String(currency).toUpperCase();
};

export const positionKey = (row) => JSON.stringify([
  row.portfolio_id || null, row.account_id || null,
  String(row.ticker || '').toUpperCase().trim(), currencyForTicker(row.ticker, row.currency || 'USD'),
]);

const sortTransactions = (transactions) => [...transactions].sort((a, b) => {
  const dateOrder = String(a.transaction_date || '').localeCompare(String(b.transaction_date || ''));
  return dateOrder || String(a.created_at || '').localeCompare(String(b.created_at || ''))
    || String(a.id || '').localeCompare(String(b.id || ''));
});

/** Opening positions precede all recorded activity. Never persist this derived result as holdings. */
export const derivePortfolioFromTransactions = (transactions = [], openingHoldings = []) => {
  const positions = new Map();
  const summary = { realizedPnl: 0, dividends: 0, fees: 0, byCurrency: {} };
  const errors = [];
  const getPosition = (row) => {
    const key = positionKey(row);
    if (!positions.has(key)) positions.set(key, {
      id: key, portfolio_id: row.portfolio_id || null, account_id: row.account_id || null,
      ticker: String(row.ticker || '').toUpperCase().trim(), currency: currencyForTicker(row.ticker, row.currency || 'USD'),
      quantity: 0, totalCost: 0, average_cost: 0, transactionDerived: false,
      source: { type: 'opening', holdingIds: [], transactionIds: [] },
    });
    return positions.get(key);
  };
  for (const holding of openingHoldings) {
    const current = getPosition(holding);
    current.quantity += Number(holding.quantity);
    current.totalCost += Number(holding.quantity) * Number(holding.average_cost);
    current.average_cost = current.quantity > 0 ? current.totalCost / current.quantity : 0;
    if (holding.id) current.source.holdingIds.push(holding.id);
  }

  sortTransactions(transactions).forEach((transaction) => {
    const ticker = String(transaction.ticker || '').toUpperCase().trim();
    const type = transaction.transaction_type;
    const quantity = Number(transaction.quantity || 0);
    const price = Number(transaction.price || 0);
    const fees = Number(transaction.fees || 0);
    const currency = currencyForTicker(ticker, transaction.currency || 'USD');
    const currencySummary = summary.byCurrency[currency] || { realizedPnl: 0, dividends: 0, fees: 0 };
    summary.byCurrency[currency] = currencySummary;

    if (!ticker) {
      if (type === 'dividend') {
        summary.dividends += price;
        currencySummary.dividends += price;
      } else if (type === 'fee') {
        summary.fees += price + fees;
        currencySummary.fees += price + fees;
      }
      return;
    }

    const current = getPosition(transaction);
    if (type === 'sell' && quantity > current.quantity + 1e-9) {
      errors.push({ transaction, available: current.quantity,
        message: `Cannot sell ${quantity} ${ticker}; only ${current.quantity} ${ticker} are available in ${currency} for this portfolio/account.` });
      return; // Surface invalid imported history; never silently clamp a sell.
    }
    current.transactionDerived = true;
    current.source.type = current.source.holdingIds.length ? 'opening_and_transactions' : 'transactions';
    if (transaction.id) current.source.transactionIds.push(transaction.id);

    if (type === 'buy' || type === 'transfer') {
      current.totalCost += quantity * price + fees;
      current.quantity += quantity;
      current.average_cost = current.quantity > 0 ? current.totalCost / current.quantity : 0;
    } else if (type === 'sell') {
      const soldQuantity = Math.min(quantity, current.quantity);
      const realizedPnl = soldQuantity * (price - current.average_cost) - fees;
      summary.realizedPnl += realizedPnl;
      currencySummary.realizedPnl += realizedPnl;
      current.totalCost = Math.max(0, current.totalCost - soldQuantity * current.average_cost);
      current.quantity = Math.max(0, current.quantity - soldQuantity);
      current.average_cost = current.quantity > 0 ? current.totalCost / current.quantity : 0;
    } else if (type === 'dividend') {
      summary.dividends += price;
      currencySummary.dividends += price;
    } else if (type === 'fee') {
      summary.fees += price + fees;
      currencySummary.fees += price + fees;
    }
  });

  return {
    holdings: [...positions.values()]
      .filter((position) => position.quantity > 0)
      .map(({ totalCost, ...position }) => ({ ...position, cost_basis: totalCost })),
    summary,
    errors,
  };
};

/** Return the first transaction that attempts to sell more than available. */
export const validateTransactionLedger = (transactions = [], openingHoldings = []) =>
  derivePortfolioFromTransactions(transactions, openingHoldings).errors[0] || null;
