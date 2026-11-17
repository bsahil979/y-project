import React, {useRef, useState, useEffect} from 'react';
import {useSearchParams} from 'react-router-dom';
import {assetCategories, assetValue, isTrackedAsset, trackingTotals} from '../services/assetTracking';
import {createId, ensureSelectedPortfolio} from '../services/portfolioWorkspace';
import {formatMoney} from '../services/portfolioValuation';
import {API_BASE_URL} from '../config/api';

const empty = {name:'', quantity:'1', value:'', cost:'0', currency:'INR', date:new Date().toLocaleDateString('en-CA'), scheme:'', source:'User valuation'};
export default function AssetAccounts({workspace, setWorkspace, snapshot}) {
  const dialog = useRef(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedCategory = searchParams.get('addAsset');
  useEffect(() => {
    if (!assetCategories.some(([category]) => category === requestedCategory)) return;
    open(requestedCategory);
    const next = new URLSearchParams(searchParams);
    next.delete('addAsset');
    setSearchParams(next, {replace:true});
  }, [requestedCategory]);
  const [type, setType] = useState('cash');
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(empty);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const assets = workspace.holdings.filter(r => r.portfolio_id === snapshot.portfolioId && isTrackedAsset(r));
  const totals = trackingTotals(assets);
  const currencies = [...new Set([...snapshot.valuation.currencies, ...Object.keys(totals)])];
  function open(category, row = null) {
    setType(category);setEditing(row?.id || null);setError('');
    setForm(row ? {name:row.asset_name, quantity:String(row.quantity), value:String(row.manual_value ?? ''), cost:String(row.average_cost), currency:row.currency, date:row.valuation_date || '', scheme:category === 'mutual_fund' ? row.ticker.replace('MF:', '') : '', source:row.valuation_source || 'User valuation'} : {...empty, date:new Date().toLocaleDateString('en-CA')});
    dialog.current.showModal();
  }
  const update = e => setForm(f=>({...f,[e.target.name]:e.target.value, source:'User valuation'}));
  async function fetchNav() {
    setBusy(true);setError('');
    try {
      const res = await fetch(API_BASE_URL + '/funds/' + encodeURIComponent(form.scheme.trim()) + '/nav');
      const result = await res.json();
      if(!res.ok) throw new Error(result.detail || 'NAV unavailable');
      setForm(f=>({...f,name:result.name,value:String(result.nav),date:result.date,currency:'INR',source:'AMFI'}));
    } catch(e) {setError(e.message);} finally {setBusy(false);}
  }
  async function save(e) {
    e.preventDefault();setError('');
    const quantity = type === 'mutual_fund' ? Number(form.quantity) : 1;
    const value = Number(form.value), cost = Number(form.cost);
    if(!form.name.trim() || !form.date || form.value === '' || !Number.isFinite(value) || value < 0 || !Number.isFinite(quantity) || quantity <= 0 || !Number.isFinite(cost) || cost < 0) {setError('Enter a name, valuation date, positive units, and non-negative values.');return;}
    if(type === 'mutual_fund' && (!/^(?:\d{5,8}|IN[A-Z0-9]{10})$/.test(form.scheme.trim().toUpperCase()) || form.currency !== 'INR')) {setError('Use an AMFI scheme code or fund ISIN and INR for Indian mutual funds.');return;}
    const next = ensureSelectedPortfolio(workspace, form.currency);
    const id = editing || createId();
    const record = {id,portfolio_id:next.selectedPortfolioId,account_id:null,asset_type:type,asset_name:form.name.trim(),ticker:type === 'mutual_fund' ? 'MF:' + form.scheme.trim().toUpperCase() : 'ASSET:' + id,quantity,average_cost:cost,currency:form.currency,manual_value:value,valuation_date:form.date,valuation_source:form.source};
    setBusy(true);
    try {const result = await setWorkspace({...next,holdings:[...next.holdings.filter(r=>r.id!==id),record]});
      setEditing(id);
      if(result?.status === 'sync-failed') {setError('Saved on this device only. Cloud sync failed: ' + (result.error?.message || 'Please retry.'));}
      else dialog.current.close();}
    catch(e) {setError(e.message);} finally {setBusy(false);}
  }
  return <div className="space-y-5">
    {assets.length > 0 && <section className="holdings-account-card p-6"><h2>Tracked net worth</h2>{currencies.map(currency=>{
      const securities = snapshot.valuation.groups[currency];
      const amount = (securities && !securities.complete) || totals[currency] === null ? null : (securities?.market || 0) + (totals[currency] || 0);
      return <p className="mt-2 text-xl font-semibold" key={currency}>{formatMoney(amount,currency)} <span className="text-sm">{currency}</span></p>;
    })}<p className="mt-3 text-sm text-slate-500">Includes securities, dated asset valuations, and liabilities. Each currency is totaled separately.</p></section>}
    {assetCategories.map(([category,title,description])=><section key={category} className="holdings-account-card">
      <header><div><h2>{title}</h2><p>{description}</p></div></header>
      {assets.filter(r=>r.asset_type===category).map(row=><article key={row.id} className="holdings-account-row">
        <div><h3>{row.asset_name}</h3><p>{category==='mutual_fund' ? row.quantity + ' units Â· ' : ''}{row.valuation_source} Â· {row.valuation_date}</p></div>
        <div className="holdings-account-values">{formatMoney(assetValue(row),row.currency)}</div>
        <button className="text-blue-700" onClick={()=>open(category,row)}>Edit valuation</button>
      </article>)}
      <footer><button onClick={()=>open(category)}>+ Add {title.toLowerCase()}</button></footer>
    </section>)}
    <p className="text-sm text-slate-500">These assets support wealth tracking. Advisor optimization currently covers the stock portfolio. NAV-based diagnostics and profile recommendations are available in the fund advisor. Fund target-weight optimization and transaction-based XIRR are pending.</p>
    <dialog ref={dialog} className="account-import-dialog" onCancel={e=>{if(busy)e.preventDefault();}}>
      <header><h2>{editing ? 'Edit' : 'Add'} {assetCategories.find(r=>r[0]===type)?.[1]}</h2><button disabled={busy} onClick={()=>dialog.current.close()} aria-label="Close asset form">Ã—</button></header>
      <form onSubmit={save} className="grid gap-3 mt-5">
        {type==='mutual_fund' && <label>AMFI scheme code or fund ISIN<input required name="scheme" value={form.scheme} onChange={update} /><button type="button" disabled={busy} onClick={fetchNav}>Fetch latest NAV</button></label>}
        <label>Name<input required name="name" value={form.name} onChange={update} /></label>
        {type==='mutual_fund' && <label>Units<input required type="number" step="any" min="0.000001" name="quantity" value={form.quantity} onChange={update} /></label>}
        <label>{type==='mutual_fund' ? 'NAV per unit' : type==='liability' ? 'Outstanding balance' : 'Current value'}<input required type="number" step="any" min="0" name="value" value={form.value} onChange={update} /></label>
        <label>{type==='mutual_fund' ? 'Average purchase cost per unit' : 'Recorded cost'}<input required type="number" step="any" min="0" name="cost" value={form.cost} onChange={update} /></label>
        <label>Currency<select name="currency" value={form.currency} onChange={update}><option>INR</option>{type!=='mutual_fund' && <option>USD</option>}</select></label>
        <label>Valuation date<input required type="date" name="date" value={form.date} onChange={update} /></label>
        {error && <p role="alert" className="text-red-700">{error}</p>}
        <button disabled={busy} type="submit">{busy?'Workingâ€¦':'Save asset'}</button>
      </form>
    </dialog>
  </div>;
}
