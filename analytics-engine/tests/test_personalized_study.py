import json
import numpy as np
import pandas as pd
import pytest
from research.personalized_study import training_rows, probabilities_as_of, FEATURE_COLUMNS, statistics, OUTPUT
from services.personalized_research import personalized_study_results


def sample_features():
    dates = pd.bdate_range('2023-01-01', periods=180)
    rng = np.random.default_rng(42)
    frames = []
    for ticker in ('A', 'B', 'C'):
        frame = pd.DataFrame(rng.normal(size=(180, len(FEATURE_COLUMNS))), columns=FEATURE_COLUMNS)
        frame['ticker'], frame['Date'] = ticker, dates
        frame['label_end'] = pd.Series(dates).shift(-5)
        frame['target'] = rng.integers(0, 3, 180)
        frame['regime_code'], frame['regime_available'] = 1, True
        frames.append(frame)
    return pd.concat(frames, ignore_index=True), dates


def test_labels_mature_before_prediction_and_future_changes_cannot_affect_probabilities():
    frame, dates = sample_features()
    decision = dates[120]
    train = training_rows(frame, dates[0], decision)
    assert train.label_end.max() <= decision
    assert train.Date.max() == dates[115]
    first, audit = probabilities_as_of(frame, ['A','B','C'], dates[0], decision)
    changed = frame.copy()
    changed.loc[changed.Date > decision, FEATURE_COLUMNS] = 999
    changed.loc[changed.label_end > decision, 'target'] = 2
    second, _ = probabilities_as_of(changed, ['A','B','C'], dates[0], decision)
    assert first == second
    assert all(r['training_label_end'] <= r['decision_date'] for r in audit)
    for probabilities in first.values():
        assert sum(probabilities.values()) == pytest.approx(1)


def test_signed_drawdown_includes_initial_capital_and_cost_sensitive_sharpe():
    gross = np.array([-.1, .02, -.01])
    values = statistics(gross)
    assert values['max_drawdown'] == pytest.approx(-.1)
    assert statistics((1-.001)*(1+gross)-1)['sharpe'] < values['sharpe']


def test_saved_replay_has_causal_dates_feasible_targets_and_no_observed_sentiment():
    result = personalized_study_results()
    assert not result['stale']
    assert result['sentiment_coverage'] == 'unavailable_in_historical_replay'
    assert all(r['observation_count'] == 249 for r in result['metrics'])
    predictions = json.loads((OUTPUT/'predictions.json').read_text())
    assert all(r['training_feature_end'] < r['decision_date'] and r['training_label_end'] <= r['decision_date'] for r in predictions)
    decisions = json.loads((OUTPUT/'decisions.json').read_text())
    for row in decisions:
        assert row['decision_date'] < row['execution_date'] < row['first_return_date']
        allocation = row['allocation']
        assert sum(allocation['weights'].values()) == pytest.approx(1)
        assert max(allocation['weights'].values()) <= allocation['max_weight_cap'] + 1e-7
        if 'provenance' in allocation:
            for view in allocation['provenance'].values():
                assert view['finbert_score'] is None
    metrics = {r['strategy']: r for r in result['metrics']}
    for key in ('annualized_return', 'annualized_volatility', 'max_drawdown', 'sharpe'):
        assert metrics['Conservative'][key] == pytest.approx(metrics['Equal weight'][key], abs=1e-10)


def test_artifact_corruption_is_not_served_as_valid(tmp_path, monkeypatch):
    import services.personalized_research as module
    (tmp_path/'manifest.json').write_text(json.dumps({'source_sha256': {}, 'input_sha256': {}, 'output_sha256': {'summary.json': 'wrong'}}))
    (tmp_path/'summary.json').write_text('{}')
    monkeypatch.setattr(module, 'STUDY', tmp_path)
    with pytest.raises(ValueError, match='integrity'):
        module.personalized_study_results()
