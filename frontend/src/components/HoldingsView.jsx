import AssetAccounts from './AssetAccounts';
import AccountImport from './AccountImport';
import { FileText, Plus, RefreshCw } from 'lucide-react';
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { createTransaction, ensureSelectedPortfolio, validateTransactionLedger } from '../services/portfolioData';
import { currencyForTicker } from '../services/portfolioLedger';
import { formatMoney, formatQuoteFreshness } from '../services/portfolioValuation';
import usePortfolioSnapshot from '../hooks/usePortfolioSnapshot';

const initialForm = { accountId: '', ticker: '', quantity: '', averageCost: '', currency: 'INR', transactionDate: new Date().toLocaleDateString('en-CA') };
const field = 'mt-1 w-full rounded-xl border border-gray-700 bg-[#161822] px-3 py-2 text-white';

export default function HoldingsView({ workspace, setWorkspace }) {
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState('');
  const [closing, setClosing] = useState(null);
  const [salePrice, setSalePrice] = useState('');
  const [saleDate, setSaleDate] = useState(new Date().toLocaleDateString('en-CA'));
  const { snapshot, pricing } = usePortfolioSnapshot();
  const fromTransactions = snapshot.transactions.length > 0;
  const holdings = snapshot.holdings;
  const valuation = snapshot.valuation;
  const accountGroups = [...new Set(holdings.map(holding => holding.account_id || ''))].map(id => ({
    id,
    name: workspace.accounts.find(account => account.id === id)?.name || 'Unassigned holdings',
    positions: valuation.positions.filter(holding => (holding.account_id || '') === id),
  }));
  const update = (event) => setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  const add = (event) => {
    event.preventDefault();
    const ticker = form.ticker.trim().toUpperCase();
    const quantity = Number(form.quantity);
    const averageCost = Number(form.averageCost);
    if (!ticker || !form.quantity || form.averageCost === '' || !Number.isFinite(quantity) || quantity <= 0 || !Number.isFinite(averageCost) || averageCost <= 0) {
      setError('Enter a ticker, a positive quantity, and a positive purchase price.'); return;
    }
    const currency = currencyForTicker(ticker, form.currency);
    const next = ensureSelectedPortfolio(workspace, currency);
    const transaction = createTransaction({ portfolioId: next.selectedPortfolioId, accountId: form.accountId || null, ticker, quantity, price: averageCost, currency, transactionType: 'buy', transactionDate: form.transactionDate });
    const transactions = [...next.transactions, transaction];
    const ledgerError = validateTransactionLedger(transactions, next.holdings);
    if (ledgerError) { setError(ledgerError.message); return; }
    setWorkspace({ ...next, transactions });
    setForm(initialForm); setError('');
  };
  const remove = (event) => {
    event.preventDefault();
    const price = Number(salePrice);
    if (!closing || !salePrice || !Number.isFinite(price) || price <= 0 || !saleDate) {
      setError('Enter the actual sale price and date.'); return;
    }
    const transaction = createTransaction({ portfolioId: snapshot.portfolioId, accountId: closing.account_id,
      ticker: closing.ticker, currency: closing.currency, transactionType: 'sell', quantity: closing.quantity,
      price, transactionDate: saleDate });
    const transactions = [...workspace.transactions, transaction];
    const ledgerError = validateTransactionLedger(transactions, workspace.holdings);
    if (ledgerError) { setError(ledgerError.message); return; }
    setWorkspace({ ...workspace, transactions });
    setClosing(null); setSalePrice(''); setError('');
  };
  return <div className="holdings-page space-y-6 text-slate-800">
    <header className="holdings-heading"><h1>Your securities</h1><div className="holdings-totals">{valuation.currencies.map(currency => <div key={currency}><span>{currency} portfolio value</span><strong>{pricing.loading ? 'Loading prices…' : formatMoney(valuation.groups[currency].market, currency)}</strong></div>)}</div>{!holdings.length && <p>Add your first holding to see its value here.</p>}</header>
    <AccountImport workspace={workspace} setWorkspace={setWorkspace} />
    <section className="holdings-account-card">
      <header><FileText size={28} aria-hidden="true" /><div><h2>Securities accounts</h2><p>Your stock holdings in the selected portfolio.</p></div></header>
      {accountGroups.map(account => <article key={account.id} className="holdings-account-row">
        <div><h3>{account.name}</h3><p>{account.positions.length} {account.positions.length === 1 ? 'holding' : 'holdings'}</p></div>
        <div className="holdings-account-values">{[...new Set(account.positions.map(p => p.currency))].map(currency => {
          const positions = account.positions.filter(p => p.currency === currency);
          const total = positions.every(p => Number.isFinite(p.market)) ? positions.reduce((sum, p) => sum + p.market, 0) : null;
          return <p key={currency}>{pricing.loading ? 'Loading prices…' : formatMoney(total, currency)} <span>{currency}</span></p>;
        })}</div>
        <a href="#holding-entry" onClick={() => setForm(current => ({...current, accountId: account.id}))}>Add holding →</a>
      </article>)}
      {!accountGroups.length && <p className="p-5 text-sm text-slate-500">Account summaries appear when you add holdings.</p>}
      <footer><a href="#holding-entry"><Plus size={16} aria-hidden="true" /> Add a holding</a><button onClick={pricing.refresh} disabled={pricing.loading || !holdings.length}><RefreshCw size={16} aria-hidden="true" /> {pricing.loading ? 'Refreshing…' : 'Refresh prices'}</button><Link to="/dashboard/portfolio/transactions">View transactions →</Link></footer>
    </section>
    <div className="grid gap-4 md:grid-cols-2">{valuation.currencies.map((currency) => {
      const group = valuation.groups[currency];
      return <section key={currency} className="rounded-2xl border border-gray-800 bg-[#11131a] p-5"><h2 className="text-sm font-semibold">{currency} holdings</h2><p className="mt-2 text-2xl font-bold text-white">{pricing.loading ? 'Loading prices...' : formatMoney(group.market, currency)}</p><p className="mt-2 text-sm text-gray-400">Recorded cost: {formatMoney(group.cost, currency)}</p><p className="text-sm text-gray-400">Unrealized P/L: {formatMoney(group.pnl, currency)}{group.pnlPct == null ? '' : ' (' + group.pnlPct.toFixed(2) + '%)'}</p>{!group.complete && !pricing.loading && <p className="mt-3 text-sm text-amber-300">Complete market value unavailable: {group.missing.map((item) => item.ticker).join(', ')} need valid prices.</p>}</section>;
    })}</div>
    <p className="text-xs text-gray-400">The receipt time and last daily market session appear with each price. A fetch time does not mean the market quote is live. Missing or mismatched prices stay unavailable; purchase costs are not shown as current market values. Currency totals are not combined.</p>
    {pricing.error && <p role="alert" className="text-amber-300">{pricing.error}</p>}
    {!snapshot.valid && <p role="alert" className="text-amber-300">{snapshot.errors.map((item) => item.message).join(" ")}</p>}
    {fromTransactions && <div className="rounded-xl border border-indigo-700/40 p-4 text-sm">Holdings include opening positions and recorded transactions. <Link to="/dashboard/portfolio/transactions" className="text-indigo-300 underline">Manage transactions</Link> to change positions.</div>}
    <form id="holding-entry" onSubmit={add} className="rounded-2xl border border-gray-800 bg-[#11131a] p-5"><h2 className="mb-4 font-semibold">Add a holding (records a Buy)</h2><div className="grid gap-3 md:grid-cols-5">
      <label className="text-xs">Account<select name="accountId" value={form.accountId} onChange={update} className={field}><option value="">Unassigned</option>{workspace.accounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</select></label>
      <label className="text-xs">Ticker<input required name="ticker" value={form.ticker} onChange={update} placeholder="RELIANCE.NS" className={field} /></label>
      <label className="text-xs">Quantity<input required name="quantity" type="number" step="any" min="0" value={form.quantity} onChange={update} className={field} /></label>
      <label className="text-xs">Purchase price per share<input required name="averageCost" type="number" step="any" min="0" value={form.averageCost} onChange={update} className={field} /></label>
      <label className="text-xs">Currency<select name="currency" value={form.currency} onChange={update} className={field}><option>INR</option><option>USD</option></select></label>
      <label className="text-xs">Purchase date<input required name="transactionDate" type="date" value={form.transactionDate} onChange={update} className={field} /></label>
      <button type="submit" className="self-end rounded-xl bg-indigo-600 px-4 py-2 text-white">Add holding</button>
    </div><p className="mt-3 text-xs text-gray-400">Unassigned means no brokerage account. The holding is added to the portfolio selected in the sidebar. Adding a holding creates a Buy in Transactions automatically. Enter the actual purchase date and price. Indian exchange symbols use .NS or .BO and are recorded in INR.</p>{error && <p role="alert" className="mt-3 text-sm text-amber-300">{error}</p>}</form>
    {closing && <form onSubmit={remove} className="rounded-xl border border-rose-700/40 p-5 space-y-3">
      <h2 className="font-semibold">Record sale of {closing.quantity} {closing.ticker} shares ({closing.currency})</h2>
      <p className="text-sm">This removes the position by recording a Sell. Your existing purchase history stays intact.</p>
      <label className="block text-xs">Sale price per share<input required type="number" min="0.000001" step="any" value={salePrice} onChange={(event) => setSalePrice(event.target.value)} className={field} /></label>
      <label className="block text-xs">Sale date<input required type="date" value={saleDate} onChange={(event) => setSaleDate(event.target.value)} className={field} /></label>
      <button type="submit" className="rounded-xl bg-rose-600 px-4 py-2 text-white">Record sale and remove holding</button>
      <button type="button" onClick={() => { setClosing(null); setError(''); }} className="ml-3">Cancel</button>
      {error && <p role="alert" className="text-amber-300">{error}</p>}
    </form>}
    <div className="overflow-x-auto rounded-2xl border border-gray-800 bg-[#11131a] p-4"><table className="w-full whitespace-nowrap text-sm"><thead><tr className="text-gray-400"><th className="p-2 text-left">Stock</th><th className="p-2 text-right">Quantity</th><th className="p-2 text-right">Cost</th><th className="p-2 text-right">Market value</th><th className="p-2 text-right">Unrealized P/L</th><th className="p-2 text-left">Price source and time</th><th className="p-2">Action</th></tr></thead><tbody>{valuation.positions.map((holding, index) => <tr key={holding.id || holding.ticker + ':' + index} className="border-t border-gray-800"><td className="p-2">{holding.ticker} <span className="text-xs text-gray-500">{holding.currency} · {workspace.accounts.find((account) => account.id === holding.account_id)?.name || 'Unassigned'}</span></td><td className="p-2 text-right">{holding.quantity}</td><td className="p-2 text-right">{formatMoney(holding.cost, holding.currency)}</td><td className="p-2 text-right">{formatMoney(holding.market, holding.currency)}</td><td className="p-2 text-right">{formatMoney(holding.pnl, holding.currency)}</td><td className="max-w-sm whitespace-normal p-2 text-xs text-gray-400">{pricing.loading ? 'Loading price...' : holding.issue || formatQuoteFreshness(holding.quote)}</td><td className="p-2"><button onClick={() => { setClosing(holding); setSalePrice(''); setError(''); }} className="text-rose-300" aria-label={'Remove holding ' + holding.ticker}>Remove / record sale</button></td></tr>)}</tbody></table>{!holdings.length && <p className="p-4 text-sm text-gray-400">No owned positions yet.</p>}</div>
    <AssetAccounts workspace={workspace} setWorkspace={setWorkspace} snapshot={snapshot} />
    {fromTransactions && <div className="grid gap-3 md:grid-cols-2">{Object.entries(snapshot.summary.byCurrency).map(([currency, summary]) => <section key={currency} className="rounded-xl border border-gray-800 p-4 text-sm"><h2 className="font-semibold">Realized activity ({currency})</h2><p>Realized P/L: {formatMoney(summary.realizedPnl, currency)}</p><p>Dividends: {formatMoney(summary.dividends, currency)}</p><p>Fees: {formatMoney(summary.fees, currency)}</p></section>)}</div>}
  </div>;
}
