import assert from 'node:assert/strict';
import { test } from 'node:test';
import { quickPortfolioAnswer, quickPortfolioIntent } from '../src/services/advisorQuickAnswer.js';

test('the suggested-allocation prompt produces a complete answer from engine weights', () => {
  const intent = quickPortfolioIntent('Explain my suggested allocation and the biggest weight change.');
  assert.equal(intent, 'allocation');
  const tickers = ['AAPL', 'MSFT', 'GOOG', 'META', 'NVDA', 'AMZN', 'NFLX', 'JPM'];
  const result = quickPortfolioAnswer(intent, {
    tickers, weights: [.3, .1, .1, .1, .1, .1, .1, .1],
    personalized_allocation: {
      success: true,
      weights: Object.fromEntries(tickers.map(ticker => [ticker, .125])),
      applied_profile: 'conservative', investment_horizon_years: 2,
      objective_used: 'minimum_volatility', max_weight_cap: .2,
    },
  });
  assert.match(result, /Largest change: AAPL, -17\.5 percentage points/);
  for (const ticker of tickers) assert.match(result, new RegExp(`\\| ${ticker} \\|`));
  assert.match(result, /Horizon: 2 years/);
  assert.equal(quickPortfolioIntent('Could FinBERT affect my suggested allocation?'), null);
});

test('today overview uses the selected snapshot and preserves missing prices', async () => {
  const {portfolioOverview} = await import('../src/services/advisorQuickAnswer.js');
  const {valuePortfolio} = await import('../src/services/portfolioValuation.js');
  assert.equal(quickPortfolioIntent('give me an analysis of my portfolio for today'), 'overview');
  assert.equal(quickPortfolioIntent('analyze my portfolio for downside risk'), null);
  const holdings = [{ticker:'TCS.NS', currency:'INR', quantity:2, average_cost:80}];
  const snapshot = {valid:true, trackedAssets:[], valuation:valuePortfolio(holdings, {'TCS.NS':{price:100,currency:'INR',last_daily_session:'2026-11-16'}})};
  const result = portfolioOverview(snapshot,'INR');
  assert.match(result,/since purchase: ₹40.00/);
  assert.match(result,/TCS.NS at 100.0%/);
  assert.match(result,/2026-11-16/);
  snapshot.valuation = valuePortfolio(holdings);
  assert.match(portfolioOverview(snapshot,'INR'), /Missing valid prices for TCS.NS/);
});
