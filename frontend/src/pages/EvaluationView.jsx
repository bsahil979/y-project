import React, { useEffect, useState } from 'react';
import { getEvaluationSummary } from '../services/api';
const number = (v, percent = false) => Number.isFinite(v) ? `${(v * (percent ? 100 : 1)).toFixed(4)}${percent ? '%' : ''}` : 'Unavailable';
function Table({ headers, rows }) {
  return <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr>{headers.map(h => <th className="p-3 border-b" key={h}>{h}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={i}>{row.map((v, j) => <td className="p-3 border-b" key={j}>{v}</td>)}</tr>)}</tbody></table></div>;
}
function Card({ title, children }) { return <section className="rounded-2xl bg-white border border-slate-200 p-6 space-y-4"><h2 className="text-xl font-semibold">{title}</h2>{children}</section>; }
export default function EvaluationView() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => { let active = true; getEvaluationSummary().then(d => { if (active) setData(d); }).catch(() => { if (active) setError('Evaluation artifacts could not be loaded. Please retry later.'); }); return () => { active = false; }; }, []);
  if (error) return <p role="alert">{error}</p>;
  if (!data) return <p role="status">Loading saved model evaluations...</p>;
  return <EvaluationContent data={data} />;
}

export function EvaluationContent({ data }) {
  const { regime, personalized, marketmind, forecasting, integrity } = data;
  const bootstrap = regime.manifest.holdout.bootstrap;
  const study = personalized.holdout;
  return <main className="max-w-6xl mx-auto space-y-6 text-slate-700">
    <header><h1 className="text-3xl font-bold text-slate-950">2025 holdout results</h1><p className="mt-3">Saved evidence, current safeguards and remaining validation work. Research results are not guarantees of investment performance.</p></header>
    <Card title="Personalized and AI Black-Litterman allocations">
      <p>{personalized.scope}</p>
      {study.stale && <p role="alert" className="text-amber-800">Saved study is stale: its source or input hashes have changed.</p>}
      <p>{study.observations} holdout sessions; {study.horizon_years}-year horizon; {study.cost_bps} bps transaction costs. Historical sentiment: <strong>{study.sentiment_coverage}</strong>.</p>
      <Table headers={['Strategy', 'Net annual return', 'Volatility', 'Net Sharpe', 'Max drawdown', 'Mean rebalance turnover']} rows={study.metrics.map(r => [r.strategy, number(r.annualized_return, true), number(r.annualized_volatility, true), number(r.sharpe), number(r.max_drawdown, true), number(r.average_turnover, true)])} />
      <p>{study.risk_interpretation}</p>
      <details><summary>Turnover, uncertainty and risk comparisons</summary><p>{study.turnover_definition}</p>
      <Table headers={['Strategy', 'Baseline', 'Sharpe difference', 'Paired 95% interval']} rows={study.sharpe_intervals.map(r => [r.strategy, r.baseline, number(r.point_estimate), `[${number(r.lower)}, ${number(r.upper)}]`])} />
      <p>{study.bootstrap.replicates.toLocaleString()} paired bootstrap replicates with {study.bootstrap.block_sessions}-session blocks.</p>
      <h3 className="font-semibold">Does conservative allocation reduce realized risk?</h3>
      <Table headers={['Comparison', 'Risk metric', 'Difference', '95% interval', 'Interval supports reduction']} rows={study.risk_comparisons.map(r => [r.comparison, r.metric, number(r.difference, true), `[${number(r.lower, true)}, ${number(r.upper, true)}]`, r.interval_supports_reduction ? 'Yes, in this replay' : 'No'])} />
      <p>{study.limitations}</p></details>
      <details><summary>Implementation constraints and view provenance</summary><p className="mt-3">{personalized.constraint_scope}</p>
      <Table headers={['Profile', 'Horizon years', 'Cap', 'Standalone objective', 'Horizon rule']} rows={personalized.constraints.map(c => [c.applied_profile, c.investment_horizon_years, number(c.max_weight_cap, true), c.objective_used, c.horizon_modifier])} />
      <p>{personalized.objective_note}</p><p>{personalized.ai_views}</p><p>{personalized.confidence_note}</p><p>Per-ticker provenance: {personalized.provenance_fields.join(', ')}.</p></details>
    </Card>
    <details className="space-y-4"><summary className="cursor-pointer font-semibold">Model evaluations and safeguards</summary>
    <Card title="Regime allocation on the 2025 holdout">
      {(regime.stale || regime.status !== 'ready') && <p role="alert" className="text-amber-800">Artifact validation warning: {regime.status}; changed sources: {regime.changed_sources.join(', ') || 'none'}. Results describe the saved run.</p>}
      <p>{regime.convergence.converged}/{regime.convergence.fits} HMM fits converged. {regime.manifest.holdout.return_observations} daily observations; {regime.manifest.config.cost_bps} basis points per unit absolute traded weight.</p>
      <Table headers={['Strategy', 'Net Sharpe', 'Annual traded notional', 'Cumulative cost fraction']} rows={regime.holdout_metrics.map(r => [r.strategy, number(r.sharpe), number(r.annualized_traded_notional, true), number(r.cumulative_cost_fraction, true)])} />
      <p>HMM minus minimum-variance Sharpe: {number(bootstrap.point_estimate)}. Paired block bootstrap 95% interval [{number(bootstrap.lower)}, {number(bootstrap.upper)}], {bootstrap.block_length_sessions}-session blocks, {bootstrap.replicates_valid.toLocaleString()} replicates. The interval includes zero; superiority is not established.</p>
      <p>{regime.manifest.config.execution}. {regime.manifest.config.cost_definition}. No final liquidation.</p>
    </Card>
    <Card title="MarketMind classification holdout">
      <p>{marketmind.rows.toLocaleString()} predictions per classifier in archived Phase 2E.</p>
      <Table headers={['Model', 'Accuracy', 'Macro F1']} rows={[...Object.entries(marketmind.models).map(([k, v]) => [k, number(v.accuracy, true), number(v.macro_f1)]), ['Majority class baseline', number(marketmind.majority_baseline.accuracy, true), number(marketmind.majority_baseline.macro_f1)]]} />
      <p>{marketmind.regime_integration}</p>
    </Card>
    <Card title="Forecasting against the last-close baseline">
      <Table headers={['Experiment', 'Model error', 'Baseline error', 'Units']} rows={[
        ['MSFT direct-return LSTM test', number(forecasting.lstm.test_lstm_mae), number(forecasting.lstm.test_baseline_mae), 'Cumulative log-return percentage points'],
        ...Object.entries(forecasting.timesfm.summary).map(([k, v]) => [`TimesFM-2.5 replay ${k} (${v.origins} origins)`, number(v.model_mean_mae_pct_of_spot), number(v.baseline_mean_mae_pct_of_spot), 'MAE as percent of spot'])]} />
      <p>MSFT validation selected: {forecasting.lstm.model}. {forecasting.lstm.limitations}</p><p>{forecasting.timesfm.limitation}</p><p>{forecasting.interpretation}</p>
    </Card>
    <Card title="System integrity and guardrails"><p>{integrity.quarantined_rf_count} legacy RF evaluation records quarantined for in-sample overlap. Invalid accuracy is not exposed as live model confidence.</p><p>PPO: {integrity.ppo_status}. {integrity.ppo_preprocessing}</p><p>{integrity.advisor}</p></Card>
    </details>
    <details className="rounded-xl border p-4"><summary>Artifact provenance</summary>{data.sources.map(s => <p className="text-xs break-all mt-3" key={s.path}>{s.path}<br />SHA256 {s.sha256}</p>)}<p className="text-xs mt-3">HMM source hashes and snapshot verification are supplied in the evaluation API manifest.</p></details>
  </main>;
}
