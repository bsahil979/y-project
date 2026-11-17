import React, { useMemo, useState } from 'react';
import { AlertCircle, ArrowDownLeft, ArrowUpRight, Plus, Receipt, Trash2 } from 'lucide-react';
import { ensureSelectedPortfolio, createTransaction, validateTransactionLedger } from '../services/portfolioData';

import usePortfolioSnapshot from '../hooks/usePortfolioSnapshot';

const transactionTypes = [
  { value: 'buy', label: 'Buy' },
  { value: 'sell', label: 'Sell' },
  { value: 'dividend', label: 'Dividend' },
  { value: 'fee', label: 'Fee' },
  { value: 'transfer', label: 'Transfer' },
];
const initialForm = {
  accountId: '',
  ticker: '',
  transactionType: 'buy',
  quantity: '',
  price: '',
  fees: '0',
  transactionDate: new Date().toISOString().slice(0, 10),
  currency: 'USD',
};
const field = 'mt-1 w-full h-10 bg-[#161822] border border-gray-700 rounded-xl px-3 text-sm text-white focus:outline-none focus:border-indigo-500';

const money = (value, currency) => Number(value || 0).toLocaleString(undefined, {
  style: 'currency',
  currency: currency || 'USD',
});

export default function TransactionsView({ workspace, setWorkspace }) {
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState('');
  const { snapshot } = usePortfolioSnapshot();
  const transactions = snapshot.transactions;
  const sortedTransactions = useMemo(
    () => [...transactions, ...snapshot.openingHoldings.map(holding => ({
      ...holding, id: 'opening:' + holding.id, transaction_type: 'opening position',
      price: holding.average_cost, fees: 0, transaction_date: holding.purchase_date || null,
      isOpening: true,
    }))].sort((a, b) => String(b.transaction_date || '').localeCompare(String(a.transaction_date || ''))),
    [transactions, snapshot.openingHoldings],
  );

  const update = (event) => setForm((current) => ({ ...current, [event.target.name]: event.target.value }));

  const add = (event) => {
    event.preventDefault();
    const ticker = form.ticker.trim().toUpperCase();
    const quantity = Number(form.quantity || 0);
    const price = Number(form.price || 0);
    const fees = Number(form.fees || 0);
    const type = form.transactionType;
    if ((!ticker && type !== 'dividend' && type !== 'fee') || !Number.isFinite(quantity) || quantity < 0 || !Number.isFinite(price) || price < 0 || !Number.isFinite(fees) || fees < 0) {
      setError('Enter a ticker for positions, or leave it blank for cash dividends/fees, plus valid non-negative amounts.');
      return;
    }
    if ((type === 'dividend' || type === 'fee') && price <= 0) {
      setError(`${type === 'fee' ? 'Fee' : 'Dividend'} amount must be greater than zero.`);
      return;
    }
    if ((type === 'buy' || type === 'sell') && (quantity <= 0 || price <= 0)) {
      setError('Buy and sell transactions require a quantity and per-unit price greater than zero.');
      return;
    }
    if (type === 'transfer' && (quantity <= 0 || price <= 0)) {
      setError('Transfers require a ticker, a positive quantity, and the per-unit value on the transfer date.');
      return;
    }

    const next = ensureSelectedPortfolio(workspace, form.currency);
    const transaction = createTransaction({
      portfolioId: next.selectedPortfolioId,
      accountId: form.accountId || null,
      ticker,
      transactionType: type,
      quantity,
      price,
      fees,
      transactionDate: form.transactionDate,
      currency: form.currency,
    });
    {
      const ledgerError = validateTransactionLedger([...transactions, transaction], snapshot.openingHoldings);
      if (ledgerError) {
        setError(ledgerError.message);
        return;
      }
    }
    setWorkspace({
      ...next,
      transactions: [...next.transactions, transaction],
    });
    setForm(initialForm);
    setError('');
  };

  const remove = (id) => {
    const remaining = transactions.filter((transaction) => transaction.id !== id);
    const ledgerError = validateTransactionLedger(remaining, snapshot.openingHoldings);
    if (ledgerError) { setError(ledgerError.message); return; }
    setWorkspace({ ...workspace, transactions: workspace.transactions.filter((transaction) => transaction.id !== id) });
    setError('');
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <header className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-indigo-600/20 flex items-center justify-center"><Receipt className="w-5 h-5 text-indigo-400" /></div>
        <div><h1 className="text-2xl font-black text-white">Transactions</h1><p className="text-sm text-gray-500">All recorded buys, sales, transfers, and opening holdings for this portfolio.</p></div>
      </header>

      {!snapshot.valid && <p role="alert" className="text-amber-300">{snapshot.errors.map((item) => item.message).join(' ')}</p>}
      <form onSubmit={add} className="bg-[#11131a]/80 border border-gray-800/50 rounded-2xl p-5">
        <h2 className="text-sm font-bold uppercase tracking-wider text-gray-200 mb-4"><Plus className="inline w-4 h-4 mr-2 text-emerald-400" />Add transaction</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-8 gap-3">
          <label className="text-xs text-gray-500">Account<select name="accountId" value={form.accountId} onChange={update} className={field}><option value="">Unassigned</option>{workspace.accounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</select></label>
          <label className="text-xs text-gray-500">Type<select name="transactionType" value={form.transactionType} onChange={update} className={field}>{transactionTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}</select></label>
          <label className="text-xs text-gray-500">Ticker<input name="ticker" value={form.ticker} onChange={update} placeholder="AAPL" className={field} /></label>
          <label className="text-xs text-gray-500">Quantity<input name="quantity" type="number" min="0" step="any" value={form.quantity} onChange={update} placeholder="10" className={field} /></label>
          <label className="text-xs text-gray-500">Price / amount<input name="price" type="number" min="0" step="any" value={form.price} onChange={update} placeholder="185.50" className={field} /></label>
          <label className="text-xs text-gray-500">Fees<input name="fees" type="number" min="0" step="any" value={form.fees} onChange={update} className={field} /></label>
          <label className="text-xs text-gray-500">Date<input name="transactionDate" type="date" value={form.transactionDate} onChange={update} className={field} /></label>
          <label className="text-xs text-gray-500">Currency<select name="currency" value={form.currency} onChange={update} className={field}><option>USD</option><option>INR</option><option>EUR</option><option>GBP</option></select></label>
          <button className="self-end h-10 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold">Save</button>
        </div>
        {error && <p className="mt-3 text-xs text-rose-400"><AlertCircle className="inline w-4 h-4 mr-1" />{error}</p>}
        <p className="mt-3 text-[11px] text-gray-600">For dividends and fees, use the amount field and leave quantity at zero. For transfers, record the position quantity and price at the transfer date.</p>
      </form>

      <p className="text-sm text-slate-500">Adding a holding records a buy here. Removing a holding through a recorded sale keeps both the purchase and sale visible. Opening positions show previously saved holdings.</p>
      <section className="bg-[#11131a]/80 border border-gray-800/50 rounded-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-800/50 flex justify-between"><h2 className="text-sm font-bold text-white">Activity ledger</h2><span className="text-xs text-gray-500">{sortedTransactions.length} record{sortedTransactions.length === 1 ? '' : 's'}</span></div>
        {sortedTransactions.length === 0 ? <p className="p-10 text-center text-sm text-gray-500">No transactions yet. Add your first buy, sell, dividend, fee, or transfer above.</p> : sortedTransactions.map((transaction) => {
          const type = transaction.transaction_type;
          const isIncome = type === 'sell' || type === 'dividend' || type === 'transfer';
          const amount = Number(transaction.quantity || 0) * Number(transaction.price || 0);
          return <div key={transaction.id} className="px-5 py-4 flex items-center justify-between gap-4 border-b border-gray-800/50 last:border-0">
            <div className="flex items-center gap-3"><div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isIncome ? 'bg-emerald-500/10 text-emerald-400' : 'bg-indigo-500/10 text-indigo-400'}`}>{isIncome ? <ArrowDownLeft className="w-4 h-4" /> : <ArrowUpRight className="w-4 h-4" />}</div><div><p className="font-bold text-white capitalize">{type === 'sell' ? 'Sold / removed' : type === 'buy' ? 'Bought / added' : type} {transaction.ticker && <span className="font-mono">· {transaction.ticker}</span>}</p><p className="text-xs text-gray-500">{transaction.transaction_date || 'Original purchase date unavailable'} · {transaction.quantity || 0} units · {transaction.currency || 'USD'} · {workspace.accounts.find((account) => account.id === transaction.account_id)?.name || 'Unassigned'}</p></div></div>
            <div className="text-right"><p className="font-bold text-gray-200">{money(amount || transaction.price, transaction.currency)}</p><p className="text-xs text-gray-500">Fees {money(transaction.fees, transaction.currency)}</p></div>
            {!transaction.isOpening && <button type="button" onClick={() => remove(transaction.id)} aria-label={`Remove ${type} transaction`} className="text-gray-500 hover:text-rose-400"><Trash2 className="w-4 h-4" /></button>}
          </div>;
        })}
      </section>
      <p className="text-[11px] text-gray-600">Transactions are stored locally and synchronized to Supabase when the portfolio schema and authenticated session are available.</p>
    </div>
  );
}
