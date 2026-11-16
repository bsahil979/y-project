from pathlib import Path
import hashlib
import json

import pandas as pd

from api import regime_study_results


def test_delivered_reproduction_matches_preserved_experiment():
    root = Path(__file__).resolve().parents[1]
    original = root / 'research/regime_holdout_2026-09-27_v2'
    replay = root / 'research/regime_reproduction_2026-10-12'
    manifest = json.loads((replay / 'manifest.json').read_text())
    assert hashlib.sha256((replay / 'prices.csv').read_bytes()).hexdigest() == manifest['snapshot_sha256']
    for name in ['metrics.csv', 'holdout_metrics.csv', 'equity.csv', 'daily_ledger.csv', 'sensitivity.csv']:
        pd.testing.assert_frame_equal(pd.read_csv(original / name), pd.read_csv(replay / name))
    result = regime_study_results()
    assert result['status'] == 'ready'
    assert result['stale'] is False
    assert result['changed_sources'] == []
    assert 'services/hmm_engine.py' in result['manifest']['source_sha256']
    assert result['manifest']['snapshot_sha256'] == manifest['snapshot_sha256']
    assert result['convergence']['fits'] == result['convergence']['converged'] == 70
    assert result['reproduction']['status'] == 'matched'
    assert len(result['holdout_metrics']) == 4


def test_source_change_is_still_reported_as_stale(monkeypatch):
    original_read = Path.read_bytes

    def changed_read(path):
        data = original_read(path)
        return data + b'\n# simulated change' if path.name == 'regime_allocation.py' else data

    monkeypatch.setattr(Path, 'read_bytes', changed_read)
    result = regime_study_results()
    assert result['stale'] is True
    assert 'services/regime_allocation.py' in result['changed_sources']


def test_matching_source_manifest_is_not_stale(monkeypatch):
    from services import research_delivery
    original_load = research_delivery.json.loads
    def current_manifest(text):
        manifest = original_load(text)
        if 'source_sha256' not in manifest:
            return manifest
        manifest['source_sha256'] = {name: hashlib.sha256((research_delivery.ROOT/name).read_bytes()).hexdigest()
                                    for name in manifest['source_sha256']}
        return manifest
    monkeypatch.setattr(research_delivery.json, 'loads', current_manifest)
    assert regime_study_results()['stale'] is False
