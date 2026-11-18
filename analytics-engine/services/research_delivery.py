"""Read preserved research artifacts without claiming they reflect changed source."""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def regime_study_results():
    original = ROOT / 'research/regime_holdout_2026-09-27_v2'
    replay = ROOT / 'research/regime_reproduction_2026-10-12'
    current = ROOT / 'research/regime_evaluation_2026-11-17'
    manifest = json.loads((current / 'manifest.json').read_text())
    changed = [name for name, digest in manifest['source_sha256'].items()
               if not (ROOT/name).exists() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest]
    names = ['prices.csv','metrics.csv','holdout_metrics.csv','equity.csv','daily_ledger.csv','sensitivity.csv']
    matched = all((original/name).read_bytes() == (replay/name).read_bytes() for name in names)
    snapshot_valid = hashlib.sha256((current/'prices.csv').read_bytes()).hexdigest() == manifest['snapshot_sha256']
    return {'status': 'ready' if snapshot_valid else 'invalid_snapshot', 'stale': bool(changed),
            'changed_sources': changed, 'manifest': manifest,
            'reproduction': {'scope': 'archived_original_and_replay', 'status': 'matched' if matched else 'mismatch'},
            'convergence': json.loads((current/'convergence.json').read_text()),
            'holdout_metrics': pd.read_csv(current/'holdout_metrics.csv').to_dict('records'),
            'metrics': pd.read_csv(current/'metrics.csv').to_dict('records')}
