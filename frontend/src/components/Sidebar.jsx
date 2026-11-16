import React, { useEffect, useState } from 'react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { PortfolioService } from '../services/api';
import { formatMoney } from '../services/portfolioValuation';
import usePortfolioSnapshot from '../hooks/usePortfolioSnapshot';
import { LineChart, Sparkles } from 'lucide-react';

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
          ? 'bg-[#eeeaff] font-bold text-[#5b3df5] shadow-[inset_3px_0_0_#5b3df5]' 
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
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-[270px] flex-col border-r border-slate-200/80 bg-[#f8f9fc] px-4 py-5">
      <Link to="/dashboard" className="mb-7 flex items-center gap-3 px-3 py-2 text-[18px] font-black tracking-tight text-slate-950">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#5b3df5] text-white shadow-[0_8px_16px_rgba(91,61,245,0.25)]">
          <LineChart className="h-5 w-5" />
        </span>
        SmartPortfolio
      </Link>

      <div className="my-1 space-y-3 rounded-[22px] border border-slate-200 bg-white p-4 shadow-[0_8px_22px_rgba(15,23,42,0.04)]">
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">Selected portfolio</p>
        {portfolios.length > 0 && (
          <select 
            aria-label="Selected portfolio" 
            value={snapshot.portfolioId || ''} 
            onChange={(event) => selectPortfolio(event.target.value)} 
            className="w-full rounded-lg border border-slate-200 bg-white p-1 text-sm"
          >
            {portfolios.map((portfolio) => <option key={portfolio.id} value={portfolio.id}>{portfolio.name}</option>)}
          </select>
        )}
        {!snapshot.valid && <p role="alert" className="text-xs text-amber-700">Portfolio history needs correction.</p>}
        {!valuation.currencies.length && <p className="text-sm text-slate-500">Add your first holding</p>}
        {valuation.currencies.map((currency) => (
          <div key={currency}>
            <p className="text-xs text-slate-500">{currency}</p>
            <p className="text-lg font-bold text-slate-900">
              {!snapshot.valid ? 'Unavailable' : pricing.loading ? 'Loading prices...' : formatMoney(valuation.groups[currency].market, currency)}
            </p>
          </div>
        ))}
        <p className="text-[11px] leading-5 text-slate-400">Currencies shown separately. Quotes may be delayed.</p>
      </div>

      <nav aria-label="Main navigation" className="min-h-0 flex-1 overflow-y-auto space-y-1">
        {primary.map(navLink)}
        <details className="mt-5 border-t border-slate-200 pt-4">
          <summary className="cursor-pointer px-4 py-2 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-400">
            More tools
          </summary>
          <p className="px-4 pb-2 text-xs text-slate-400">Optional analysis modules.</p>
          {experiments.map(navLink)}
        </details>
      </nav>

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
