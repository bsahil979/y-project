import React from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function Layout({ children, syncStatus }) {
  const { pathname } = useLocation();
  const portfolioPage = ['/dashboard', '/dashboard/', '/dashboard/portfolio', '/dashboard/portfolio/transactions'].includes(pathname);
  const title = portfolioPage ? 'My Portfolio' : ({advisor: 'Advisor', research: 'Research', 'ai-architecture': 'How estimates work', chat: 'AI chat', manage: 'Watchlist', forecast: 'Stock forecasts', sentiment: 'News sentiment', trading: 'Trading experiments', goals: 'Goals', settings: 'Settings', fundamentals: 'Fundamentals'})[pathname.split('/').filter(Boolean).pop()];
  const syncLabels = { loading: 'Loading workspace...', saving: 'Saving changes...', synced: 'Synced', 'local-only': 'Saved on this device', 'sync-failed': 'Sync failed; local copy kept' };
  return <div className="ml-[270px] min-h-screen bg-transparent px-5 py-5 md:px-8 md:py-7">
    <header className="mb-7 flex flex-wrap items-center justify-between gap-4">
      <div><p className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">Workspace</p><p className="mt-1 text-2xl font-black tracking-tight text-slate-950">{title}</p><p className="mt-1 text-xs font-medium text-slate-500">{syncLabels[syncStatus] || 'Your investing dashboard'}</p></div>
      {portfolioPage && <nav aria-label="Portfolio tools" className="flex items-center gap-4"><Link to="/dashboard/portfolio/transactions">Transactions</Link><Link to="/dashboard/portfolio" className="rounded-full bg-[#5b3df5] px-5 py-2.5 text-sm font-bold text-[#ffffff] shadow-[0_8px_18px_rgba(91,61,245,0.2)] transition hover:-translate-y-0.5 hover:bg-[#4930d6]">Manage holdings</Link></nav>}
    </header>
    <main>{syncStatus === 'loading' ? <p role="status" className="rounded-[28px] bg-white p-12 text-center text-sm text-slate-500 shadow-[0_8px_30px_rgba(15,23,42,0.04)]">Loading your saved portfolio before enabling edits…</p> : children}</main>
  </div>;
}
