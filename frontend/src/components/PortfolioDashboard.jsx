import FundAdvisor from './FundAdvisor';
import {assetValue, trackingTotals} from '../services/assetTracking';
import AdvisorAnalytics from './AdvisorAnalytics';
import { Link, useLocation } from 'react-router-dom';
import React, { useState, useEffect } from 'react';
import {
  TrendingUp, TrendingDown, Loader2, AlertTriangle, Brain, Briefcase,
  Target, Shield, BarChart3, PieChart as PieIcon,
  Zap, ChevronRight,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Legend,
  PieChart as RechartsPieChart, Pie, Treemap,
} from 'recharts';
import { PortfolioService } from '../services/api';
import { analysisRequest, combinedAnalysisRequest, formatMoney } from '../services/portfolioValuation';
import usePortfolioSnapshot from '../hooks/usePortfolioSnapshot';

const COLORS = ['#2343b5', '#1668ce', '#3b7ff5', '#61a2f8', '#df72ef', '#edacf7', '#075b53', '#354256'];

const PortfolioDashboard = ({ advisor = false }) => {
  const { search } = useLocation();
  const scope = new URLSearchParams(search);
  const [preview, setPreview] = useState('saved');
  const { snapshot, pricing } = usePortfolioSnapshot();
  const [activeTab, setActiveTab] = useState('overview');
  const [dismissedRecommendations, setDismissedRecommendations] = useState([]);
  const [selectedCurrency, setSelectedCurrency] = useState(scope.get('currency') || 'INR');
  const [analysis, setAnalysis] = useState({ key: '', data: null, error: '' });
  const allHoldings = snapshot.holdings;
  const valued = snapshot.valuation;
  const [combineHoldings, setCombineHoldings] = useState(scope.get('mixed') === '1');
  const mixed = valued.currencies.length === 2 && valued.currencies.includes('USD') && valued.currencies.includes('INR');
  const combined = mixed && combineHoldings;
  const currency = valued.groups[selectedCurrency] ? selectedCurrency : valued.currencies[0];
  const localGroup = valued.groups[currency];
  const request = snapshot.valid ? (combined ? combinedAnalysisRequest(valued, currency, snapshot)
    : analysisRequest(localGroup, snapshot)) : null;
  if (request && advisor && preview !== 'saved') {
    Object.assign(request, { risk_preference: 'aggressive', investment_horizon_years: Number(preview), horizon_source: 'explicit' });
  }
  if (request) request.include_optional_ml = advisor;
  const requestJson = request ? JSON.stringify(request) : '';
  const analysisKey = (snapshot.portfolioId || '') + ':' + (snapshot.portfolioRevision || '') + ':' + requestJson + ':' + pricing.revision;
  const isStale = Boolean(analysis.data?.portfolio_revision && snapshot.portfolioRevision && analysis.data.portfolio_revision !== snapshot.portfolioRevision);
  const loading = (Boolean(requestJson) && analysis.key !== analysisKey) || isStale;
  const data = (analysis.key === analysisKey && !isStale) ? analysis.data : null;
  const error = (analysis.key === analysisKey && !isStale) ? analysis.error : '';
  const group = combined && data ? {tickers: data.tickers, weights: data.weights,
    market: data.portfolio_value, marketByTicker: data.position_values_base, complete: true,
    cost: null, pnl: null, pnlPct: null} : localGroup;
  const currencyControls = <div className="flex flex-wrap items-center gap-3 text-sm text-gray-300">
    {advisor && <label>Allocation scenario <select value={preview} onChange={e => setPreview(e.target.value)} className="ml-2 rounded-lg border p-2">
      <option value="saved">My saved profile</option><option value="10">Preview aggressive · 10 years</option><option value="1">Preview aggressive · 1 year</option>
    </select></label>}
    <label>Portfolio currency <select aria-label="Portfolio currency" value={currency || ''} onChange={(event) => setSelectedCurrency(event.target.value)} className="ml-2 rounded-lg border border-gray-700 bg-[#11131a] p-2">{valued.currencies.map((code) => <option key={code} value={code}>{code}</option>)}</select></label>
    <button onClick={pricing.refresh} disabled={pricing.loading} className="rounded-lg border border-gray-700 px-3 py-2 disabled:opacity-50">Refresh prices and analysis</button>
    {mixed && <label><input type="checkbox" checked={combineHoldings} onChange={event => setCombineHoldings(event.target.checked)} /> Include both currencies in {currency}</label>}
    {!combined && valued.currencies.length > 1 && <span className="text-xs text-gray-400">Select a currency to view its holdings.</span>}
  </div>;

  useEffect(() => {
    if (!requestJson) return;
    let active = true;
    const timer = setTimeout(() => { if (active) { active = false; setAnalysis({key:analysisKey, data:null, error:'Analysis is taking longer than expected. Your saved holdings are unchanged. Please retry shortly.'}); } }, 120000);
    PortfolioService.getPortfolioAnalysis(JSON.parse(requestJson), pricing.revision > 0)
      .then((result) => { if (active) { clearTimeout(timer); const stale = result?.portfolio_revision && result.portfolio_revision !== snapshot.portfolioRevision; setAnalysis({ key:analysisKey, data:stale ? null : result, error:stale ? 'Analysis returned an older portfolio version. Refresh prices and analysis to retry.' : '' }); } })
      .catch((err) => { if (active) setAnalysis({ key: analysisKey, data: null, error: err?.response?.data?.detail || err?.message || 'Analysis unavailable' }); });
    return () => { active = false; clearTimeout(timer); };
  }, [requestJson, analysisKey, pricing.revision]);

  const savedOverview = <section className="rounded-xl border p-5"><h2 className="text-lg font-semibold">Your saved holdings</h2><p className="text-sm text-slate-500">Stock analysis is separate from mutual funds and other dated assets.</p><div className="overflow-auto"><table className="w-full text-left mt-3"><thead><tr><th>Asset</th><th>Units</th><th>Market / recorded value</th></tr></thead><tbody>
    {allHoldings.map((h,i) => <tr key={h.id || i}><td className="py-2">{h.ticker}</td><td>{h.quantity}</td><td>{h.market == null ? 'Price unavailable' : formatMoney(h.market,h.currency)}</td></tr>)}
    {(snapshot.trackedAssets || []).map((h,i) => <tr key={h.id || `asset-${i}`}><td className="py-2">{h.asset_name || h.ticker}</td><td>{h.quantity}</td><td>{formatMoney(assetValue(h),h.currency)}</td></tr>)}
  </tbody></table></div><Link className="text-blue-700 underline" to="/dashboard/portfolio">Manage holdings</Link></section>;

  if (!snapshot.valid) return <p role="alert" className="text-amber-300">{snapshot.errors.map((item) => item.message).join(" ")}</p>;
  if (!allHoldings.length && snapshot.trackedAssets?.length) {
    const assets = snapshot.trackedAssets, totals = trackingTotals(assets);
    return <div className="space-y-5">
      <section className="rounded-xl border p-6"><h2 className="text-xl font-semibold">Your investments</h2>
        {Object.entries(totals).map(([code,total]) => <p key={code} className="text-3xl font-semibold mt-3">{formatMoney(total,code)} <small className="text-sm">{code}</small></p>)}
        <p className="text-slate-500 mt-3">Based on saved NAVs and dated valuations. Values may differ from today's market.</p>
      </section>
      <section className="rounded-xl border p-6"><h2 className="text-xl font-semibold">Holdings</h2><div className="overflow-auto"><table className="w-full text-left mt-4"><thead><tr>{['Asset','Units','Cost per unit','NAV / value per unit','Current value','Valuation date'].map(h=><th key={h} className="p-3">{h}</th>)}</tr></thead>
        <tbody>{assets.map(a=><tr key={a.id} className="border-t"><td className="p-3">{a.asset_name || a.ticker}<small className="block text-slate-500">{a.asset_type?.replaceAll('_',' ')}</small></td><td className="p-3">{a.quantity}</td><td className="p-3">{formatMoney(a.average_cost,a.currency)}</td><td className="p-3">{formatMoney(a.manual_value,a.currency)}</td><td className="p-3">{formatMoney(assetValue(a),a.currency)}</td><td className="p-3">{a.valuation_date || 'Unavailable'}<small className="block">{a.valuation_source}</small></td></tr>)}</tbody></table></div>
      </section>
      <FundAdvisor snapshot={snapshot} />
      <Link className="text-blue-700 underline" to="/dashboard/portfolio">Manage holdings and update NAVs</Link>
    </div>;
  }
  if (!allHoldings.length) return <div className="rounded-2xl border border-gray-800 p-8 text-center text-gray-300"><Briefcase className="mx-auto mb-3 h-10 w-10" /><h2 className="text-xl font-semibold">Start with your holdings</h2><p className="mt-2">Add positions in My Holdings or record transactions. A watchlist alone is not an owned portfolio.</p></div>;
  if (pricing.loading || loading) return <div className="space-y-5">{currencyControls}<div className="flex items-center gap-3 text-gray-300"><Loader2 className="h-6 w-6 animate-spin" />{pricing.loading ? 'Loading the latest available quotes...' : 'Analyzing current market-value weights...'}</div>{savedOverview}</div>;
  if (!request) return <div className="space-y-4">{currencyControls}<div className="rounded-2xl border border-amber-600/40 p-6 text-gray-300"><h2 className="font-semibold">Complete pricing is required for analysis</h2><p className="mt-2">{pricing.error || (!['INR', 'USD'].includes(currency) ? 'Analysis currently supports INR and USD portfolios.' : 'Some positions have unavailable or mismatched prices. Recorded costs are available in My Holdings; they are not used as substitute prices.')}</p><ul className="mt-3 list-disc pl-5">{group?.missing.map((item, index) => <li key={index}>{item.ticker}: {item.reason}</li>)}</ul></div></div>;
  if (error) return <div className="space-y-4">{currencyControls}<p role="alert" className="text-amber-300">Analysis unavailable: {error}</p>{savedOverview}</div>;
  if (!data) return null;

  const riskSummary = data.risk_engine || {};
  const benchmark = data.benchmark || {};
  const attribution = data.attribution || {};
  const riskBudget = data.risk_budget || {};
  const recommendations = data.recommendations || [];

  const volData = riskSummary["Volatility (Annual)"] || {};
  const varData = riskSummary["VaR (95%)"] || {};
  const cvarData = riskSummary["CVaR (95%)"] || {};
  const drawdownData = riskSummary["Max Drawdown"] || {};
  const tickersList = Object.keys(volData);

  // Benchmark comparison
  const benchComp = benchmark.comparison || {};
  const benchPortfolio = benchmark.portfolio || {};
  const benchIndex = benchmark.benchmark || {};

  // Attribution data
  const secContrib = attribution.security_contribution || [];
  const sectorContrib = attribution.sector_contribution || [];

  // Risk budget
  const riskContrib = riskBudget.risk_contributions || [];

  // Tabs
  const tabs = [
    { id: 'overview', label: 'Overview', icon: PieIcon },
    { id: 'risk', label: 'Risk & Budget', icon: Shield },
    { id: 'performance', label: 'Performance', icon: TrendingUp },
  ];

  const allocation = data.personalized_allocation;
  const biggestRisk = riskContrib.reduce((largest, row) => !largest || row.percentage_contribution_to_risk > largest.percentage_contribution_to_risk ? row : largest, null);
  if (advisor) {
    const actions = (Array.isArray(recommendations) ? recommendations : []).filter(rec => rec && !dismissedRecommendations.includes(rec.id));
    const priorityActions = ['reduce_position', 'de-risk', 'add_diversification', 'rebalance'];
    const ordered = [...actions].sort((a,b) => {
      const rank = rec => {const i = priorityActions.indexOf(rec.action); return i < 0 ? priorityActions.length : i;};
      return rank(a) - rank(b);
    });
    const horizon = allocation?.investment_horizon_years ?? request.investment_horizon_years;
    return <div className="space-y-6 text-slate-900">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="text-xs font-semibold uppercase tracking-widest text-blue-600">Your portfolio advisor</p>
        <h2 className="mt-2 text-3xl font-semibold">A clearer plan for your investments</h2>
        <p className="mt-2 text-sm text-slate-500">Review the risks, understand the suggestions, then decide what to change.</p></div>
        <Link to="/dashboard/settings" className="rounded-lg border border-blue-200 px-4 py-2 text-sm text-blue-600">Edit investment preferences</Link>
      </header>
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">{currencyControls}</div>
      {preview !== 'saved' && <p role="status" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">Scenario preview only. Your saved preferences and holdings have not changed.</p>}
      <div className="grid gap-4 sm:grid-cols-3">
        <section className="rounded-xl border border-slate-200 p-5"><p className="text-sm text-slate-500">Investment approach</p><p className="mt-2 text-xl font-semibold capitalize">{allocation?.applied_profile || request.risk_preference}</p></section>
        <section className="rounded-xl border border-slate-200 p-5"><p className="text-sm text-slate-500">Planning horizon</p><p className="mt-2 text-xl font-semibold">{horizon == null ? 'Not set' : Number(horizon).toFixed(1) + ' years'}</p></section>
        <section className="rounded-xl border border-slate-200 p-5"><p className="text-sm text-slate-500">Portfolio reviewed</p><p className="mt-2 text-xl font-semibold">{formatMoney(group.market, currency)}</p><p className="mt-1 text-xs text-slate-500">{data.tickers.length} stocks / {currency}</p></section>
      </div>
      <section className="rounded-xl border border-blue-200 bg-blue-50 p-5">
        <h3 className="font-semibold">What this review covers</h3>
        <p className="mt-2 text-sm text-slate-600">Suggestions use your stock holdings and latest available market prices. Cash, mutual funds, property and other manually valued assets are tracked in net worth but are not included in this optimization.</p>
      </section>
      <AdvisorAnalytics data={data} currency={currency} />
      <section id="advisor-next-steps" className="space-y-3 scroll-mt-24">
        <div className="flex items-center justify-between gap-3"><h3 className="text-xl font-semibold">Your next steps</h3><span className="text-sm text-slate-500">{ordered.length} suggestions</span></div>
        <p className="text-sm text-slate-500">Concentration and risk reviews appear first, followed by diversification and rebalancing.</p>
        {ordered.length ? <div className="grid gap-4 xl:grid-cols-3">{ordered.slice(0,3).map((rec,index) => <article key={rec.id || index} className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-3"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-50 text-sm font-semibold text-blue-600">{index+1}</span><h4 className="font-semibold capitalize">{String(rec.action || 'Review portfolio').replaceAll('_',' ')}{rec.asset ? ' / ' + rec.asset : ''}</h4></div>
          <p className="mt-3 text-sm leading-relaxed text-slate-600">{String(rec.reason || rec.description || '')}</p>
          {rec.expected_impact && <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm"><strong>Why consider it: </strong>{String(rec.expected_impact)}</p>}
          {Array.isArray(rec.supporting_models) && <p className="mt-3 text-xs text-slate-500">Based on: {rec.supporting_models.join(', ')}</p>}
        </article>)}</div> : <p role="status" className="rounded-xl border p-5 text-sm text-slate-600">{['FAILED','UNAVAILABLE'].includes(data.stages?.recommendations?.status) ? 'Recommendations are unavailable. Refresh analysis to retry.' : 'No additional recommendations were returned for this analysis. Review the allocation and your preferences below.'}</p>}
        {ordered.length > 3 && <p className="text-sm text-slate-500">{ordered.length-3} more suggestions are available in the detailed review below.</p>}
      </section>
      {allocation ? <section className="rounded-xl border border-slate-200 p-5 space-y-4">
        <h3 className="text-xl font-semibold">Current holdings vs suggested allocation</h3>
        <p className="text-sm text-slate-600">{String(allocation.objective_used || 'Unavailable').replaceAll('_',' ')} / Maximum position: {Number.isFinite(allocation.max_weight_cap) ? (allocation.max_weight_cap*100).toFixed(1)+'%' : 'Unavailable'}</p>
        {allocation.success ? <div className="overflow-x-auto"><AllocationComparison data={data}/></div> : <p role="status" className="rounded-lg bg-amber-50 p-3 text-amber-800">{allocation.reason || 'No feasible allocation is available.'}</p>}
        {allocation.feasibility_floor_applied && <p className="text-sm">The position cap uses the minimum feasible weight for this number of stocks.</p>}
        {allocation.target_return_adjusted && <p className="text-sm">The return target was lowered to fit the position cap.</p>}
        <p className="text-xs text-slate-500">Model estimates before trading costs and taxes. No trades are placed by this page.</p>
        {allocation.success && preview === 'saved' && !combined && <Link className="inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white" to="/dashboard/chat" state={{allocationCurrency:currency,portfolioId:snapshot.portfolioId}}>Discuss this allocation with AI chat</Link>}
      </section> : <p role="status">Profile allocation unavailable.</p>}
      <details className="rounded-xl border border-slate-200 p-5"><summary className="cursor-pointer font-semibold">Detailed model comparisons and all recommendations</summary><div className="mt-5">{renderRecommendations()}</div></details>
    </div>;
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {currencyControls}
      <p className="text-sm text-gray-400">Analysis uses current market-value weights from the latest available quotes, which may be delayed. Suggested allocations are model estimates.</p>
      {/* Tab Navigation & Refresh */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-[#11131a]/80 border border-gray-800/50 rounded-xl p-1.5">
        <div className="flex flex-wrap gap-1 w-full sm:w-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-indigo-600/20 text-white border border-indigo-500/30'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/30'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && renderOverview()}
      {activeTab === 'risk' && renderRisk()}
      {activeTab === 'risk' && Object.entries(data.stress_test?.scenarios || {}).map(([scenario, result]) =>
        <details key={scenario} className="rounded-xl border border-gray-800 p-4">
          <summary>{scenario} · {formatMoney(result.value_change, currency)}</summary>
          <p>Gain required to recover: {result.recovery_gain_required == null ? 'Unavailable' : (result.recovery_gain_required * 100).toFixed(1) + '%'}</p>
          <table className="w-full text-sm"><thead><tr><th>Holding</th><th>Method</th><th>Shock</th><th>Value change</th></tr></thead>
          <tbody>{Object.entries(result.holdings).map(([ticker, h]) => <tr key={ticker}><td>{ticker}</td>
            <td>{h.scenario_method === 'realized_historical_replay' ? 'Historical window' : 'Beta and residual risk'}</td>
            <td>{(h.holding_shock * 100).toFixed(1)}%</td><td>{formatMoney(h.value_change, currency)}</td></tr>)}</tbody></table>
        </details>)}
      {activeTab === 'performance' && renderPerformance()}
    </div>
  );

  // ── Tab Renderers ──────────────────────────────────────

  function renderOverview() {
    const allocationRows = group.tickers.map((ticker, index) => (() => {
      const positions = allHoldings.filter(h => h.ticker === ticker && h.currency === currency);
      const cost = positions.reduce((sum,h) => sum + (Number(h.cost) || 0),0);
      const market = group.marketByTicker[ticker];
      return {ticker, market, weight:group.weights[index], currency,
        performance: !combined && cost > 0 ? (market / cost - 1) * 100 : null};
    })());
    return <div className="space-y-5">
      <div className="assessment-banner"><div><h2>Review your portfolio assessment</h2><p>See your largest risks and allocation suggestions based on your investment profile.</p></div><Link to={`/dashboard/advisor?currency=${currency}&mixed=${combined ? 1 : 0}`}>See assessment →</Link></div>
      <div className="portfolio-overview-grid">
        <section className="holdings-map-panel">
          <div className="holdings-map-heading"><div><h2>Your holdings at a glance</h2><p className="holdings-map-total" style={{color:group.pnl == null ? '#292929' : group.pnl >= 0 ? '#008653' : '#c40e42'}}>{group.pnl == null ? formatMoney(group.market,currency) : `${group.pnl >= 0 ? '+' : ''}${formatMoney(group.pnl,currency)}`}<small>{group.pnlPct == null ? '' : ` ${group.pnlPct >= 0 ? '+' : ''}${group.pnlPct.toFixed(1)}%`}</small></p><p className="text-sm text-slate-500">{allocationRows.length} holdings · {group.pnl == null ? "current market value" : "unrealized gain/loss since purchase"}</p></div><span className="holdings-view-label">Holdings</span></div>
          <div className="holdings-map-canvas"><ResponsiveContainer width="100%" height="100%">
            <Treemap data={allocationRows.filter(r => r.market > 0).map(r => ({...r, name:r.ticker}))} dataKey="market" aspectRatio={1.5} isAnimationActive={false}
              content={<AllocationTile />}><Tooltip content={<AllocationTooltip />} /></Treemap>
          </ResponsiveContainer></div>
          <p className="text-xs">Tile area shows current market value. Colors and percentages show unrealized gain/loss against recorded purchase cost, not 30-day returns.</p>
          <div className="flex flex-wrap gap-4 mt-3 text-xs text-slate-600"><span>🟩 Gain</span><span>🟥 Loss</span><span>Deeper color = larger change</span><span>Gray = unavailable</span></div>
        </section>
        <aside className="portfolio-pulse"><h2>Portfolio pulse</h2>
          <section><h3>Risk concentration</h3><p>{biggestRisk ? `${biggestRisk.ticker} contributes ${biggestRisk.percentage_contribution_to_risk.toFixed(1)}% of portfolio volatility.` : 'Risk contributions are unavailable.'}</p><button onClick={() => setActiveTab('risk')}>Review risk →</button></section>
          <section><h3>Your investment plan</h3><p>{allocation?.applied_profile || request.risk_preference} profile · {request.investment_horizon_years == null ? 'Horizon unspecified' : request.investment_horizon_years.toFixed(1) + ' years'}</p><Link to="/dashboard/settings">Update preferences →</Link></section>
          <section><h3>News and sentiment</h3><p>Explore available headlines and sentiment for the stocks you follow.</p><Link to="/dashboard/sentiment">Read market news →</Link></section>
        </aside>
      </div>
      <div className="track-quick-actions"><Link to="/dashboard/portfolio"><Briefcase size={30}/><div><strong>Connect your accounts →</strong><p>Bring your broker and manual holdings together.</p></div></Link><Link to="/dashboard/advisor"><BarChart3 size={30}/><div><strong>Review your investment strategy →</strong><p>Explore risk and allocation with your saved profile.</p></div></Link></div>
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Holdings value" value={formatMoney(group.market, currency)} subtitle="Latest available quotes" />
        <StatCard label="Risk preference" value={allocation?.applied_profile || request.risk_preference} subtitle={request.investment_horizon_years == null ? 'Horizon unspecified' : request.investment_horizon_years.toFixed(1) + ' year horizon'} />
        <StatCard label="Largest contributor to risk" value={biggestRisk?.ticker || 'Unavailable'} subtitle={biggestRisk ? biggestRisk.percentage_contribution_to_risk.toFixed(1) + '% of portfolio volatility' : 'Risk contributions unavailable'} />
      </div>
      <div className="rounded-2xl border border-gray-800 p-5 text-gray-300">
        <h2 className="mb-3 font-semibold">Your current allocation ({currency})</h2>
        <table className="w-full text-sm"><thead><tr><th className="py-2 text-left">Stock</th><th className="text-right">Market value</th><th className="text-right">Weight</th></tr></thead><tbody>{allocationRows.map((row) => <tr key={row.ticker}><td className="py-2">{row.ticker}</td><td className="text-right">{formatMoney(row.market, currency)}</td><td className="text-right">{(row.weight * 100).toFixed(1)}%</td></tr>)}</tbody></table>
        <p className="mt-3 text-xs text-gray-400">{combined ? `Values use USD/INR ${data.fx_rate_inr_per_usd} on ${data.valuation_date}. Weight is each converted value divided by the combined total.` : 'Weight is each position’s market value divided by the total in this currency.'} These weights are used throughout the risk and allocation analysis.</p>
      </div>
      <Link to={`/dashboard/advisor?currency=${currency}&mixed=${combined ? 1 : 0}`} className="inline-block rounded-lg bg-indigo-600 px-4 py-2 text-white">Review suggested allocation</Link>
    </div>;
  }

  function renderRisk() {
    const rb = riskBudget;
    return (
      <div className="grid grid-cols-12 gap-6">
        {/* Risk Contributions */}
        <div className="col-span-6 bg-[#11131a]/80 border border-gray-800/50 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Risk Contribution</h3>
          <p className="text-xs text-gray-500 mb-4">
            Portfolio volatility: <span className="text-white font-bold">{(rb.portfolio_volatility * 100).toFixed(1)}%</span>
            {' '}· Risk concentration: <span className="text-white font-bold">{rb.risk_concentration}</span>
            {' '}· Diversification ratio: <span className="text-white font-bold">{rb.diversification_ratio?.toFixed(2)}</span>
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={riskContrib} barCategoryGap="30%">
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                <XAxis dataKey="ticker" stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} unit="%" />
                <Tooltip contentStyle={{ backgroundColor: '#ffffff', color: '#182230', border: '1px solid #e5e7eb', borderRadius: '12px' }} />
                <Bar dataKey="percentage_contribution_to_risk" name="Risk %" fill="#1668ce" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 space-y-2">
            {riskContrib.map((r) => (
              <div key={r.ticker} className="flex justify-between items-center text-xs">
                <span className="text-gray-400">{r.ticker}</span>
                <div className="flex gap-4">
                  <span className="text-gray-500">W: {(r.weight * 100).toFixed(0)}%</span>
                  <span className="text-white font-bold">{r.percentage_contribution_to_risk.toFixed(1)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Risk Summary Table */}
        <div className="col-span-6 bg-[#11131a]/80 border border-gray-800/50 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-2">Historical Risk Metrics by Holding</h3>
          <p className="mb-4 text-xs text-gray-500">Uses daily returns over the selected history. Volatility is annualized (252 trading days); VaR is the 5th-percentile daily return; CVaR is the average return in that worst 5% tail. VaR and CVaR are signed returns, so losses appear negative. Maximum drawdown is the largest peak-to-trough fall in this window.</p>
          <p className="mb-4 text-xs text-gray-500">Price history: {data.market_data?.provider || 'source unavailable'} · {data.market_data?.price_field || 'price convention unavailable'} · {data.market_data?.first_observation || '—'} to {data.market_data?.last_observation || '—'} ({data.market_data?.price_observations ?? '—'} complete observations; {data.market_data?.dropped_incomplete_rows ?? 0} incomplete dates excluded). Missing dates are excluded rather than filled with stale prices.</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-800/50">
                  <th className="text-left py-2 text-gray-400">Ticker</th>
                  <th className="text-right py-2 text-gray-400">Annualized Volatility</th>
                  <th className="text-right py-2 text-gray-400">Daily VaR (95%)</th>
                  <th className="text-right py-2 text-gray-400">Daily CVaR (95%)</th>
                  <th className="text-right py-2 text-gray-400">Max Drawdown</th>
                </tr>
              </thead>
              <tbody>
                {tickersList.map((ticker) => (
                  <tr key={ticker} className="border-b border-gray-800/30">
                    <td className="py-2 text-gray-300">{ticker}</td>
                    <td className="py-2 text-right text-gray-300">{((volData[ticker] || 0) * 100).toFixed(1)}%</td>
                    <td className="py-2 text-right text-gray-300">{((varData[ticker] || 0) * 100).toFixed(1)}%</td>
                    <td className="py-2 text-right text-gray-300">{((cvarData[ticker] || 0) * 100).toFixed(1)}%</td>
                    <td className="py-2 text-right text-gray-300">{((drawdownData[ticker] || 0) * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Correlation Matrix */}
          {data.correlation?.matrix && (
            <div className="mt-6">
              <h4 className="text-sm font-medium text-gray-400 mb-3">Correlation Matrix</h4>
              <CorrelationMatrix data={data.correlation} />
            </div>
          )}
        </div>
      </div>
    );
  }

  function renderPerformance() {
    const comp = benchComp;
    return (
      <div className="grid grid-cols-12 gap-6">
        {/* Benchmark Comparison */}
        <div className="col-span-6 bg-[#11131a]/80 border border-gray-800/50 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">
            Benchmark Comparison — Portfolio vs {benchmark.benchmark_display || 'SPY'}
          </h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-gray-800/30 rounded-xl p-3">
              <span className="text-xs text-gray-500">Alpha</span>
              <p className={`text-lg font-bold ${comp.alpha >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>{(comp.alpha * 100).toFixed(1)}%</p>
            </div>
            <div className="bg-gray-800/30 rounded-xl p-3">
              <span className="text-xs text-gray-500">Information Ratio</span>
              <p className={`text-lg font-bold ${comp.information_ratio >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>{comp.information_ratio?.toFixed(3)}</p>
            </div>
            <div className="bg-gray-800/30 rounded-xl p-3">
              <span className="text-xs text-gray-500">Beta</span>
              <p className="text-lg font-bold text-gray-300">{comp.beta?.toFixed(3)}</p>
            </div>
            <div className="bg-gray-800/30 rounded-xl p-3">
              <span className="text-xs text-gray-500">Tracking Error</span>
              <p className="text-lg font-bold text-gray-300">{(comp.tracking_error * 100).toFixed(1)}%</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <h4 className="text-xs text-gray-500 uppercase mb-2">Portfolio</h4>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between"><span>Total Return</span><span className="text-white">{(benchPortfolio.total_return * 100).toFixed(1)}%</span></div>
                <div className="flex justify-between"><span>Annualized</span><span className="text-white">{(benchPortfolio.annualized_return * 100).toFixed(1)}%</span></div>
                <div className="flex justify-between"><span>Volatility</span><span className="text-white">{(benchPortfolio.volatility * 100).toFixed(1)}%</span></div>
                <div className="flex justify-between"><span>Sharpe</span><span className="text-white">{benchPortfolio.sharpe_ratio?.toFixed(3)}</span></div>
                <div className="flex justify-between"><span>Max Drawdown</span><span className="text-white">{(benchPortfolio.max_drawdown * 100).toFixed(1)}%</span></div>
              </div>
            </div>
            <div>
              <h4 className="text-xs text-gray-500 uppercase mb-2">{benchmark.benchmark_display || 'Benchmark'}</h4>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between"><span>Total Return</span><span className="text-white">{(benchIndex.total_return * 100).toFixed(1)}%</span></div>
                <div className="flex justify-between"><span>Annualized</span><span className="text-white">{(benchIndex.annualized_return * 100).toFixed(1)}%</span></div>
                <div className="flex justify-between"><span>Volatility</span><span className="text-white">{(benchIndex.volatility * 100).toFixed(1)}%</span></div>
                <div className="flex justify-between"><span>Max Drawdown</span><span className="text-white">{(benchIndex.max_drawdown * 100).toFixed(1)}%</span></div>
              </div>
            </div>
          </div>
        </div>

        {/* Attribution */}
        <div className="col-span-6 bg-[#11131a]/80 border border-gray-800/50 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Return Attribution</h3>
          <p className="text-xs text-gray-500 mb-4">
            Period: {attribution.period?.start || 'N/A'} → {attribution.period?.end || 'N/A'}
            {' '}· Portfolio Return: <span className="text-white font-bold">{(attribution.portfolio_total_return * 100).toFixed(1)}%</span>
          </p>
          <div className="space-y-4">
            <AttributionTable
              title="Security Contribution"
              items={secContrib}
              valueKey="ticker"
              contribKey="contribution"
              weightKey="weight"
              returnKey="return"
            />
            <AttributionTable
              title="Sector Contribution"
              items={sectorContrib}
              valueKey="category"
              contribKey="contribution"
              weightKey="weight"
              returnKey="return"
            />
          </div>
        </div>
      </div>
    );
  }

  function renderRecommendations() {
    try {
      const list = Array.isArray(recommendations) ? recommendations : [];
      const dismissed = Array.isArray(dismissedRecommendations) ? dismissedRecommendations : [];
      const activeRecs = list.filter((rec) => rec && (rec.id || rec.action || rec.description) && !dismissed.includes(rec.id));

      return (
        <div className="space-y-4">
          <div className="rounded-2xl border border-indigo-800/50 bg-[#11131a]/80 p-5 space-y-3">
            <h3 className="text-lg font-semibold text-white">Allocation using market conditions</h3>
            {data.regime_allocation?.status === 'ready' ? (
              <>
                <p className="text-sm text-gray-400">{data.regime_allocation.explanation}</p>
                {data.regime_allocation.convergence?.converged === false && (
                  <p role="status" className="rounded-lg border border-amber-700/60 bg-amber-950/30 px-3 py-2 text-sm text-amber-200">
                    The HMM reached its {data.regime_allocation.convergence.iterations}-iteration limit before meeting the likelihood tolerance. Treat these state probabilities and weights as less reliable estimates.
                  </p>
                )}
                {data.regime_allocation.states?.some((state) => state.covariance_fallback) && (
                  <p role="status" className="rounded-lg border border-amber-700/60 bg-amber-950/30 px-3 py-2 text-sm text-amber-200">
                    At least one market state had too little training data to estimate its own covariance. Its risk estimate falls back to the overall history, so this allocation is less state-specific.
                  </p>
                )}
                <p className="text-xs text-gray-500">Trained on {data.regime_allocation.observations} daily returns: {data.regime_allocation.training_start} to {data.regime_allocation.training_end}. State probabilities look two trading sessions ahead.</p>
                <div className="flex flex-wrap gap-3">
                  {data.regime_allocation.states.map((state) => <span key={state.label} className="rounded-lg bg-indigo-500/10 px-3 py-2 text-sm text-indigo-300">{state.label}: {(state.probability * 100).toFixed(1)}%</span>)}
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-gray-300">
                    <thead><tr><th className="text-left py-2">Stock</th><th className="text-right">Current</th><th className="text-right">Without regimes</th><th className="text-right">With regimes</th></tr></thead>
                    <tbody>{data.tickers.map((ticker, index) => <tr key={ticker}><td className="py-2">{ticker}</td><td className="text-right">{(data.weights[index] * 100).toFixed(1)}%</td><td className="text-right">{(data.regime_allocation.baseline_weights[ticker] * 100).toFixed(1)}%</td><td className="text-right">{(data.regime_allocation.weights[ticker] * 100).toFixed(1)}%</td></tr>)}</tbody>
                  </table>
                </div>
                <p className="text-xs text-gray-500">Experimental comparison. Neither allocation has a guaranteed performance advantage.</p>
              </>
            ) : <p className="text-sm text-gray-400">{data.regime_allocation?.reason || 'Refresh the analysis to calculate market-condition allocations.'}</p>}
          </div>
          {data.ai_black_litterman_allocation && (
            <div className="glass-card rounded-xl p-6 space-y-3">
              <h3 className="text-lg font-semibold text-white">AI Black–Litterman allocation</h3>
              <p className="text-sm text-gray-400">MarketMind + FinBERT · maximum position {(data.ai_black_litterman_allocation.max_weight_cap * 100).toFixed(1)}% · {data.ai_black_litterman_allocation.horizon_modifier?.replaceAll('_', ' ')}</p>
              {data.ai_black_litterman_allocation.signal_status === 'prior_only' && <p className="text-sm text-amber-400">AI signals unavailable. Uses the equilibrium prior without an AI tilt.</p>}
              {data.ai_black_litterman_allocation.success ? (
                <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr><th className="text-left">Stock</th><th>Current</th><th>Prior</th><th>AI target</th><th>Signal sources</th></tr></thead>
                  <tbody>{data.tickers.map((ticker, index) => {
                    const ai = data.ai_black_litterman_allocation;
                    const view = ai.provenance[ticker];
                    return <tr key={ticker}><td className="py-2">{ticker}</td><td className="text-center">{(data.weights[index] * 100).toFixed(1)}%</td><td className="text-center">{(ai.prior_weights[ticker] * 100).toFixed(1)}%</td><td className="text-center">{(ai.weights[ticker] * 100).toFixed(1)}%</td><td className="text-center">{view.fallback_to_prior ? 'Prior only' : [view.marketmind_net_prob != null && 'MarketMind', view.finbert_score != null && 'FinBERT'].filter(Boolean).join(' + ')}</td></tr>;
                  })}</tbody></table></div>
              ) : <p role="status">{data.ai_black_litterman_allocation.reason}</p>}
              <p className="text-xs text-gray-400">Equal-weight equilibrium prior. Historical estimates; AI view confidence is heuristic, not calibrated accuracy. Missing news is not neutral sentiment.</p>
            </div>
          )}
          {data.allocation?.weights && (
            <div className="rounded-2xl border border-gray-800 bg-[#11131a]/80 p-5 space-y-3">
              <h3 className="text-lg font-semibold text-white">Minimum-volatility allocation</h3>
              <p className="text-sm text-gray-400">{data.allocation.explanation}</p>
              <table className="w-full text-sm text-gray-300">
                <thead><tr><th className="text-left py-2">Stock</th><th className="text-right">Current weight</th><th className="text-right">Suggested weight</th></tr></thead>
                <tbody>{data.tickers.map((ticker, index) => (
                  <tr key={ticker}><td className="py-2">{ticker}</td><td className="text-right">{(data.weights[index] * 100).toFixed(1)}%</td><td className="text-right">{(data.allocation.weights[ticker] * 100).toFixed(1)}%</td></tr>
                ))}</tbody>
              </table>
              <p className="text-sm text-gray-400">Historical annualized volatility: {(data.allocation.current_performance.volatility * 100).toFixed(1)}% current; {(data.allocation.performance.volatility * 100).toFixed(1)}% suggested.</p>
            </div>
          )}
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-lg font-semibold text-white">Portfolio Improvements</h3>
            <span className="text-xs text-gray-400 font-mono">{activeRecs.length} improvements available</span>
          </div>
          {activeRecs.length > 0 ? (
            <div className="space-y-3">
              {activeRecs.map((rec, idx) => (
                <RecommendationCard
                  key={rec?.id || idx}
                  rec={rec}
                  onDismiss={() => rec?.id && setDismissedRecommendations((current) => [...current, rec.id])}
                />
              ))}
            </div>
          ) : data.stages?.recommendations?.status === 'UNAVAILABLE' || data.stages?.recommendations?.status === 'FAILED' ? (
            <div className="bg-[#11131a]/80 border border-gray-800/50 rounded-2xl p-8 text-center">
              <Brain className="w-10 h-10 text-amber-500/50 mx-auto mb-3" />
              <p className="text-gray-300 font-medium">Recommendations currently unavailable.</p>
              <p className="text-xs text-gray-500 mt-1">{data.stages.recommendations.reason || 'Check model signals and market data coverage.'}</p>
            </div>
          ) : (
            <div className="bg-[#11131a]/80 border border-gray-800/50 rounded-2xl p-8 text-center">
              <Brain className="w-10 h-10 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-300 font-medium">No immediate recommendations requiring review.</p>
              <p className="text-xs text-gray-500 mt-1">No risk concentration or rebalancing thresholds were triggered for this portfolio.</p>
            </div>
          )}
        </div>
      );
    } catch (err) {
      return (
        <div className="bg-[#11131a]/80 border border-amber-500/30 rounded-2xl p-6 text-center text-amber-300 text-sm">
          Unable to render recommendations. {String(err?.message || err)}
        </div>
      );
    }
  }
};

// ── Sub-components ───────────────────────────────────────────

const ActionCenter = ({ recommendations, totalCount, onReviewAll, onDismiss }) => (
<section className="rounded-[28px] border border-indigo-500/20 bg-gradient-to-br from-indigo-500/10 via-slate-900/80 to-slate-950/80 p-5 shadow-xl shadow-indigo-950/20">
  <div className="mb-4 flex items-center justify-between gap-4">
      <div>
      <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-indigo-300">Action center</p>
      <h2 className="mt-1 text-lg font-bold text-white">What deserves your attention?</h2>
      <p className="mt-1 text-xs text-slate-400">Evidence-backed insights from your portfolio analysis.</p>
      </div>
    <button type="button" onClick={onReviewAll} className="text-xs font-bold text-indigo-200 transition hover:text-white">
      Review all {totalCount > 0 ? `(${totalCount})` : ''} <ChevronRight className="inline h-3.5 w-3.5" />
      </button>
    </div>
    {Array.isArray(recommendations) && recommendations.length === 0 ? (
    <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4">
        <p className="text-sm font-semibold text-emerald-300">No immediate actions identified.</p>
      <p className="mt-1 text-xs text-slate-400">Your current analysis has no recommendations requiring review.</p>
      </div>
    ) : (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {Array.isArray(recommendations) ? recommendations.map((rec, i) => (
        <div key={rec?.id || i} className="flex flex-col rounded-2xl border border-white/10 bg-slate-900/60 p-4">
            <div className="flex items-start justify-between gap-2">
            <p className="text-xs font-bold uppercase text-slate-300">{String(rec?.action || 'Review').replace(/_/g, ' ')} <span className="normal-case text-white">{String(rec?.asset || '')}</span></p>
            <span className="shrink-0 rounded-full bg-amber-500/10 px-2 py-1 text-[10px] font-bold uppercase text-amber-300">{String(rec?.confidence || 'review')}</span>
            </div>
          <p className="mt-3 flex-1 text-sm text-slate-300">{String(rec?.reason || rec?.description || 'Review this portfolio insight.')}</p>
          {rec?.expected_impact && <p className="mt-3 text-[11px] text-slate-400">Potential impact: {String(rec.expected_impact)}</p>}
          <div className="mt-4 flex gap-2">
            <button type="button" onClick={onReviewAll} className="rounded-lg bg-indigo-600/20 px-3 py-1.5 text-xs text-indigo-200 transition hover:bg-indigo-600/30">Review</button>
            <button type="button" onClick={() => rec?.id && onDismiss(rec.id)} className="rounded-lg bg-white/5 px-3 py-1.5 text-xs text-slate-300 transition hover:text-white">Dismiss</button>
            </div>
          </div>
        )) : (
          <></>
        )}
      </div>
    )}
  </section>
);

const StatCard = ({ label, value, subtitle, icon }) => (
<div className="rounded-[24px] border border-white/10 bg-gradient-to-br from-slate-900/90 to-slate-950/80 p-4 shadow-xl shadow-slate-950/20">
  <div className="mb-3 flex items-center gap-2">
    {icon && <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-800/80">{icon}</div>}
    <span className="text-xs font-medium text-slate-400">{label}</span>
    </div>
  <div className="text-2xl font-black tracking-tight text-white">{value}</div>
  <p className="mt-1 text-[10px] text-slate-400">{subtitle}</p>
  </div>
);

const AttributionTable = ({ title, items, valueKey }) => (
  <div>
    <h4 className="text-xs text-gray-500 uppercase mb-2">{title}</h4>
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-gray-800/50">
            <th className="text-left py-1.5 text-gray-500">{valueKey === 'ticker' ? 'Ticker' : 'Sector'}</th>
            <th className="text-right py-1.5 text-gray-500">%</th>
            <th className="text-right py-1.5 text-gray-500">Return</th>
            <th className="text-right py-1.5 text-gray-500">Contrib</th>
            <th className="text-right py-1.5 text-gray-500">% of Total</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={item[valueKey] || i} className="border-b border-gray-800/30">
              <td className="py-1.5 text-gray-300">{item[valueKey] || item.ticker || item.category}</td>
              <td className="py-1.5 text-right text-gray-400">{(item.weight * 100).toFixed(1)}%</td>
              <td className="py-1.5 text-right text-gray-400">{(item.return * 100).toFixed(1)}%</td>
              <td className="py-1.5 text-right text-gray-400">{item.contribution.toFixed(4)}</td>
              <td className="py-1.5 text-right font-bold text-white">{item.contribution_pct.toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

const CorrelationMatrix = ({ data }) => {
  const tickers = data.tickers || [];
  const matrix = data.matrix || [];
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>{tickers.map((t) => <th key={t} className="text-center py-1.5 text-gray-500">{t}</th>)}</tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={tickers[i] || i}>
              <th className="text-left py-1.5 text-gray-400">{tickers[i] || '?'}</th>
              {row.map((val, j) => (
                <td
                  key={j}
                  className="text-center py-1.5 font-medium"
                  style={{
                    color: val > 0.7 ? '#ef4444' : val > 0.3 ? '#f59e0b' : val > -0.3 ? '#9ca3af' : val > -0.7 ? '#3b82f6' : '#10b981',
                  }}
                >{val.toFixed(2)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const RecommendationCard = ({ rec, onDismiss }) => {
  if (!rec) return null;

  const formatMetricVal = (val) => {
    try {
      if (val == null) return 'N/A';
      if (typeof val === 'number') {
        return Number.isInteger(val) ? val.toString() : val.toFixed(Math.abs(val) >= 1 ? 2 : 4);
      }
      if (Array.isArray(val)) {
        return val.map((item) => (typeof item === 'object' && item !== null ? JSON.stringify(item) : String(item))).join(', ');
      }
      if (typeof val === 'object') {
        return Object.entries(val).map(([k, v]) => `${k}: ${typeof v === 'number' ? v.toFixed(2) : String(v ?? 'N/A')}`).join(' | ');
      }
      return String(val);
    } catch {
      return String(val ?? 'N/A');
    }
  };

  const severityColors = {
    high: 'border-rose-500 bg-rose-500/5',
    medium: 'border-amber-500 bg-amber-500/5',
    low: 'border-blue-500 bg-blue-500/5',
    experimental: 'border-purple-500 bg-purple-500/5',
  };
  const confidenceStr = String(rec.confidence || 'medium').toLowerCase();
  const colorClass = severityColors[confidenceStr] || 'border-gray-500 bg-gray-500/5';
  return (
    <div className={`border-l-2 rounded-xl p-4 ${colorClass}`}>
      <div className="flex justify-between items-start mb-2">
        <div>
          <span className="text-xs font-bold uppercase text-gray-500">{String(rec.action || 'Review').replace(/_/g, ' ')}</span>
          <span className="text-sm font-bold text-white"> {String(rec.asset || '')}</span>
        </div>
        <span className={`text-[10px] uppercase font-bold px-2 py-1 rounded ${
          confidenceStr === 'high' ? 'text-rose-300 bg-rose-500/10' :
          confidenceStr === 'medium' ? 'text-amber-300 bg-amber-500/10' :
          'text-blue-300 bg-blue-500/10'
        }`}>{confidenceStr}</span>
      </div>
      <p className="text-sm text-gray-300 mb-2">{String(rec.reason || rec.description || '')}</p>
      {rec.supporting_metrics && typeof rec.supporting_metrics === 'object' && !Array.isArray(rec.supporting_metrics) && Object.keys(rec.supporting_metrics).length > 0 && (
        <div className="text-xs text-gray-500 mb-2">
          <span className="font-medium text-gray-400">Metrics:</span>
          {Object.entries(rec.supporting_metrics).map(([k, v]) => (
            <span key={k} className="ml-2">{k}: {formatMetricVal(v)}</span>
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 mt-2">
        <button className="text-xs px-3 py-1.5 bg-gray-800/50 text-gray-300 rounded-lg hover:bg-gray-700/50 transition-colors">
          Review
        </button>
        <button className="text-xs px-3 py-1.5 bg-indigo-600/20 text-indigo-300 rounded-lg hover:bg-indigo-600/30 transition-colors">
          Simulate
        </button>
        {onDismiss && <button type="button" onClick={onDismiss} className="text-xs px-3 py-1.5 bg-gray-800/50 text-gray-400 rounded-lg hover:text-white transition-colors">Dismiss</button>}
        <span className="text-[10px] text-gray-600">
          Models: {Array.isArray(rec.supporting_models) ? rec.supporting_models.join(', ') : 'N/A'}
        </span>
      </div>
    </div>
  );
};

function performanceColor(value) {
  if (value == null || !Number.isFinite(value)) return '#eef1f5';
  if (value >= 0) return value > 15 ? '#49d3a5' : value > 5 ? '#a6ead2' : '#ebfaf4';
  return value < -15 ? '#cc1749' : value < -5 ? '#f9a9b8' : '#fff0f2';
}
function AllocationTile({x, y, width, height, name, weight, performance}) {
  if (!width || !height || !name) return null;
  const label = performance == null ? 'Unavailable' : `${performance >= 0 ? '+' : ''}${performance.toFixed(1)}%`;
  return <g><rect x={x + 2} y={y + 2} width={Math.max(0,width - 4)} height={Math.max(0,height - 4)} rx={3} fill={performanceColor(performance)} stroke="#dce5e2" />
    <title>{name} · {(weight * 100).toFixed(1)}% weight · {label} unrealized return</title>
    {width > 65 && height > 45 && <text x={x + width/2} y={y + height/2} textAnchor="middle" fill={performance != null && performance < -15 ? "#ffffff" : "#15191d"} fontSize={16} fontWeight={600}>{name}<tspan x={x + width/2} dy={23} fill={performance != null && performance < -15 ? "#ffffff" : "#555f60"} fontSize={13}>{label}</tspan></text>}
  </g>;
}
function AllocationTooltip({active,payload}) {
  const row = payload?.[0]?.payload;
  if (!active || !row?.ticker) return null;
  return <div className="allocation-tooltip"><strong>{row.ticker}</strong>
    <p><span>Portfolio weight</span><b>{(row.weight * 100).toFixed(1)}%</b></p>
    <p><span>Market value</span><b>{formatMoney(row.market,row.currency)}</b></p>
    <p><span>Unrealized return</span><b style={{color:row.performance == null ? '#626a73' : row.performance >= 0 ? '#008553' : '#c51746'}}>{row.performance == null ? 'Unavailable' : `${row.performance >= 0 ? '+' : ''}${row.performance.toFixed(1)}%`}</b></p>
  </div>;
}

export function AllocationComparison({ data }) {
  const allocation = data.personalized_allocation;
  const rows = data.tickers.map((ticker, index) => ({
    ticker, current: data.weights[index], target: allocation.weights[ticker],
    change: allocation.weights[ticker] - data.weights[index],
  })).sort((a, b) => Math.abs(b.change) - Math.abs(a.change));
  const top = rows[0];
  const aiView = allocation.objective_used === 'black_litterman' && data.ai_black_litterman_allocation?.provenance?.[top?.ticker];
  const pct = weight => (weight * 100).toFixed(1) + '%';
  return <>
    <table className="w-full text-sm"><thead><tr><th className="text-left">Holding</th><th>Current</th><th>Suggested</th><th>Change (pp)</th></tr></thead>
      <tbody>{rows.map(r => <tr className="border-t text-center" key={r.ticker}><td className="py-2 text-left">{r.ticker}</td><td>{pct(r.current)}</td><td>{pct(r.target)}</td><td>{(100 * r.change).toFixed(1)}</td></tr>)}</tbody>
    </table>
    <details><summary className="cursor-pointer font-semibold">Explain this allocation</summary>
      {top && <p className="mt-3">{Math.abs(top.change) < 0.0005 ? 'Current weights already match the suggested allocation at the precision shown.' : `The largest adjustment is ${top.ticker}, from ${pct(top.current)} to ${pct(top.target)}.`}</p>}
      <p>The optimizer used {allocation.objective_used.replaceAll('_', ' ')} with a {pct(allocation.max_weight_cap)} position cap. Horizon rule: {allocation.horizon_modifier?.replaceAll('_', ' ') || 'baseline'}.</p>
      {aiView && <p>{top.ticker} view: MarketMind net probability {aiView.marketmind_net_prob == null ? 'unavailable' : pct(aiView.marketmind_net_prob)}. FinBERT sentiment {aiView.finbert_score == null ? 'unavailable' : aiView.finbert_score.toFixed(2)}. {aiView.fallback_to_prior && 'The model used the equilibrium prior.'}</p>}
      <p className="mt-2 text-sm">Suggested weights are estimates before execution costs.</p>
    </details>
  </>;
}

export default PortfolioDashboard;
