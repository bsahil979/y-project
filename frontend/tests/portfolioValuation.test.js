import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { valuePortfolio, analysisRequest } from '../src/services/portfolioValuation.js';

const position = (ticker, quantity, average_cost, currency = 'INR') => ({ ticker, quantity, average_cost, currency });
const quote = (price, currency = 'INR') => ({ price, currency });

describe('portfolio valuation', () => {
  it('weights current values rather than equal purchase costs', () => {
    const group = valuePortfolio([position('A.NS', 10, 100), position('B.NS', 10, 100)], { 'A.NS': quote(200), 'B.NS': quote(50) }).groups.INR;
    assert.deepEqual(group.weights, [.8, .2]);
    assert.equal(group.market, 2500);
    assert.equal(group.pnl, 500);
    assert.equal(analysisRequest(group).portfolio_value, 2500);
    assert.equal(analysisRequest(group).benchmark, '^NSEI');
  });
  it('does not invent value or P/L when even one price is missing', () => {
    const group = valuePortfolio([position('A.NS', 1, 100), position('B.NS', 1, 100)], { 'A.NS': quote(120) }).groups.INR;
    assert.equal(group.market, null);
    assert.equal(group.pnl, null);
    assert.equal(group.cost, 200);
    assert.equal(analysisRequest(group), null);
    assert.equal(group.positions[1].market, null);
  });
  it('keeps currencies separate without a made-up exchange rate', () => {
    const result = valuePortfolio([position('A.NS', 1, 100), position('AAPL', 2, 100, 'USD')], { 'A.NS': quote(150), AAPL: quote(125, 'USD') });
    assert.equal(result.groups.INR.market, 150);
    assert.equal(result.groups.USD.market, 250);
    assert.deepEqual(analysisRequest(result.groups.USD).tickers, ['AAPL']);
  });
  it('rejects wrong currency, zero, negative, non-finite and errored quotes', () => {
    for (const bad of [quote(100, 'USD'), quote(0), quote(-1), quote(Infinity), quote(NaN), { ...quote(50), error: 'unavailable' }]) {
      assert.equal(analysisRequest(valuePortfolio([position('A.NS', 1, 10)], { 'A.NS': bad }).groups.INR), null);
    }
  });
  it('aggregates duplicate positions and includes zero-cost transferred holdings', () => {
    const group = valuePortfolio([position('A.NS', 1, 0), position('A.NS', 2, 50)], { 'A.NS': quote(100) }).groups.INR;
    assert.deepEqual(group.tickers, ['A.NS']);
    assert.deepEqual(group.weights, [1]);
    assert.equal(group.market, 300);
    assert.equal(group.cost, 100);
    assert.equal(group.positions[0].pnlPct, null);
  });
  it('reprices quantity changes and does not analyze a watchlist or empty portfolio', () => {
    assert.equal(valuePortfolio([position('A.NS', 3, 100)], { 'A.NS': quote(200) }).groups.INR.market, 600);
    assert.deepEqual(valuePortfolio([], {}).currencies, []);
    assert.equal(analysisRequest(undefined), null);
  });
});
