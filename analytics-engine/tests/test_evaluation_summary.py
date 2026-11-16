from services.evaluation_summary import evaluation_summary


def test_summary_matches_artifacts_and_labels_unvalidated_changes():
    result = evaluation_summary()
    assert result['integrity']['quarantined_rf_count'] == 100
    assert result['regime']['convergence'] == {'fits': 70, 'converged': 70, 'iteration_cap_failures': 0}
    assert not result['regime']['stale']
    assert result['marketmind']['rows'] == 42568
    assert result['marketmind']['models']['A']['accuracy'] < result['marketmind']['majority_baseline']['accuracy']
    assert result['personalized']['evaluation_status'] == 'completed_retrospective_walk_forward'
    assert len(result['personalized']['constraints']) == 9
    assert result['forecasting']['lstm']['test_lstm_mae'] > result['forecasting']['lstm']['test_baseline_mae']


def test_summary_api():
    from fastapi.testclient import TestClient
    from api import app
    response = TestClient(app).get('/research/evaluation-summary')
    assert response.status_code == 200
    assert response.json()['read_only'] is True
