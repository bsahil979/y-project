import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import {
  currencyForTicker,
  derivePortfolioFromTransactions,
  validateTransactionLedger,
} from '../src/services/portfolioLedger.js';

const transaction = (overrides) => ({
  transaction_date: '2026-01-01',
  quantity: 0,
  price: 0,
  fees: 0,
  currency: 'USD',
  ...overrides,
});

describe('portfolio ledger', () => {
  it('normalizes Indian exchange symbols to INR', () => {
    assert.equal(currencyForTicker(' tcs.ns '), 'INR');
    assert.equal(currencyForTicker('RELIANCE.BO'), 'INR');
    assert.equal(currencyForTicker('AAPL', 'EUR'), 'EUR');
  });

  it('derives weighted-average cost and realized P/L including fees', () => {
    const result = derivePortfolioFromTransactions([
      transaction({ transaction_type: 'buy', ticker: 'AAPL', quantity: 2, price: 100, fees: 2 }),
      transaction({ transaction_type: 'buy', ticker: 'AAPL', quantity: 2, price: 120, fees: 2, transaction_date: '2026-01-02' }),
      transaction({ transaction_type: 'sell', ticker: 'AAPL', quantity: 1, price: 150, fees: 3, transaction_date: '2026-01-03' }),
    ]);

    assert.equal(result.holdings.length, 1);
    assert.equal(result.holdings[0].ticker, 'AAPL');
    assert.equal(result.holdings[0].quantity, 3);
    assert.equal(result.holdings[0].cost_basis, 333);
    assert.equal(result.holdings[0].average_cost, 111);
    assert.equal(result.summary.realizedPnl, 36);
    assert.equal(result.summary.byCurrency.USD.realizedPnl, 36);
  });

  it('accepts transfers as inventory without treating them as purchases', () => {
    const result = derivePortfolioFromTransactions([
      transaction({ transaction_type: 'transfer', ticker: 'MSFT', quantity: 4, price: 80 }),
      transaction({ transaction_type: 'sell', ticker: 'MSFT', quantity: 1, price: 100, fees: 1, transaction_date: '2026-01-02' }),
    ]);

    assert.equal(result.holdings[0].quantity, 3);
    assert.equal(result.holdings[0].cost_basis, 240);
    assert.equal(result.summary.realizedPnl, 19);
  });

  it('records cash-only dividends and fees by currency', () => {
    const result = derivePortfolioFromTransactions([
      transaction({ transaction_type: 'dividend', ticker: '', price: 12.5 }),
      transaction({ transaction_type: 'fee', ticker: null, price: 2, fees: 0.5, currency: 'EUR' }),
    ]);

    assert.equal(result.holdings.length, 0);
    assert.equal(result.summary.dividends, 12.5);
    assert.equal(result.summary.fees, 2.5);
    assert.equal(result.summary.byCurrency.USD.dividends, 12.5);
    assert.equal(result.summary.byCurrency.EUR.fees, 2.5);
  });

  it('keeps positions with the same ticker separate by currency', () => {
    const result = derivePortfolioFromTransactions([
      transaction({ transaction_type: 'buy', ticker: 'ABC', quantity: 1, price: 10, currency: 'USD' }),
      transaction({ transaction_type: 'buy', ticker: 'ABC', quantity: 2, price: 20, currency: 'INR' }),
    ]);

    assert.equal(result.holdings.length, 2);
    assert.deepEqual(
      result.holdings.map(({ ticker, quantity, currency }) => ({ ticker, quantity, currency })),
      [
        { ticker: 'ABC', quantity: 1, currency: 'USD' },
        { ticker: 'ABC', quantity: 2, currency: 'INR' },
      ],
    );
  });

  it('returns the first oversell with available quantity', () => {
    const oversell = transaction({ transaction_type: 'sell', ticker: 'AAPL', quantity: 3, price: 100, transaction_date: '2026-01-02' });
    const error = validateTransactionLedger([
      transaction({ transaction_type: 'buy', ticker: 'AAPL', quantity: 2, price: 100 }),
      oversell,
    ]);

    assert.equal(error.transaction, oversell);
    assert.equal(error.available, 2);
    assert.match(error.message, /only 2 AAPL are available in USD/);
  });

  it('allows an exact sell and ignores cash-only transactions during inventory validation', () => {
    assert.equal(validateTransactionLedger([
      transaction({ transaction_type: 'dividend', ticker: null, price: 10 }),
      transaction({ transaction_type: 'buy', ticker: 'AAPL', quantity: 2, price: 100 }),
      transaction({ transaction_type: 'sell', ticker: 'AAPL', quantity: 2, price: 110, transaction_date: '2026-01-02' }),
    ]), null);
  });
});