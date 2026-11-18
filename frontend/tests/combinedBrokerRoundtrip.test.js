import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'vite';
import {applyPortfolioImport,normalizeBrokerPortfolio} from '../src/services/portfolioImport.js';
import {createEmptyWorkspace} from '../src/services/portfolioWorkspace.js';
import {getPortfolioSnapshot} from '../src/services/portfolioSnapshot.js';
import {buildAllocationDraft} from '../src/services/allocationDraft.js';

test('combined brokerage and manual buy survive a fresh session from cloud rows',async()=>{
  const server=await createServer({configFile:false,server:{middlewareMode:true,watch:null},optimizeDeps:{noDiscovery:true}});
  const previous=globalThis.localStorage, local=new Map(), tables=new Map();
  globalThis.localStorage={getItem:k=>local.get(k)??null,setItem:(k,v)=>local.set(k,v),removeItem:k=>local.delete(k)};
  try {
    const {supabase}=await server.ssrLoadModule('/src/services/supabaseClient.js');
    const {PortfolioDataService,createTransaction}=await server.ssrLoadModule('/src/services/portfolioData.js');
    supabase.from=name=>{
      if (!tables.has(name)) tables.set(name,new Map());
      const rows=tables.get(name);
      return {select:()=>({eq:async(key,id)=>({data:[...rows.values()].filter(r=>r[key]===id)})}),
        upsert:async(batch)=>{for(const r of batch) rows.set(r.id,structuredClone(r));return {};}};
    };
    const user='11111111-1111-4111-8111-111111111111';
    let ws=createEmptyWorkspace();
    const brokers=[
      ['Zerodha',{equities:{data:[{tradingsymbol:'INFY',exchange:'NSE',quantity:2,average_price:100}]}}],
      ['Upstox',{mutual_funds:{data:[{instrument_key:'INF200K01T51',fund:'Growth Fund',quantity:3,average_price:10,last_price:12,last_price_date:'2026-11-13'}]}}]
    ];
    for(const [institution,sections] of brokers){
      const {rows}=normalizeBrokerPortfolio({source:institution,sections});
      const opts={institution,accountName:institution,portfolioId:ws.selectedPortfolioId};
      ws=applyPortfolioImport(ws,rows,'holdings','My Portfolio',opts);
      assert.throws(()=>applyPortfolioImport(ws,rows,'holdings','My Portfolio',opts),/already exists/);
    }
    ws.transactions.push(createTransaction({portfolioId:ws.selectedPortfolioId,ticker:'INFY.NS',transactionType:'buy',quantity:1,price:90,currency:'INR'}));
    assert.equal((await PortfolioDataService.saveWorkspace(user,ws)).status,'synced');
    local.clear();
    const loaded=await PortfolioDataService.getWorkspaceResult(user);
    assert.equal(loaded.status,'synced');
    const s=getPortfolioSnapshot(loaded.workspace,ws.selectedPortfolioId,{quotes:{'INFY.NS':{price:110,currency:'INR'}}});
    assert.deepEqual(s.accounts.map(a=>a.institution).sort(),['Upstox','Zerodha']);
    assert.equal(s.transactions.length,1);
    assert.equal(s.trackedAssets[0].quantity*s.trackedAssets[0].manual_value,36);
    assert.equal(s.valuation.groups.INR.market,330);
    assert.deepEqual(s.holdings.map(p=>p.quantity).sort(),[1,2]);
    assert.equal((await PortfolioDataService.getWorkspace('22222222-2222-4222-8222-222222222222')).holdings.length,0);
  } finally {globalThis.localStorage=previous;await server.close();}
});

test('draft distributes target deltas across existing accounts and balances in value',()=>{
  const group={complete:true,market:400,tickers:['A','B'],marketByTicker:{A:300,B:100},
    positions:[{ticker:'A',market:100,quantity:1},{ticker:'A',market:200,quantity:2,account_id:'x'},{ticker:'B',market:100,quantity:2}]};
  const model={success:true,weights:{A:.5,B:.5}};
  const draft=buildAllocationDraft(group,model,[{id:'x',name:'Broker'}]);
  assert.equal(draft.rows[1].account,'Broker');
  assert.ok(Math.abs(draft.rows[0].units+1/3)<1e-9);
  assert.ok(Math.abs(draft.rows.reduce((sum,r)=>sum+r.amount,0))<1e-9);
  assert.equal(draft.rows[2].units,2);
  assert.equal(buildAllocationDraft(group,{success:true,weights:{A:1}}),null);
});
