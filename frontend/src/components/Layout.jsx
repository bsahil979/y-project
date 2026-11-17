import React, {useState} from 'react';
import {useAuth} from '../contexts/AuthContext';
import {Search} from 'lucide-react';
import { Link, NavLink, useLocation } from 'react-router-dom';

export default function Layout({ children, syncStatus }) {
  const { pathname } = useLocation();
  const {user} = useAuth();
  const firstName = (user?.user_metadata?.full_name || user?.name || '').trim().split(' ')[0];
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  const isTrack = pathname === '/dashboard' || pathname === '/dashboard/';
  const [query,setQuery] = useState('');
  const destinations = [['Holdings','/dashboard/portfolio'],['Transactions','/dashboard/portfolio/transactions'],['Advisor','/dashboard/advisor'],['AI chat','/dashboard/chat'],['News sentiment','/dashboard/sentiment'],['Fundamentals','/dashboard/fundamentals'],['Goals','/dashboard/planning/goals'],['Research','/dashboard/research'],['Stock forecasts','/dashboard/forecast'],['Settings','/dashboard/settings']];
  const portfolioPage = ['/dashboard', '/dashboard/', '/dashboard/portfolio', '/dashboard/portfolio/transactions'].includes(pathname);
  const title = portfolioPage ? 'My Portfolio' : ({advisor: 'Advisor', research: 'Research', 'ai-architecture': 'How estimates work', chat: 'AI chat', manage: 'Watchlist', forecast: 'Stock forecasts', sentiment: 'News sentiment', trading: 'Trading experiments', goals: 'Goals', settings: 'Settings', fundamentals: 'Fundamentals'})[pathname.split('/').filter(Boolean).pop()];
  const syncLabels = { loading: 'Loading workspace...', saving: 'Saving changes...', synced: 'Synced', 'local-only': 'Saved on this device', 'sync-failed': 'Sync failed; local copy kept' };
  return <div className="workspace-main ml-[270px] min-h-screen bg-white px-5 pb-5 md:px-7">
    <nav aria-label="Workspace sections" className="workspace-topbar">
      <div className="workspace-tabs">
        {[['Track', '/dashboard'], ['Plan', '/dashboard/planning/goals'], ['Improve', '/dashboard/advisor'], ['Explore', '/dashboard/manage']].map(([label, path]) => <NavLink key={path} to={path} end className={({isActive}) => isActive ? 'selected' : ''}>{label}</NavLink>)}
      </div>
      <div className="workspace-search"><Search size={17}/><input aria-label="Find a portfolio tool" placeholder="Find holdings, analysis & more..." value={query} onChange={e=>setQuery(e.target.value)} />{query.trim() && <div className="workspace-search-results">{destinations.filter(([label])=>label.toLowerCase().includes(query.toLowerCase().trim())).map(([label,to])=><Link key={to} to={to} onClick={()=>setQuery('')}>{label}</Link>)}{!destinations.some(([label])=>label.toLowerCase().includes(query.toLowerCase().trim())) && <p>No matching tool</p>}</div>}</div>
      <div className="workspace-actions"><Link to="/dashboard/portfolio">+ Add asset</Link><Link to="/dashboard/chat">Assistant</Link></div>
    </nav>
    <header className="workspace-page-heading mb-6 pt-6 flex flex-wrap items-center justify-between gap-4">
      <div><p className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">SmartPortfolio</p><p className="mt-1 text-2xl font-black tracking-tight text-slate-950">{isTrack ? `${greeting}${firstName ? ', ' + firstName : ''}.` : title}{isTrack && <span className="workspace-greeting-note"> Here’s where you stand.</span>}</p><p className="mt-1 text-xs font-medium text-slate-500">{syncLabels[syncStatus] || 'Your investing dashboard'}</p></div>
      {portfolioPage && <nav aria-label="Portfolio tools" className="flex items-center gap-4"><Link to="/dashboard/portfolio/transactions">Transactions</Link><Link to="/dashboard/portfolio" className="rounded-full bg-[#5b3df5] px-5 py-2.5 text-sm font-bold text-[#ffffff] shadow-[0_8px_18px_rgba(91,61,245,0.2)] transition hover:-translate-y-0.5 hover:bg-[#4930d6]">Manage holdings</Link></nav>}
    </header>
    <main>{syncStatus === 'loading' ? <p role="status" className="rounded-[28px] bg-white p-12 text-center text-sm text-slate-500 shadow-[0_8px_30px_rgba(15,23,42,0.04)]">Loading your saved portfolio before enabling edits…</p> : children}</main>
  </div>;
}
