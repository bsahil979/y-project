"""Compare saved MarketMind predictions to a training-only majority baseline."""
import hashlib
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score


ROOT = Path(__file__).resolve().parents[1]


def checked_csv(path, sha256, **options):
    with path.open('rb') as handle:
        if hashlib.sha256(handle.read()).hexdigest() != sha256:
            raise ValueError(f'Historical input hash mismatch for {path.name}')
    return pd.read_csv(path, **options)


def evaluate():
    archive = ROOT / 'models/phase_2e'
    manifest = json.loads((archive / 'phase_2e_prediction_manifest.json').read_text(encoding='utf-8'))
    report = json.loads((archive / 'phase_2e_classification_report.json').read_text(encoding='utf-8'))
    rows = checked_csv(archive / 'holdout_predictions.csv', report['input']['prediction_csv_sha256'],
                       parse_dates=['Date'])
    train = checked_csv(ROOT / 'models/meta_model/meta_dataset.csv', manifest['dataset']['sha256'],
                        usecols=['ticker', 'Date', 'target'], parse_dates=['Date'])
    train = train.sort_values(['ticker', 'Date'])
    if train.duplicated(['ticker', 'Date']).any():
        raise ValueError('Training data has duplicate ticker dates.')
    label_end = train.groupby('ticker')['Date'].shift(-5)
    cutoff = pd.Timestamp(manifest['split']['train_end'])
    majority = int(train.loc[label_end <= cutoff, 'target'].mode().iloc[0])
    if rows.Date.min() <= cutoff or len(rows) != manifest['split']['holdout_rows']:
        raise ValueError('Predictions do not match the archived chronology.')
    rows['Majority'] = majority
    scores = {}
    for name, group in [('All', rows), *rows.groupby('market')]:
        actual = group.actual_target
        scores[name] = {'rows': len(group), 'models': {}}
        for model in ['A_prediction', 'B_prediction', 'Majority']:
            scores[name]['models'][model] = {
                'accuracy': accuracy_score(actual, group[model]),
                'balanced_accuracy': balanced_accuracy_score(actual, group[model]),
                'macro_f1': f1_score(actual, group[model], labels=[-1, 0, 1], average='macro', zero_division=0),
            }
    return {'train_cutoff': str(cutoff.date()), 'majority_label': majority, 'scores': scores}


if __name__ == '__main__':
    print(json.dumps(evaluate(), indent=2, allow_nan=False))
