import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeWorkspace} from '../src/services/portfolioWorkspace.js';

test('fresh cloud workspace prefers populated portfolio but preserves explicit selection', () => {
  const a = '11111111-1111-4111-8111-111111111111', b = '22222222-2222-4222-8222-222222222222';
  const cloud = {portfolios: [{id:a,name:'My Portfolio'}, {id:b,name:'My Portfolio'}],
    holdings:[{id:'33333333-3333-4333-8333-333333333333',portfolio_id:b,ticker:'TCS.NS',quantity:2,currency:'INR'}]};
  assert.equal(normalizeWorkspace(cloud).selectedPortfolioId,b);
  assert.equal(normalizeWorkspace({...cloud,selectedPortfolioId:a}).selectedPortfolioId,a);
});
