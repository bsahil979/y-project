import assert from 'node:assert/strict';
import { it } from 'node:test';
import { holdingAnswer } from '../src/services/advisorHolding.js';

it('answers about the named owned holding without repeating unrelated assets', () => {
  const snapshot = { holdings: [{ ticker: 'RELIANCE.NS', currency: 'INR', quantity: 12, average_cost: 1000, market_value: 13836, pnl: 1836 }, { ticker: 'AAPL', currency: 'USD', quantity: 6 }], valuation: { groups: { INR: { market: 30000 } } } };
  const answer = holdingAnswer('tell me about reliance stock in my portfolio', snapshot, 'INR');
  assert.match(answer, /12 shares/);
  assert.match(answer, /46.1%/);
  assert.doesNotMatch(answer, /AAPL/);
  assert.equal(holdingAnswer('tell me about reliance', snapshot, 'USD'), null);
  assert.equal(holdingAnswer('what is my risk', snapshot, 'INR'), null);
});
