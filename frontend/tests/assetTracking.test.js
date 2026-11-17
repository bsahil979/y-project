import {test} from 'node:test';
import assert from 'node:assert/strict';
import {getPortfolioSnapshot} from '../src/services/portfolioSnapshot.js';
import {trackingTotals} from '../src/services/assetTracking.js';
test('tracked assets preserve stock weights and subtract liabilities by currency',()=>{
 const rows = [
 {id:'home',portfolio_id:'p',ticker:'ASSET:home',asset_type:'real_estate',quantity:1,manual_value:100000,currency:'INR',average_cost:80000},
 {id:'loan',portfolio_id:'p',ticker:'ASSET:loan',asset_type:'liability',quantity:1,manual_value:20000,currency:'INR',average_cost:0},
 {id:'fund',portfolio_id:'p',ticker:'MF:123456',asset_type:'mutual_fund',quantity:10,manual_value:20,currency:'INR',average_cost:18}];
 const snapshot=getPortfolioSnapshot({selectedPortfolioId:'p',portfolios:[{id:'p'}],accounts:[],holdings:[...rows,{portfolio_id:'p',ticker:'AAPL',quantity:2,average_cost:10,currency:'USD'}],transactions:[]},'p',{quotes:{AAPL:{price:20,currency:'USD'}}});
 assert.deepEqual(snapshot.valuation.groups.USD.weights,[1]);
 assert.deepEqual(snapshot.valuation.currencies,['USD']);
 assert.equal(snapshot.trackedAssets.length,3);
 assert.equal(trackingTotals(rows).INR,80200);
});
