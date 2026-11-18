import { securitiesAccountGroups } from '../services/accountSummary';
import React, { useEffect, useState } from 'react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { PortfolioService } from '../services/api';
import { formatMoney } from '../services/portfolioValuation';
import usePortfolioSnapshot from '../hooks/usePortfolioSnapshot';
import { assetCategories, assetValue, trackingTotals } from '../services/assetTracking';
import { LineChart, Pencil, CircleHelp, ListChecks, Plus } from 'lucide-react';

const primary = [
  ['My Portfolio', '/dashboard'],
  ['Advisor', '/dashboard/advisor'],
  ['AI chat', '/dashboard/chat'],
  ['News sentiment', '/dashboard/sentiment'],
  ['Fundamentals', '/dashboard/fundamentals'],
];

const experiments = [
  ['Research', '/dashboard/research'],
  ['Goals', '/dashboard/planning/goals'],
  ['Settings', '/dashboard/settings'],
  ['Stock forecasts', '/dashboard/forecast'],
  ['How estimates work', '/dashboard/ai-architecture'],
  ['Watchlist', '/dashboard/manage'],
  ['Trading experiments', '/dashboard/trading'],
];

export default function Sidebar() {
  const { snapshot, pricing, portfolios, selectPortfolio } = usePortfolioSnapshot();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [connected, setConnected] = useState(null);
  const valuation = snapshot.valuation;
  const assets = snapshot.trackedAssets || [];
  const totals = trackingTotals(assets);
  const currencies = [...new Set([...valuation.currencies, ...Object.keys(totals)])];
  const securitiesAccounts = securitiesAccountGroups(snapshot);
  const netValue = currency => {
    const group = valuation.groups[currency];
    if (!snapshot.valid || (group && (pricing.loading || !group.complete)) || totals[currency] === null) return null;
    return (group?.market || 0) + (totals[currency] || 0);
  };

  useEffect(() => {
    let active = true;
    const check = () => PortfolioService.checkHealth().then((result) => { if (active) setConnected(result.ok); }).catch(() => { if (active) setConnected(false); });
    check();
    const interval = setInterval(check, 30000);
    return () => { active = false; clearInterval(interval); };
  }, []);

  const navLink = ([label, path]) => (
    <NavLink 
      key={path} 
      to={path} 
      end 
      className={({ isActive }) => 
        'group flex items-center justify-between rounded-2xl px-4 py-3 text-sm transition ' + 
        (isActive 
          ? 'bg-blue-50 font-bold text-blue-700'
          : 'text-slate-500 hover:bg-white hover:text-slate-900')
      }
    >
      <span>{label}</span>
      {path === '/dashboard/ai-architecture' && (
        <span className="flex h-2 w-2 rounded-full bg-indigo-500" />
      )}
    </NavLink>
  );

  return (
    <aside className="workspace-sidebar fixed left-0 top-0 z-40 flex h-screen w-[270px] flex-col border-r border-slate-200/80 bg-white px-4 py-5">
      <Link to="/dashboard" className="mb-7 flex items-center gap-3 px-3 py-2 text-[18px] font-black tracking-tight text-slate-950">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white shadow-[0_8px_16px_rgba(91,61,245,0.25)]">
          <LineChart className="h-5 w-5" />
        </span>
        SmartPortfolio
      </Link>

      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
      <section aria-label="Portfolio assets" className="py-1 mb-5">
        <select aria-label="Selected portfolio" value={snapshot.portfolioId || ''}
          onChange={event => selectPortfolio(event.target.value)}
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm">
          {!portfolios.length && <option value="">My Portfolio</option>}
          {portfolios.map(p => <option key={p.id} value={p.id}>{p.name} · {p.savedRecordCount ?? 0} saved records</option>)}
        </select>
        {portfolios.length > 1 && !(portfolios.find(p => p.id === snapshot.portfolioId)?.savedRecordCount) && <div className="text-sm p-2 bg-blue-50 rounded-lg">
          <p>This portfolio is empty. Your other saved portfolios:</p>
          {portfolios.filter(p => p.savedRecordCount > 0).map(p => <button key={p.id} className="block text-blue-700 underline py-1" onClick={() => selectPortfolio(p.id)}>{p.name} · {p.savedRecordCount} saved records</button>)}
        </div>}
        <div className="grid grid-cols-3 gap-2 py-3 text-slate-500">
          {[[Pencil,'Edit','/dashboard/portfolio'],[CircleHelp,'Recs','/dashboard/advisor'],[ListChecks,'Activity','/dashboard/portfolio/transactions']].map(([Icon,label,to]) =>
            <Link key={label} to={to} className="flex flex-col items-center gap-1 text-xs hover:text-blue-600"><Icon size={19}/>{label}</Link>)}
        </div>
        {!snapshot.valid && <p role="alert" className="text-xs text-amber-700">Portfolio history needs correction.</p>}
        <div className="flex items-center justify-between mt-3 mb-1">
          <Link to="/dashboard/portfolio" className="text-sm font-semibold">Securities</Link>
          <Link to="/dashboard/portfolio" aria-label="Add securities" className="p-1 text-blue-600"><Plus size={16}/></Link>
        </div>
        {securitiesAccounts.map(account => <Link key={account.key} to="/dashboard/portfolio" className="flex justify-between gap-2 rounded-md bg-slate-50 px-2 py-1 text-xs">
          <span className="truncate">{account.name}</span><span className="shrink-0">{formatMoney(!snapshot.valid || pricing.loading ? null : account.market,account.currency)} <small>{account.currency}</small></span>
        </Link>)}
        {assetCategories.map(([category,label]) => <div key={category} className="mt-4">
          <div className="flex items-center justify-between">
            <Link to="/dashboard/portfolio" className="text-sm font-semibold">{label}</Link>
            <Link to={'/dashboard/portfolio?addAsset=' + category} aria-label={'Add ' + label.toLowerCase()} className="p-1 text-blue-600"><Plus size={16}/></Link>
          </div>
          {assets.filter(row => row.asset_type === category).map(row => <Link key={row.id} to="/dashboard/portfolio" className="flex justify-between gap-2 px-2 py-1 text-xs hover:bg-slate-50 rounded-md">
            <span className="truncate" title={row.asset_name}>{row.asset_name}</span>
            <span className="shrink-0">{formatMoney(assetValue(row),row.currency)} <small>{row.currency}</small></span>
          </Link>)}
        </div>)}
        <div className="mt-4 border-t border-dashed border-slate-300 pt-3">
          <Link to="/dashboard/portfolio" className="text-sm font-semibold">Net worth ›</Link>
          {currencies.map(currency => <div key={currency} className="flex justify-between mt-2 text-sm"><span className="text-slate-500">{currency}</span><strong>{formatMoney(netValue(currency),currency)}</strong></div>)}
          {!currencies.length && <p className="mt-2 text-xs text-slate-500">Add assets to track net worth.</p>}
          <p className="mt-2 text-[10px] text-slate-400">Currencies shown separately. Asset values are dated estimates.</p>
        </div>
      </section>

      <nav aria-label="Main navigation" className="space-y-1">
        {primary.map(navLink)}
        <details className="mt-5 border-t border-slate-200 pt-4">
          <summary className="cursor-pointer px-4 py-2 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-400">
            More tools
          </summary>
          <p className="px-4 pb-2 text-xs text-slate-400">Optional analysis modules.</p>
          {experiments.map(navLink)}
        </details>
      </nav>
      </div>

      <div className="space-y-3 border-t border-slate-200 pt-4">
        {user && (
          <div className="px-3 py-2 rounded-xl bg-slate-100 border border-slate-200 text-xs">
            <div className="text-[10px] uppercase font-bold text-slate-400">Signed In As</div>
            <div className="font-semibold text-slate-800 truncate" title={user.email}>
              {user.email || 'User'}
            </div>
            <div className="text-[10px] text-indigo-600 font-medium mt-0.5">
              {user.isDemo ? 'Demo Mode' : user.isLocal ? 'Local Workspace' : 'Cloud Account'}
            </div>
          </div>
        )}
        <p className="px-3 text-[11px] font-semibold text-slate-400">
          {connected == null ? 'Connecting to analytics...' : connected ? 'Analytics connected' : 'Analytics unavailable'}
        </p>
        <button 
          onClick={async () => { 
            try { 
              await logout(); 
            } finally { 
              navigate('/auth', { replace: true }); 
            } 
          }} 
          className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-rose-600 hover:bg-rose-50 transition"
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
