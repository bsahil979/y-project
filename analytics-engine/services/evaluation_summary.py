"""Read-only, artifact-backed evaluation inventory. No training or market requests."""
import hashlib
import json
from services.research_delivery import ROOT, regime_study_results
from services.portfolio_optimizer import get_profile_constraints
from services.personalized_research import personalized_study_results


def evaluation_summary():
    sources = []

    def read(relative):
        raw = (ROOT / relative).read_bytes()
        sources.append({'path': relative, 'sha256': hashlib.sha256(raw).hexdigest()})
        return json.loads(raw)

    classification = read('models/phase_2e/phase_2e_classification_report.json')
    lstm = read('models/forecast_v2/MSFT/report.json')
    timesfm = read('evaluations/timesfm_replay_2026-11-04.json')
    holdout = personalized_study_results()
    aggregate = classification['aggregate']
    supports = [v['support'] for v in aggregate['A']['per_class'].values()]
    majority = max(supports) / sum(supports)
    quarantined = 0
    for path in sorted((ROOT / 'models').glob('*/metadata.json')):
        metadata = json.loads(path.read_text(encoding='utf-8'))
        rf = metadata.get('metrics', {}).get('rf', {})
        quarantined += rf.get('evaluation_status') == 'invalidated_in_sample_overlap'
    return {
        'schema_version': 1, 'read_only': True, 'sources': sources,
        'regime': regime_study_results(),
        'personalized': {
            'evaluation_status': holdout['evaluation_status'],
            'holdout': holdout,
            'scope': holdout['scope'],
            'constraints': [get_profile_constraints(p, years, n_assets=5)
                            for p in ('conservative', 'moderate', 'aggressive')
                            for years in (1, 5, 10)],
            'constraint_scope': 'Five-asset illustration; actual caps depend on asset count and feasibility.',
            'ai_views': 'Q = pi + 0.50 * annual volatility * signal. Signal = 0.65 * (P_buy - P_sell) + 0.35 * FinBERT when both exist; otherwise the available source. Missing both retains the prior. VADER is excluded.',
            'objective_note': 'Effective aggressive profiles use AI Black-Litterman in the pipeline; short horizons use maximum Sharpe. Standalone aggressive optimization without AI views uses target return.',
            'provenance_fields': ['marketmind_net_prob', 'finbert_score', 'composite_signal', 'implied_view_return_q', 'view_confidence', 'fallback_to_prior'],
            'confidence_note': 'View confidence is a policy coefficient, not calibrated prediction accuracy.'},
        'marketmind': {
            'evaluation_status': 'archived_holdout_before_causal_hmm_integration',
            'rows': aggregate['A']['rows'],
            'models': {k: {m: aggregate[k][m] for m in ('accuracy', 'macro_f1', 'balanced_accuracy')} for k in ('A', 'B')},
            'majority_baseline': {'accuracy': majority, 'macro_f1': (2 * majority / (1 + majority)) / 3},
            'regime_integration': 'Current features use causal HMM filtering with canonical states 0/1/2 and legacy shape compatibility. Archived Phase 2E scores do not evaluate this change; the Phase 8 allocation replay separately retrains the RF with causal HMM features on five stocks. It does not replace this archived classifier accuracy audit.'},
        'forecasting': {'lstm': lstm, 'timesfm': {k: timesfm[k] for k in ('method', 'limitation', 'horizon_sessions', 'summary')},
                        'interpretation': 'Short-horizon price forecasts in these experiments cluster near the last-close random-walk baseline. The evidence does not establish predictive superiority. The architecture prioritizes constrained allocation and explicit Black-Litterman views; the separate Phase 8 walk-forward allocation replay measures its risk and cost tradeoffs on the five-stock 2025 window.'},
        'integrity': {'quarantined_rf_count': quarantined, 'ppo_status': 'experimental_disabled',
                      'ppo_preprocessing': 'Causal expanding-window HMM filtering; causal_preprocessing=true.',
                      'advisor': 'Hybrid local MiniLM and TF-IDF with offline TF-IDF fallback. Labeled numerical claims are checked against canonical portfolio facts and mismatches receive deterministic corrections. This does not verify every prose claim.'}}
