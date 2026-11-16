import test from 'node:test';
import assert from 'node:assert/strict';
import { combinedAnalysisRequest } from '../src/services/portfolioValuation.js';

test('combined analysis preserves native market values until the FX stage', () => {
  const valuation = { currencies:['INR','USD'], groups: {
    INR:{currency:'INR',complete:true,tickers:['TCS.NS'],marketByTicker:{'TCS.NS':8000}},
    USD:{currency:'USD',complete:true,tickers:['AAPL'],marketByTicker:{AAPL:100}}}};
  const req = combinedAnalysisRequest(valuation,'USD',{});
  assert.equal(req.base_currency,'USD');
  assert.deepEqual(req.position_values,[8000,100]);
  assert.equal(req.weights,undefined);
  valuation.groups.USD.complete=false;
  assert.equal(combinedAnalysisRequest(valuation,'USD',{}),null);
});
