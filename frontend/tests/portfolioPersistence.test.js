import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'vite';
test('failed asset saves survive reload and successful retry clears pending data', async () => {
 const server=await createServer({configFile:false,server:{middlewareMode:true,watch:null},optimizeDeps:{noDiscovery:true,include:[]}});
 const old=globalThis.localStorage, saved=new Map();
 globalThis.localStorage={getItem:k=>saved.get(k)??null,setItem:(k,v)=>saved.set(k,v),removeItem:k=>saved.delete(k)};
 try {
  const {supabase}=await server.ssrLoadModule('/src/services/supabaseClient.js');
  const {PortfolioDataService:service}=await server.ssrLoadModule('/src/services/portfolioData.js');
  let fail=true; const batches=[];
  supabase.from=table=>({select:()=>({eq:async()=>({data:[],error:null})}),upsert:async(rows,options)=>{
    batches.push({table,rows,options});return {error:fail?{message:'test database unavailable'}:null};
  }});
  const user='11111111-1111-4111-8111-111111111111';
  const workspace={holdings:[{id:'stock',ticker:'TCS.NS',quantity:1,average_cost:100,created_at:'2026-01-01'},
    {id:'cash',ticker:'ASSET:cash',asset_type:'cash',asset_name:'TEST cash',quantity:1,average_cost:0,manual_value:10000,currency:'INR'}]};
  assert.equal((await service.saveWorkspace(user,workspace)).status,'sync-failed');
  const loaded=await service.getWorkspaceResult(user);
  assert.equal(loaded.status,'sync-failed');
  assert.equal(loaded.workspace.holdings[1].manual_value,10000);
  fail=false;
  assert.equal((await service.saveWorkspace(user,loaded.workspace)).status,'synced');
  assert.equal(saved.has(`smart_advisor_pending_${user}`),false);
  const holdings=batches.filter(b=>b.table==='holdings');
  assert.equal(holdings.length,2);
  assert.ok(holdings.every(b=>b.options.defaultToNull===false));
  assert.equal((await service.getWorkspaceResult(user)).workspace.holdings.length,0);
 } finally {globalThis.localStorage=old;await server.close();}
});
