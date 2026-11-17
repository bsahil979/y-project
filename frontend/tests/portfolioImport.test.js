import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseCSV, normalizeImport, applyPortfolioImport} from '../src/services/portfolioImport.js';
import {createEmptyWorkspace} from '../src/services/portfolioWorkspace.js';

test('CSV quoted amounts and Upstox symbols map to opening holdings without synthetic dates', () => {
  const rows = normalizeImport(parseCSV('trading symbol,exchange,quantity,average price\nRELIANCE,NSE,2,"1,200.50"'), 'holdings');
  assert.equal(rows[0].ticker, 'RELIANCE.NS');
  assert.equal(rows[0].price, 1200.50);
  const workspace = applyPortfolioImport(createEmptyWorkspace(), rows, 'holdings', 'Upstox');
  assert.equal(workspace.holdings.length, 1);
  assert.equal(workspace.transactions.length, 0);
  assert.throws(() => applyPortfolioImport(workspace, rows, 'holdings', 'Again'), /already exist/);
});
test('invalid records and incomplete sale history fail before saving', () => {
  assert.throws(() => normalizeImport([{ticker:'AAPL',quantity:1,price:20}], 'holdings'), /currency/);
  assert.throws(() => normalizeImport([{ticker:'AAPL',quantity:1,price:20,currency:'USD',type:'buy',date:'2026-02-30'}], 'trades'), /date/);
  const rows = normalizeImport([{ticker:'AAPL',quantity:1,price:20,currency:'USD',type:'sell',date:'2026-01-01'}], 'trades');
  assert.throws(() => applyPortfolioImport(createEmptyWorkspace(), rows, 'trades', 'Sales'), /history/);
});

import {normalizeBrokerPortfolio} from '../src/services/portfolioImport.js';
import {assetValue} from '../src/services/assetTracking.js';
import {getPortfolioSnapshot} from '../src/services/portfolioSnapshot.js';
test('fund-only Upstox import preserves NAV and aggregates folios without stock analytics', () => {
  const fund = {instrument_key:'INF200K01T51',fund:'Test fund',quantity:2,average_price:100,last_price:120,last_price_date:'2026-11-13'};
  const result = normalizeBrokerPortfolio({sections:{mutual_funds:{data:[{...fund,folio:'a'},{...fund,folio:'b',quantity:3,average_price:110}]},positions:{data:[{quantity:999}]}}});
  assert.equal(result.rows.length,1);
  assert.equal(result.rows[0].quantity,5);
  assert.equal(result.rows[0].price,106);
  const ws = applyPortfolioImport(createEmptyWorkspace(),result.rows,'holdings','Funds');
  const snapshot = getPortfolioSnapshot(ws);
  assert.equal(snapshot.holdings.length,0);
  assert.equal(snapshot.trackedAssets.length,1);
  assert.equal(assetValue(snapshot.trackedAssets[0]),600);
  assert.equal(snapshot.trackedAssets[0].valuation_date,'2026-11-13');
  assert.throws(()=>applyPortfolioImport(ws,result.rows,'holdings','Again'),/already exist/);
});
test('missing NAV date and duplicate folios are reported without invented prices', () => {
  const fund = {instrument_key:'INF200K01T51',fund:'Test',folio:'a',quantity:2,average_price:100,last_price:120,last_price_date:'2026-11-13'};
  const r=normalizeBrokerPortfolio({sections:{mutual_funds:{data:[fund,fund,{...fund,folio:'b',last_price_date:null}]}}});
  assert.equal(r.rows[0].quantity,2);
  assert.equal(r.warnings.length,2);
});

test('multiple brokers retain separate accounts in one portfolio including identical securities', () => {
  const rows=normalizeImport([{ticker:'AAPL',quantity:2,price:100,currency:'USD'}],'holdings');
  const first=applyPortfolioImport(createEmptyWorkspace(),rows,'holdings','Combined',{institution:'Upstox',accountName:'Upstox personal'});
  const next=applyPortfolioImport(first,rows,'holdings','Ignored',{institution:'Groww',accountName:'Groww personal',portfolioId:first.selectedPortfolioId});
  assert.equal(next.portfolios.length,1);
  assert.equal(next.accounts.length,2);
  assert.deepEqual(next.accounts.map(a=>a.institution),['Upstox','Groww']);
  assert.notEqual(next.holdings[0].account_id,next.holdings[1].account_id);
  assert.equal(getPortfolioSnapshot(next).holdings.length,2);
  assert.throws(()=>applyPortfolioImport(next,rows,'holdings','Third',{institution:'Groww',accountName:'Groww personal',portfolioId:first.selectedPortfolioId}),/already exists/);
  assert.throws(()=>applyPortfolioImport(next,rows,'holdings','Third',{institution:'Other',portfolioId:'missing'}),/existing portfolio/);
});


test('Zerodha equities and Coin funds normalize with correct provenance', () => {
  const snapshot = {source:'Zerodha', sections:{equities:{data:[{tradingsymbol:'INFY',exchange:'NSE',instrument_token:123,quantity:2,average_price:100}]}, mutual_funds:{data:[{tradingsymbol:'INF000000001',fund:'Test fund',quantity:3,average_price:10,last_price:12,last_price_date:'2026-11-16'}]}}};
  const result = normalizeBrokerPortfolio(snapshot);
  assert.equal(result.rows.length, 2);
  assert.equal(result.rows[0].ticker, 'INFY.NS');
  assert.equal(result.rows[1].ticker, 'MF:INF000000001');
  assert.equal(result.rows[1].valuation_source, 'Zerodha NAV');
  snapshot.sections.mutual_funds.data[0].last_price_date = '';
  const missing = normalizeBrokerPortfolio(snapshot);
  assert.equal(missing.rows.length, 1);
  assert.match(missing.warnings[0], /NAV date/);
});


import {combineOwnedPortfolios} from '../src/services/portfolioWorkspace.js';
test('combining portfolios retains broker/manual holdings, transactions and identities', () => {
 const workspace={selectedPortfolioId:'p1',portfolios:[{id:'p1'},{id:'p2'}],accounts:[{id:'a1'},{id:'a2'}],holdings:[{id:'h1',portfolio_id:'p1',account_id:'a1'},{id:'h2',portfolio_id:'p2',account_id:'a2'},{id:'manual',portfolio_id:'p2',account_id:null}],transactions:[{id:'t1',portfolio_id:'p2'}],goals:[]};
 const combined=combineOwnedPortfolios(workspace);
 assert.equal(combined.portfolios.length,1);
 assert.equal(combined.holdings.length,3);
 assert.ok(combined.holdings.every(h=>h.portfolio_id==='p1'));
 assert.equal(combined.transactions[0].portfolio_id,'p1');
 assert.deepEqual(combined.accounts,workspace.accounts);
 assert.equal(workspace.holdings[1].portfolio_id,'p2');
});
