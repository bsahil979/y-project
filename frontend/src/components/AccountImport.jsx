import {combineOwnedPortfolios} from '../services/portfolioWorkspace.js';
import React, {useEffect, useRef, useState} from 'react';
import {API_BASE_URL} from '../config/api';
import {supabase} from '../services/supabaseClient';
import {parseCSV, normalizeImport, applyPortfolioImport, normalizeBrokerPortfolio} from '../services/portfolioImport';

async function brokerRequest(provider, path, method = 'POST') {
  const {data} = await supabase.auth.getSession();
  if (!data?.session?.access_token) throw new Error('Sign in to your cloud account to connect a brokerage.');
  const response = await fetch(API_BASE_URL + '/brokers/' + provider.toLowerCase() + '/' + path, {
    method, headers:{Authorization:'Bearer ' + data.session.access_token},
  });
  const result = await response.json();
  if (!response.ok) { const error = new Error(result.detail || 'Broker request failed.'); error.status = response.status; throw error; }
  return result;
}

const brokerChoices = ['Upstox', 'Zerodha', 'Groww', 'Angel One', 'ICICI Direct', 'HDFC Securities', 'Other broker'];

const authorizationMessages = {
      invalid_credentials: 'Upstox rejected the API key or API secret. Copy both from the same Upstox developer app into the backend configuration, then restart the backend.',
      invalid_redirect: 'Upstox rejected the redirect URI. It must exactly match the URI registered in your Upstox developer app.',
      invalid_code: 'The authorization code expired or was already used. Click Connect Upstox to start a fresh authorization.',
      network_error: 'The server could not reach Upstox to finish authorization. Check the server connection, then click Connect Upstox again.',
      token_rejected: 'Upstox rejected the token request. Check your developer app configuration and reconnect.',
      invalid_response: 'Upstox returned an incomplete token response. Click Connect Upstox to retry.',
    };

export default function AccountImport({workspace, setWorkspace}) {
  const dialog = useRef(null);
  const [selectedBroker, setSelectedBroker] = useState(() => typeof window !== 'undefined' && new URLSearchParams(window.location.search).has('zerodha') ? 'Zerodha' : 'Upstox');
  const [accountName, setAccountName] = useState('Upstox account');
  const [targetPortfolio, setTargetPortfolio] = useState(workspace.selectedPortfolioId || '');
  const [brokerSearch, setBrokerSearch] = useState('');
  const [configured, setConfigured] = useState(false);
  const [connected, setConnected] = useState(null);
  const [rows, setRows] = useState([]);
  const [mode, setMode] = useState('holdings');
  const [name, setName] = useState('Imported portfolio');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [fileKey, setFileKey] = useState(0);
  const [notice, setNotice] = useState('');
  const [brokerSnapshot, setBrokerSnapshot] = useState(null);
  const [importWarnings, setImportWarnings] = useState([]);
  const apiBroker = ['Upstox', 'Zerodha'].includes(selectedBroker);
  const broker = (path, method) => brokerRequest(selectedBroker, path, method);
  const authMessage = result => (authorizationMessages[result] || '').replaceAll('Upstox', selectedBroker);
  useEffect(() => {
    let active = true;
    setConfigured(false); setConnected(null);
    if (!apiBroker) return;
    const provider = selectedBroker.toLowerCase();
    fetch(API_BASE_URL + '/brokers/' + provider + '/status').then(r => r.json())
      .then(r => {if (active) setConfigured(r.configured === true);}).catch(() => {});
    const result = new URLSearchParams(window.location.search).get(provider);
    if (result) {
      if (!dialog.current.open) dialog.current.showModal();
      const url = new URL(window.location.href);
      url.searchParams.delete(provider);
      window.history.replaceState(null, '', url.pathname + url.search + url.hash);
    }
    brokerRequest(selectedBroker, 'connection', 'GET').then(status => {
      if (!active) return;
      setConnected(status.connected);
      setError(authMessage(status.authorization_result));
      if (result === 'connected') setNotice(status.connected
        ? selectedBroker + ' connected. Fetch portfolio, review it, then Confirm import.'
        : 'Connection not found for this app account. Connect again.');
    }).catch(e => {if (active) setError('Could not check connection: ' + e.message);});
    return () => {active = false;};
  }, [selectedBroker]);
  async function run(action) {
    setError(''); setNotice(''); setBusy(true);
    try {await action();} catch(e) {setError(e.message); if ([401, 409].includes(e.status)) setConnected(false);} finally {setBusy(false);}
  }
  async function fetchHoldings() {
    setRows([]);
    setBrokerSnapshot(null); setImportWarnings([]);
    const result = await broker('portfolio');
    setConnected(true); setBrokerSnapshot(result);
    setMode('holdings'); setFileKey(k => k + 1);
    const imported = normalizeBrokerPortfolio(result);
    setRows(imported.rows); setImportWarnings(imported.warnings); setName(selectedBroker + ' portfolio'); setAccountName(selectedBroker + ' account');
    setNotice(imported.rows.length ? `Fetched ${imported.rows.length} equity/fund holdings. Review and Confirm import to save.` : 'No importable holdings returned. Check each category below for empty results or access errors.');
  }

  async function openDialog() {
    dialog.current.showModal();
    if (!apiBroker) return;
    setConnected(null);
    try {
      const status = await broker('connection', 'GET');
      setConnected(status.connected);
      setError(authMessage(status.authorization_result));
      if (status.authorization_result === 'pending') setNotice('Authorization has not completed at this server. Finish the broker authorization in the same browser.');
    } catch(e) {setConnected(null); setError('Could not check broker connection: ' + e.message);}
  }
  function chooseBroker(value) {
    setSelectedBroker(value); setRows([]); setBrokerSnapshot(null); setImportWarnings([]);
    setNotice(''); setError(''); setFileKey(k => k + 1);
    setName(value + ' portfolio'); setAccountName(value + ' account');
  }
  async function readFile(file) {
    setRows([]);
    setBrokerSnapshot(null); setImportWarnings([]);
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) throw new Error('Choose a CSV smaller than 5 MB.');
    setRows(normalizeImport(parseCSV(await file.text()), mode));
  }
  return <>
    <button className="rounded-lg border border-blue-300 px-4 py-2 text-blue-700" onClick={openDialog}>+ Add account / Import portfolio</button>
    <dialog ref={dialog} className="account-import-dialog" onCancel={e => {if(busy) e.preventDefault();}}>
      <header><h2>Add an account</h2><button aria-label="Close account import" disabled={busy} onClick={() => dialog.current.close()}>×</button></header>
      <h3>Connect your brokerage or import a statement</h3>
      {workspace.portfolios.length > 1 && <section><h4>See all your assets together</h4><p>Your holdings are currently split across {workspace.portfolios.length} portfolios. Combine them into My Portfolio while keeping each brokerage account and every holding.</p><button disabled={busy} onClick={() => run(async () => { const combined = combineOwnedPortfolios(workspace); await setWorkspace(combined); setTargetPortfolio(combined.selectedPortfolioId); setNotice('Portfolios combined. Broker accounts and manual holdings are retained.'); })}>Combine all into My Portfolio</button></section>}
      <section><h4>Your brokerage accounts</h4>
        <p>Add several brokers to one portfolio, or keep separate portfolios. Each import creates a separate account. Use a new label only for a genuinely different account, not to refresh existing holdings.</p>
        {workspace.accounts.filter(a => a.account_type === 'brokerage').map(a => <div key={a.id} className="border-b py-3"><strong>{a.name}</strong><span className="ml-3 text-slate-500">{a.institution || 'Broker not specified'} · Saved holdings</span></div>)}
        <label>Find a broker<input value={brokerSearch} onChange={e => setBrokerSearch(e.target.value)} placeholder="Search brokers" /></label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 my-3">{brokerChoices.filter(b => b.toLowerCase().includes(brokerSearch.toLowerCase())).map(b => <button type="button" disabled={busy} aria-pressed={selectedBroker === b} key={b} onClick={() => chooseBroker(b)} className={selectedBroker === b ? 'border-2 border-blue-600 bg-blue-50 p-3 rounded-lg' : 'border p-3 rounded-lg'}>{b}<small className="block">{['Upstox', 'Zerodha'].includes(b) ? 'API connection + CSV' : 'CSV import'}</small></button>)}</div>
        <p>Selected broker: <strong>{selectedBroker}</strong></p>
        {!apiBroker && <p>Live connection is not implemented for this broker. Export your holdings or trades and arrange the CSV columns shown below before importing.</p>}
      </section>
      {apiBroker && <section><h4>{selectedBroker}</h4><p>Connect {selectedBroker} to fetch equity and mutual fund holdings, positions, SIPs, orders, and funds/margin for review.</p>
        <p role="status">{connected === null ? 'Checking connection...' : connected ? 'Connected to this app account. Fetch holdings to preview before importing.' : 'Not connected to this app account. Start with Connect broker.'}</p>
        {!configured && <p>Connection setup required. Configure the selected broker developer app and Supabase authentication on the server.</p>}
        <div className="flex flex-wrap gap-3 mt-3">
          <button disabled={busy || !configured} onClick={() => run(async () => {const result = await broker('connect'); window.location.assign(result.url);})}>Connect {selectedBroker}</button>
          <button disabled={busy || !configured || connected !== true} onClick={() => run(fetchHoldings)}>Fetch portfolio</button>
          <button disabled={busy || !configured} onClick={() => run(async () => {await broker('connection', 'DELETE'); setConnected(false); setRows([]); setNotice(selectedBroker + ' disconnected from this app.');})}>Disconnect</button>
        </div>
      </section>}
      <section><h4>Import CSV</h4><p>Choose a holdings snapshot or complete buy/sell history. Check the columns in the preview before saving.</p>
        <label>File type <select disabled={busy} value={mode} onChange={e=>{setMode(e.target.value);setRows([]);setFileKey(k=>k+1);}}><option value="holdings">Holdings</option><option value="trades">Trade history</option></select></label>
        <p className="text-xs my-3">Required columns: {mode === 'holdings' ? 'ticker, quantity, average_cost, currency' : 'ticker, quantity, price, type, date, currency (optional fees)'}. Dates use YYYY-MM-DD. NSE/BSE exchange columns are supported.</p>
        <input key={fileKey} disabled={busy} aria-label="Portfolio CSV file" type="file" accept=".csv,text/csv" onChange={e=>run(()=>readFile(e.target.files[0]))} />
      </section>
      {brokerSnapshot && <section><h4>Broker portfolio coverage</h4>
        <p>Equities and mutual funds can be imported. Positions, SIPs, orders, and margins are reference data, excluded from owned-asset totals to avoid double counting. Fund risk optimization is not yet available.</p>
        {Object.entries(brokerSnapshot.sections).map(([category, section]) => <details key={category} className="my-3">
          <summary>{category.replaceAll('_',' ')}: {section.status === 'ok' ? (Array.isArray(section.data) ? `${section.data.length} records` : 'Available') : section.status}</summary>
          {section.message && <p role="alert">{section.message}</p>}
          {Array.isArray(section.data) ? section.data.map((row, i) => <div key={i} className="border-b py-2 text-sm">
            {Object.entries(row).filter(([key]) => !['folio','instrument_token','exchange_order_id'].includes(key)).map(([key,value]) => <span key={key} className="inline-block mr-4"><strong>{key.replaceAll('_',' ')}:</strong> {String(value ?? 'Unavailable')}</span>)}
          </div>) : section.data && Object.entries(section.data).map(([segment,values]) => <div key={segment}><strong>{segment}</strong>{Object.entries(values || {}).map(([key,value]) => <p key={key}>{key.replaceAll('_',' ')}: {String(value)}</p>)}</div>)}
        </details>)}
      </section>}
      {importWarnings.map((warning,i) => <p role="alert" key={i} className="text-amber-800">{warning}</p>)}
      {notice && <p role="status">{notice}</p>}
      {rows.length > 0 && <section><h4>Review {rows.length} records</h4>
        <label>Save to portfolio <select disabled={busy} value={targetPortfolio} onChange={e => setTargetPortfolio(e.target.value)}><option value="">Create a new portfolio</option>{workspace.portfolios.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        <label>Broker account label <input disabled={busy} value={accountName} onChange={e => setAccountName(e.target.value)} placeholder="e.g. Groww - personal" /></label>
        {!targetPortfolio && <label>New portfolio name <input disabled={busy} value={name} onChange={e=>setName(e.target.value)} /></label>}
        <p className="my-3 text-sm">This adds a separately labeled brokerage account to the selected portfolio. Holdings imports carry average costs. Trade imports require the full purchase history.</p>
        <div className="max-h-64 overflow-auto"><table className="w-full text-sm"><thead><tr>{['Asset','Quantity','Cost per unit','Currency','Type','NAV date'].map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={i}><td>{r.asset_name || r.ticker}</td><td>{r.quantity}</td><td>{r.price}</td><td>{r.currency}</td><td>{r.asset_type || r.transaction_type || 'Equity'}</td><td>{r.valuation_date || r.transaction_date || 'Unavailable'}</td></tr>)}</tbody></table></div>
        <button disabled={busy} className="mt-4" onClick={()=>run(async()=>{const result = await setWorkspace(applyPortfolioImport(workspace, rows, mode, name, {institution:selectedBroker, accountName, portfolioId:targetPortfolio}));setRows([]);setNotice(result?.status === 'sync-failed' ? 'Saved on this device. Cloud sync failed; check the workspace sync status.' : 'Portfolio imported.');})}>Confirm import</button>
      </section>}
      {busy && <p role="status">Working…</p>}{error && <p role="alert" className="text-red-700">{error}</p>}
    </dialog>
  </>;
}
