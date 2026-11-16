import React, { useState, useEffect, useContext, useMemo } from 'react';
import { 
  Target, Plus, Trash2, AlertCircle, TrendingUp, DollarSign, 
  Calendar, ShieldCheck, ArrowRight, Loader2, RefreshCw, Sparkles, CheckCircle2
} from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer, ReferenceLine 
} from 'recharts';
import { PortfolioContext } from '../contexts/PortfolioContext';
import { PortfolioService } from '../services/api';
import { formatMoney } from '../services/portfolioValuation';

const initialForm = {
  name: '',
  targetAmount: '',
  currentAmount: '',
  monthlyContribution: '',
  targetDate: '',
  currency: 'INR'
};

export default function GoalsView({ workspace, setWorkspace }) {
  const portfolioContext = useContext(PortfolioContext);
  const snapshot = portfolioContext?.snapshot;
  const valued = snapshot?.valuation;
  const activeCurrency = valued?.currencies?.[0] || 'INR';
  const group = valued?.groups?.[activeCurrency];
  const portfolioValue = group?.market || group?.cost || 0;

  const goals = workspace?.goals || [];
  const [selectedGoalId, setSelectedGoalId] = useState(goals[0]?.id || null);
  const [form, setForm] = useState({ ...initialForm, currency: activeCurrency });
  const [isFormOpen, setIsFormOpen] = useState(goals.length === 0);
  const [formError, setFormError] = useState('');

  // Simulation state
  const [simulation, setSimulation] = useState(null);
  const [simLoading, setSimLoading] = useState(false);
  const [simError, setSimError] = useState('');

  const selectedGoal = goals.find((g) => g.id === selectedGoalId) || goals[0] || null;

  // Sync selected goal id if deleted
  useEffect(() => {
    if (!selectedGoalId && goals.length > 0) {
      setSelectedGoalId(goals[0].id);
    }
  }, [goals, selectedGoalId]);

  // Derived tickers and weights for simulation
  const { tickers, weights } = useMemo(() => {
    if (group?.tickers?.length > 0) {
      const t = group.tickers;
      const w = group.weights?.length === t.length ? group.weights : Array(t.length).fill(1 / t.length);
      return { tickers: t, weights: w };
    }
    // Default diversified baseline
    if (activeCurrency === 'INR') {
      return {
        tickers: ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS'],
        weights: [0.2, 0.2, 0.2, 0.2, 0.2],
      };
    }
    return {
      tickers: ['SPY', 'QQQ', 'GLD', 'TLT'],
      weights: [0.4, 0.3, 0.15, 0.15],
    };
  }, [group, activeCurrency]);

  // Run Monte Carlo simulation for selected goal
  const runSimulation = async (goal) => {
    if (!goal) return;
    try {
      setSimLoading(true);
      setSimError('');

      const targetDate = goal.target_date ? new Date(goal.target_date) : null;
      let years = 5.0;
      if (targetDate && !isNaN(targetDate.getTime())) {
        const diffMs = targetDate.getTime() - Date.now();
        years = Math.max(0.5, parseFloat((diffMs / (1000 * 60 * 60 * 24 * 365.25)).toFixed(1)));
      }

      const payload = {
        tickers,
        weights,
        current_capital: Number(goal.current_amount ?? goal.currentAmount ?? 0),
        monthly_contribution: Number(goal.monthly_contribution ?? goal.monthlyContribution ?? 0),
        target_amount: Number(goal.target_amount ?? goal.targetAmount ?? 10000),
        time_horizon_years: years,
        num_sims: 1000,
      };

      let result;
      if (typeof PortfolioService?.analyzeGoal === 'function') {
        result = await PortfolioService.analyzeGoal(payload);
      } else {
        const resp = await fetch('http://localhost:8000/portfolio/goal', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        result = await resp.json();
      }
      setSimulation(result);
    } catch (err) {
      console.error('Goal simulation failed:', err);
      setSimError(err?.response?.data?.detail || err?.message || 'Monte Carlo simulation failed');
    } finally {
      setSimLoading(false);
    }
  };

  // Run simulation when selected goal changes
  useEffect(() => {
    if (selectedGoal) {
      runSimulation(selectedGoal);
    } else {
      setSimulation(null);
    }
  }, [selectedGoalId]);

  const updateForm = (e) => setForm((c) => ({ ...c, [e.target.name]: e.target.value }));

  const addGoal = (e) => {
    e.preventDefault();
    const target = Number(form.targetAmount);
    const current = Number(form.currentAmount || 0);
    const monthly = Number(form.monthlyContribution || 0);

    if (!form.name.trim() || !Number.isFinite(target) || target <= 0) {
      setFormError('Please enter a valid goal name and positive target amount.');
      return;
    }

    const newGoal = {
      id: `goal_${Date.now()}`,
      name: form.name.trim(),
      target_amount: target,
      current_amount: current,
      monthly_contribution: monthly,
      target_date: form.targetDate || null,
      currency: form.currency || activeCurrency,
      created_at: new Date().toISOString(),
    };

    const nextGoals = [...goals, newGoal];
    setWorkspace({ ...workspace, goals: nextGoals });
    setSelectedGoalId(newGoal.id);
    setForm({ ...initialForm, currency: activeCurrency });
    setIsFormOpen(false);
    setFormError('');
  };

  const removeGoal = (id) => {
    const nextGoals = goals.filter((g) => g.id !== id);
    setWorkspace({ ...workspace, goals: nextGoals });
    if (selectedGoalId === id) {
      setSelectedGoalId(nextGoals[0]?.id || null);
    }
  };

  // Normalized simulation data across flat and nested schemas
  const normSim = useMemo(() => {
    if (!simulation) return null;
    const analysis = simulation.analysis || {};
    const dist = simulation.distribution || {};
    const traj = simulation.trajectories || simulation.trajectory || {};

    const rawProb = simulation.success_probability_pct ?? analysis.probability_of_success_pct;
    const successProb = rawProb != null ? Math.round(Number(rawProb)) : null;

    const medianFinal = simulation.expected_final_value ?? dist.median_final ?? dist.mean_final ?? null;
    const reqMonthly = simulation.required_monthly_contribution ?? analysis.required_monthly_contribution ?? null;
    const addMonthly = simulation.additional_monthly_needed ?? analysis.additional_monthly_needed ?? (reqMonthly != null ? Math.max(0, reqMonthly - Number(selectedGoal?.monthly_contribution || 0)) : 0);

    const rawReqCagr = simulation.required_cagr_pct ?? (analysis.required_return_cagr != null ? analysis.required_return_cagr * 100 : null);
    const reqCagr = rawReqCagr != null ? Number(rawReqCagr).toFixed(1) : null;

    const rawExpCagr = simulation.expected_cagr_pct ?? (analysis.expected_annual_return != null ? analysis.expected_annual_return * 100 : null);
    const expCagr = rawExpCagr != null ? Number(rawExpCagr).toFixed(1) : null;

    return {
      successProb,
      medianFinal,
      reqMonthly,
      addMonthly,
      reqCagr,
      expCagr,
      trajectory: {
        p10: traj.p10 || [],
        p50: traj.p50 || [],
        p90: traj.p90 || [],
      }
    };
  }, [simulation, selectedGoal]);

  // Trajectory chart data transformation
  const chartData = useMemo(() => {
    const p50 = normSim?.trajectory?.p50;
    if (!p50 || !p50.length) return [];
    const p10 = normSim.trajectory.p10 || [];
    const p90 = normSim.trajectory.p90 || [];
    const n = p50.length;
    const step = Math.max(1, Math.floor(n / 30));

    const points = [];
    for (let i = 0; i < n; i += step) {
      const year = (i / 12).toFixed(1);
      points.push({
        month: i,
        label: i === 0 ? 'Today' : `Yr ${year}`,
        p10: Math.round(p10[i] || 0),
        p50: Math.round(p50[i] || 0),
        p90: Math.round(p90[i] || 0),
        target: selectedGoal ? Number(selectedGoal.target_amount) : 0,
      });
    }
    // ensure final month is included
    if (n > 0 && points[points.length - 1].month !== n - 1) {
      points.push({
        month: n - 1,
        label: `Yr ${((n - 1) / 12).toFixed(1)}`,
        p10: Math.round(p10[n - 1] || 0),
        p50: Math.round(p50[n - 1] || 0),
        p90: Math.round(p90[n - 1] || 0),
        target: selectedGoal ? Number(selectedGoal.target_amount) : 0,
      });
    }
    return points;
  }, [normSim, selectedGoal]);

  const prob = normSim?.successProb ?? null;
  const isHealthy = prob != null && prob >= 70;
  const isModerate = prob != null && prob >= 50 && prob < 70;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-[#11131a]/90 border border-gray-800 rounded-2xl p-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Target className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              Financial Goals & Monte Carlo Engine
            </h1>
            <p className="text-xs text-gray-400">
              Forward-looking stochastic wealth simulation using historical correlation and geometric Brownian motion.
            </p>
          </div>
        </div>

        <button
          onClick={() => setIsFormOpen(!isFormOpen)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition-all shadow-md shadow-indigo-600/20 active:scale-95"
        >
          <Plus className="w-4 h-4" />
          <span>{isFormOpen ? 'Close Goal Creator' : 'Create New Goal'}</span>
        </button>
      </div>

      {/* Goal Creator Form (Collapsible) */}
      {isFormOpen && (
        <form onSubmit={addGoal} className="bg-[#11131a]/90 border border-gray-800 rounded-2xl p-6 space-y-4">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            Set Up a Goal Milestone
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="lg:col-span-2">
              <label className="text-xs text-gray-400 font-medium block mb-1">Goal Name</label>
              <input
                name="name"
                value={form.name}
                onChange={updateForm}
                placeholder="e.g. Retirement 2035, Home Downpayment"
                className="w-full bg-[#161822] border border-gray-700/80 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-xs text-gray-400 font-medium block mb-1">Target Amount ({form.currency})</label>
              <input
                name="targetAmount"
                type="number"
                min="0"
                step="any"
                value={form.targetAmount}
                onChange={updateForm}
                placeholder="5000000"
                className="w-full bg-[#161822] border border-gray-700/80 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs text-gray-400 font-medium">Initial Savings</label>
                {portfolioValue > 0 && (
                  <button
                    type="button"
                    onClick={() => setForm((c) => ({ ...c, currentAmount: portfolioValue }))}
                    className="text-[10px] text-indigo-400 hover:underline"
                  >
                    Use Portfolio
                  </button>
                )}
              </div>
              <input
                name="currentAmount"
                type="number"
                min="0"
                step="any"
                value={form.currentAmount}
                onChange={updateForm}
                placeholder="100000"
                className="w-full bg-[#161822] border border-gray-700/80 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-xs text-gray-400 font-medium block mb-1">Monthly Contribution</label>
              <input
                name="monthlyContribution"
                type="number"
                min="0"
                step="any"
                value={form.monthlyContribution}
                onChange={updateForm}
                placeholder="25000"
                className="w-full bg-[#161822] border border-gray-700/80 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-xs text-gray-400 font-medium block mb-1">Target Date</label>
              <input
                name="targetDate"
                type="date"
                value={form.targetDate}
                onChange={updateForm}
                className="w-full bg-[#161822] border border-gray-700/80 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {formError && (
            <div className="flex items-center gap-2 text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 p-2.5 rounded-xl">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setIsFormOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-medium text-gray-400 hover:text-white transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-indigo-600/20 transition-all"
            >
              Save & Simulate Goal
            </button>
          </div>
        </form>
      )}

      {/* Main Grid: Goals Selector + Active Goal Simulation */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left Column: Goals List */}
        <div className="col-span-12 lg:col-span-4 space-y-3">
          <div className="text-xs font-bold uppercase tracking-wider text-gray-400 px-1">
            Active Goal Milestones ({goals.length})
          </div>

          {goals.length === 0 ? (
            <div className="bg-[#11131a]/80 border border-gray-800 rounded-2xl p-8 text-center text-gray-400 text-xs">
              <Target className="w-8 h-8 text-gray-600 mx-auto mb-2" />
              <p className="font-medium text-white mb-1">No financial goals set yet</p>
              <p className="mb-4">Create your first milestone above to start Monte Carlo projections.</p>
              <button
                onClick={() => setIsFormOpen(true)}
                className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-semibold"
              >
                Create Goal
              </button>
            </div>
          ) : (
            goals.map((goal) => {
              const isSelected = goal.id === selectedGoalId;
              const target = Number(goal.target_amount);
              const current = Number(goal.current_amount || 0);
              const fundedPct = target > 0 ? Math.min(100, Math.round((current / target) * 100)) : 0;

              return (
                <div
                  key={goal.id}
                  onClick={() => setSelectedGoalId(goal.id)}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer relative ${
                    isSelected
                      ? 'bg-[#161822] border-indigo-500 shadow-lg shadow-indigo-500/10'
                      : 'bg-[#11131a]/80 border-gray-800 hover:border-gray-700'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-bold text-white text-sm flex items-center gap-2">
                        {goal.name}
                        {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />}
                      </h3>
                      <div className="text-[11px] text-gray-400 mt-0.5 flex items-center gap-2">
                        <Calendar className="w-3 h-3 text-gray-500" />
                        <span>{goal.target_date ? `Target: ${goal.target_date}` : 'Open-ended horizon'}</span>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeGoal(goal.id);
                      }}
                      className="text-gray-500 hover:text-rose-400 p-1 rounded-lg transition-colors"
                      title="Delete Goal"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="mt-3 flex items-baseline justify-between text-xs">
                    <span className="text-gray-400">
                      Saved: {formatMoney(current, goal.currency || activeCurrency)}
                    </span>
                    <span className="font-bold text-white">
                      Target: {formatMoney(target, goal.currency || activeCurrency)}
                    </span>
                  </div>

                  <div className="w-full bg-gray-800 h-1.5 rounded-full mt-2 overflow-hidden">
                    <div
                      className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                      style={{ width: `${fundedPct}%` }}
                    />
                  </div>

                  <div className="mt-2 flex items-center justify-between text-[11px]">
                    <span className="text-gray-400">{fundedPct}% funded today</span>
                    <span className="text-indigo-400 font-medium flex items-center gap-1">
                      Simulate <ArrowRight className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Column: Monte Carlo Simulation & Analytics */}
        <div className="col-span-12 lg:col-span-8">
          {selectedGoal ? (
            <div className="bg-[#11131a]/80 border border-gray-800 rounded-2xl p-6 space-y-6">
              {/* Goal Title & Controls */}
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-800 pb-4">
                <div>
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-indigo-400">
                    <ShieldCheck className="w-4 h-4" />
                    Monte Carlo Probability Analysis
                  </div>
                  <h2 className="text-xl font-bold text-white mt-1">
                    {selectedGoal.name}
                  </h2>
                </div>

                <button
                  onClick={() => runSimulation(selectedGoal)}
                  disabled={simLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-[#161822] hover:bg-gray-800 border border-gray-700 text-gray-200 rounded-xl text-xs font-semibold transition-all disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${simLoading ? 'animate-spin' : ''}`} />
                  <span>Re-run Simulation (1,000 paths)</span>
                </button>
              </div>

              {simLoading ? (
                <div className="flex flex-col items-center justify-center h-72 gap-3">
                  <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                  <p className="text-xs text-gray-400">
                    Generating 1,000 correlated Cholesky return paths across your portfolio...
                  </p>
                </div>
              ) : simError ? (
                <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-300 text-xs">
                  {simError}
                </div>
              ) : simulation ? (
                <>
                  {/* KPI Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Probability Card */}
                    <div className="bg-[#161822] border border-gray-800/80 rounded-xl p-4">
                      <div className="text-xs text-gray-400 font-medium mb-1">Success Probability</div>
                      <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-black ${
                          isHealthy ? 'text-emerald-400' : isModerate ? 'text-amber-400' : 'text-rose-400'
                        }`}>
                          {prob != null ? `${prob}%` : '--'}
                        </span>
                        <span className="text-xs font-semibold text-gray-400">
                          {isHealthy ? 'High Confidence' : isModerate ? 'Fair Chance' : 'Shortfall Risk'}
                        </span>
                      </div>
                      <div className="w-full bg-gray-800 h-1.5 rounded-full mt-2.5 overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${
                            isHealthy ? 'bg-emerald-500' : isModerate ? 'bg-amber-500' : 'bg-rose-500'
                          }`}
                          style={{ width: `${Math.min(100, Math.max(5, prob ?? 0))}%` }}
                        />
                      </div>
                    </div>

                    {/* Projected Value Card */}
                    <div className="bg-[#161822] border border-gray-800/80 rounded-xl p-4">
                      <div className="text-xs text-gray-400 font-medium mb-1">Median Projected Wealth (P50)</div>
                      <div className="text-xl font-bold text-white tracking-tight">
                        {normSim?.medianFinal != null ? formatMoney(normSim.medianFinal, selectedGoal.currency || activeCurrency) : 'Calculating...'}
                      </div>
                      <div className="text-[11px] text-gray-400 mt-2 flex items-center justify-between">
                        <span>Target:</span>
                        <span className="font-semibold text-gray-300">
                          {formatMoney(Number(selectedGoal.target_amount), selectedGoal.currency || activeCurrency)}
                        </span>
                      </div>
                    </div>

                    {/* Recommendation Card */}
                    <div className="bg-[#161822] border border-gray-800/80 rounded-xl p-4">
                      <div className="text-xs text-gray-400 font-medium mb-1">Required Monthly Savings</div>
                      <div className="text-xl font-bold text-indigo-400">
                        {normSim?.reqMonthly != null ? formatMoney(normSim.reqMonthly, selectedGoal.currency || activeCurrency) : 'Calculating...'}
                        <span className="text-xs font-normal text-gray-400">/mo</span>
                      </div>
                      <div className="text-[11px] text-gray-400 mt-2">
                        CAGR Req: <span className="font-semibold text-white">{normSim?.reqCagr ?? '--'}%</span> vs Exp: <span className="font-semibold text-white">{normSim?.expCagr ?? '--'}%</span>
                      </div>
                    </div>
                  </div>

                  {/* Monte Carlo Trajectory Chart */}
                  <div className="bg-[#161822] border border-gray-800/80 rounded-xl p-5">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h3 className="text-sm font-bold text-white">Wealth Trajectory Distribution</h3>
                        <p className="text-[11px] text-gray-400">
                          P10 (Pessimistic), P50 (Median), and P90 (Optimistic) paths with target threshold
                        </p>
                      </div>
                      <div className="flex items-center gap-3 text-xs">
                        <span className="flex items-center gap-1 text-emerald-400">
                          <span className="w-2 h-2 rounded-full bg-emerald-500" /> P90 Bull
                        </span>
                        <span className="flex items-center gap-1 text-indigo-400">
                          <span className="w-2 h-2 rounded-full bg-indigo-500" /> P50 Median
                        </span>
                        <span className="flex items-center gap-1 text-rose-400">
                          <span className="w-2 h-2 rounded-full bg-rose-500" /> P10 Bear
                        </span>
                      </div>
                    </div>

                    <div className="h-64 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                          <defs>
                            <linearGradient id="gradP90" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                              <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                            </linearGradient>
                            <linearGradient id="gradP50" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                              <stop offset="95%" stopColor="#6366f1" stopOpacity={0.05} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#262b3d" />
                          <XAxis dataKey="label" stroke="#6b7280" fontSize={10} />
                          <YAxis 
                            stroke="#6b7280" 
                            fontSize={10}
                            tickFormatter={(v) => v >= 100000 ? `${(v / 100000).toFixed(0)}L` : `${(v / 1000).toFixed(0)}k`}
                          />
                          <Tooltip
                            contentStyle={{ backgroundColor: '#11131a', borderColor: '#374151', borderRadius: '0.75rem', fontSize: '11px' }}
                            formatter={(val) => [formatMoney(val, selectedGoal.currency || activeCurrency), '']}
                          />
                          <ReferenceLine 
                            y={Number(selectedGoal.target_amount)} 
                            stroke="#f59e0b" 
                            strokeDasharray="4 4" 
                            label={{ value: 'Target', fill: '#f59e0b', fontSize: 10, position: 'insideTopRight' }} 
                          />
                          <Area type="monotone" dataKey="p90" stroke="#10b981" strokeWidth={1.5} fill="url(#gradP90)" name="P90 (Bull)" />
                          <Area type="monotone" dataKey="p50" stroke="#6366f1" strokeWidth={2.5} fill="url(#gradP50)" name="P50 (Median)" />
                          <Area type="monotone" dataKey="p10" stroke="#ef4444" strokeWidth={1.5} fill="none" strokeDasharray="3 3" name="P10 (Bear)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Strategic Guidance Box */}
                  <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                    <div className="text-xs text-gray-300 leading-relaxed">
                      <strong>Portfolio Alignment:</strong> Simulation is conditioned on your current asset weights ({tickers.join(', ')}). 
                      {prob != null && prob < 75 ? (
                        <span> To increase certainty to 90%, consider allocating an additional {formatMoney(normSim?.addMonthly || 0, selectedGoal.currency || activeCurrency)} per month or rebalancing into higher Sharpe assets.</span>
                      ) : (
                        <span> Your current asset trajectory and contribution plan place you in a strong position to achieve this target milestone before the deadline.</span>
                      )}
                    </div>
                  </div>
                </>
              ) : null}
            </div>
          ) : (
            <div className="bg-[#11131a]/80 border border-gray-800 rounded-2xl p-12 text-center text-gray-400">
              Select or create a goal on the left to inspect Monte Carlo projections.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
