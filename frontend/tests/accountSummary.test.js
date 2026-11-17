import test from 'node:test';
import assert from 'node:assert/strict';
import {securitiesAccountGroups} from '../src/services/accountSummary.js';
test('manual holdings never inherit broker name and totals stay account/currency scoped',()=>{
 const groups=securitiesAccountGroups({accounts:[{id:'up',name:'Upstox account'}],valuation:{positions:[
 {account_id:null,currency:'INR',market:6724}, {account_id:'up',currency:'INR',market:100},
 {account_id:null,currency:'USD',market:50}, {account_id:'up',currency:'INR',market:25}]}});
 assert.deepEqual(groups.map(g=>[g.name,g.currency,g.market]),[['Unassigned holdings','INR',6724],['Upstox account','INR',125],['Unassigned holdings','USD',50]]);
});
test('unavailable price makes only that account total unavailable',()=>{
 const groups=securitiesAccountGroups({accounts:[],valuation:{positions:[{currency:'INR',market:10},{currency:'INR',market:null}]}});
 assert.equal(groups[0].market,null);
});
