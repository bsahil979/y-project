import json
import os
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from services.sentiment_analyzer import get_sentiment_analysis
from services.historical_sentiment import HistoricalSentimentStore
from services.hmm_engine import causal_regime_features
from trading_engine.data_manager import get_processed_data


DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
META_MODEL_DIR = os.path.join(DEFAULT_MODEL_DIR, 'meta_model')

FEATURE_COLUMNS = [
    'returns',
    'rsi',
    'macd',
    'macd_signal',
    'macd_diff',
    'adx',
    'volatility',
    'ema_50',
    'ema_200',
    'trend_strength',
    'momentum_5d',
    'momentum_10d',
    'sentiment_score',
    'regime_code',
]

DATASET_VERSION = 'marketmind-v1'


class MarketMindMetaModel:
    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = model_dir or META_MODEL_DIR
        os.makedirs(self.model_dir, exist_ok=True)
        self.model_path = os.path.join(self.model_dir, 'meta_model.pkl')
        self.metrics_path = os.path.join(self.model_dir, 'meta_model_metrics.json')
        self.feature_path = os.path.join(self.model_dir, 'feature_columns.json')
        self.model = None
        self.feature_columns = FEATURE_COLUMNS.copy()
        self.metadata = {}

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return float(default)

    @staticmethod
    def _sentiment_score(ticker: str):
        try:
            result = get_sentiment_analysis(ticker)
            return MarketMindMetaModel._safe_float(result.get('overall_score', 0.0), 0.0)
        except Exception:
            return 0.0

    @staticmethod
    def _build_signal_features(df: pd.DataFrame, ticker: str = None) -> pd.DataFrame:
        out = df.copy()
        out['ema_50'] = out['Close'].ewm(span=50, adjust=False).mean()
        out['ema_200'] = out['Close'].ewm(span=200, adjust=False).mean()
        out['trend_strength'] = (out['Close'] - out['ema_50']) / out['ema_50'].replace(0, np.nan)
        out['momentum_5d'] = out['Close'].pct_change(5)
        out['momentum_10d'] = out['Close'].pct_change(10)
        # All features here are point-in-time or backward-looking. Forecast and
        # downstream-model outputs are intentionally not part of MarketMind.
        regimes = causal_regime_features(out['returns'])
        # Keep the saved 14-feature shape; probabilities are diagnostics.
        # Legacy estimators receive their original code encoding at inference.
        out['hmm_state'] = regimes['regime_code']
        out['regime_code'] = regimes['regime_code']
        for column in ['regime_available', 'regime_prob_0', 'regime_prob_1', 'regime_prob_2']:
            out[column] = regimes[column]
        return out

    @classmethod
    def _label_for_future_return(cls, future_return: pd.Series, buy_threshold: float, sell_threshold: float) -> pd.Series:
        return np.where(
            future_return > buy_threshold,
            1,
            np.where(future_return < sell_threshold, -1, 0),
        )

    def build_dataset(
        self,
        tickers: Iterable[str],
        start: str = '2018-01-01',
        end: Optional[str] = None,
        horizon: int = 5,
        buy_threshold: float = 0.01,
        sell_threshold: float = -0.01,
        max_rows: Optional[int] = None,
        historical_sentiment_path: Optional[str] = None,
    ) -> pd.DataFrame:
        if horizon < 1:
            raise ValueError('horizon must be at least 1 day.')
        if sell_threshold >= buy_threshold:
            raise ValueError('sell_threshold must be less than buy_threshold.')
        # Historical construction must never call the live news service.  The
        # store performs the point-in-time cutoff; missing history is neutral.
        sentiment_path = historical_sentiment_path or os.path.join(
            self.model_dir, 'historical_sentiment.csv'
        )
        sentiment_store = HistoricalSentimentStore(sentiment_path)
        rows = []
        coverage = []
        for ticker in tickers:
            ticker = str(ticker).upper().strip()
            record = {
                'ticker': ticker,
                'status': 'not_processed',
                'raw_rows': 0,
                'window_rows': 0,
                'feature_rows': 0,
                'target_rows': 0,
                'final_rows': 0,
                'raw_first_date': None,
                'raw_last_date': None,
                'window_first_date': None,
                'window_last_date': None,
                'final_first_date': None,
                'final_last_date': None,
                'error_type': None,
                'error': None,
            }
            try:
                # Use max history so the requested start/end window is respected.
                # A fixed short provider period silently discarded older training data.
                df = get_processed_data(ticker=ticker, period='max', interval='1d')
            except Exception as exc:
                # Keep the failure visible.  Previously this continue made a
                # partial dataset look like a successful full-universe build.
                record.update(status='fetch_error', error_type=type(exc).__name__, error=str(exc))
                coverage.append(record)
                continue
            if df is None or df.empty:
                record['status'] = 'empty_fetch'
                coverage.append(record)
                continue
            df = df.copy()
            record['raw_rows'] = int(len(df))
            if len(df):
                record['raw_first_date'] = str(df.index.min())
                record['raw_last_date'] = str(df.index.max())
            df = df.loc[(df.index >= pd.Timestamp(start))]
            if end is not None:
                df = df.loc[(df.index <= pd.Timestamp(end))]
            if df.empty:
                record['status'] = 'outside_requested_window'
                coverage.append(record)
                continue
            record['window_rows'] = int(len(df))
            record['window_first_date'] = str(df.index.min())
            record['window_last_date'] = str(df.index.max())
            try:
                df = self._build_signal_features(df, ticker=ticker)
            except Exception as exc:
                record.update(status='feature_error', error_type=type(exc).__name__, error=str(exc))
                coverage.append(record)
                continue
            record['feature_rows'] = int(len(df))
            df['sentiment_score'] = [
                sentiment_store.score_as_of(ticker, observation_date)
                for observation_date in df.index
            ]
            df['ticker'] = ticker
            future_return = (df['Close'].shift(-horizon) / df['Close']) - 1
            label = self._label_for_future_return(future_return, buy_threshold, sell_threshold)
            df['target'] = label
            df['future_return'] = future_return
            # Target-bearing rows are counted before the final finite-value
            # filter so coverage can distinguish label construction from a
            # later feature/filtering exclusion.
            record['target_rows'] = int(future_return.notna().sum())
            if 'Date' not in df.columns:
                df = df.copy()
                df.insert(1, 'Date', pd.to_datetime(df.index))

            try:
                selected = df[[
                    'ticker', 'Date', 'Close', 'returns', 'rsi', 'macd',
                    'macd_signal', 'macd_diff', 'adx', 'volatility', 'ema_50',
                    'ema_200', 'trend_strength', 'momentum_5d', 'momentum_10d',
                    'sentiment_score', 'regime_code', 'target', 'future_return',
                ]].copy()
            except Exception as exc:
                record.update(status='schema_error', error_type=type(exc).__name__, error=str(exc))
                coverage.append(record)
                continue
            selected = selected.replace([np.inf, -np.inf], np.nan).dropna()
            record['final_rows'] = int(len(selected))
            if len(selected):
                record['final_first_date'] = str(selected['Date'].min())
                record['final_last_date'] = str(selected['Date'].max())
            record['status'] = 'included' if len(selected) else 'filtered_after_features'
            coverage.append(record)
            rows.append(selected)
        if not rows:
            raise ValueError('No valid rows were produced for the selected tickers.')

        dataset = pd.concat(rows, ignore_index=True)
        # Preserve temporal order. Random sampling would make the holdout depend
        # on future observations and makes training irreproducible as a time series.
        dataset = dataset.sort_values(['Date', 'ticker']).reset_index(drop=True)
        if max_rows is not None and len(dataset) > max_rows:
            dataset = dataset.tail(max_rows).reset_index(drop=True)
        dataset_path = os.path.join(self.model_dir, 'meta_dataset.csv')
        dataset.to_csv(dataset_path, index=False)
        manifest = {
            'dataset_version': DATASET_VERSION,
            'regime_feature_source': 'causal_gaussian_hmm',
            'tickers': sorted(dataset['ticker'].unique().tolist()),
            'rows': int(len(dataset)),
            'date_start': str(dataset['Date'].min()),
            'date_end': str(dataset['Date'].max()),
            'horizon_days': horizon,
            'buy_threshold': buy_threshold,
            'sell_threshold': sell_threshold,
            'features': self.feature_columns.copy(),
            'sentiment': {
                'source': os.path.abspath(sentiment_path) if sentiment_store.available else 'neutral_fallback',
                'point_in_time_cutoff': 'article_date <= observation_date',
                'future_news_excluded': True,
            },
        }
        with open(os.path.join(self.model_dir, 'dataset_manifest.json'), 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        metadata_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'ticker_metadata.csv')
        metadata = pd.read_csv(metadata_path, dtype=str)
        metadata['ticker'] = metadata['ticker'].astype(str).str.upper().str.strip()
        coverage_frame = pd.DataFrame(coverage).merge(
            metadata[['ticker', 'market']], on='ticker', how='left', validate='one_to_one'
        )

        def coverage_summary(frame: pd.DataFrame) -> dict:
            present = int(frame['status'].eq('included').sum())
            return {
                'configured': int(len(frame)),
                'present': present,
                'excluded': int(len(frame) - present),
            }

        coverage_report = {
            'configured_tickers': int(len(coverage)),
            'dataset_tickers': int(dataset['ticker'].nunique()),
            'included_tickers': sorted(dataset['ticker'].unique().tolist()),
            'missing_tickers': sorted(set(item['ticker'] for item in coverage) - set(dataset['ticker'].unique())),
            'status_counts': pd.Series([item['status'] for item in coverage]).value_counts().to_dict(),
            'by_market': {
                str(market): coverage_summary(group)
                for market, group in coverage_frame.groupby('market', dropna=False)
            },
            'tickers': coverage,
        }
        with open(os.path.join(self.model_dir, 'coverage_report.json'), 'w', encoding='utf-8') as f:
            json.dump(coverage_report, f, indent=2)
        pd.DataFrame(coverage).to_csv(os.path.join(self.model_dir, 'coverage_report.csv'), index=False)
        with open(self.feature_path, 'w', encoding='utf-8') as f:
            json.dump(self.feature_columns, f, indent=2)
        return dataset

    def train(self, dataset: pd.DataFrame, test_size: float = 0.2, random_state: int = 42):
        if not 0 < test_size < 1:
            raise ValueError('test_size must be between 0 and 1.')
        if 'target' not in dataset.columns:
            raise ValueError('Dataset must contain a target column.')
        if 'Date' in dataset.columns:
            dates = pd.to_datetime(dataset['Date'], errors='coerce')
            if dates.isna().any() or not dates.is_monotonic_increasing:
                raise ValueError('Dataset must have valid dates in chronological order.')
            unique_dates = dates.drop_duplicates().reset_index(drop=True)
            date_split_at = int(len(unique_dates) * (1 - test_size))
            if date_split_at < 1 or date_split_at >= len(unique_dates):
                raise ValueError('Dataset does not contain enough dates for the requested test_size.')
            split_at = int((dates < unique_dates.iloc[date_split_at]).sum())
        else:
            split_at = int(len(dataset) * (1 - test_size))
        if dataset['target'].isna().any():
            raise ValueError('Dataset target contains missing values.')
        if not set(dataset['target'].astype(int).unique()).issubset({-1, 0, 1}):
            raise ValueError('Dataset target must contain only -1, 0, and 1 labels.')

        missing_features = [c for c in self.feature_columns if c not in dataset.columns]
        if missing_features:
            raise ValueError(f'Dataset is missing required feature columns: {missing_features}')
        features = self.feature_columns.copy()

        X = dataset[features].replace([np.inf, -np.inf], np.nan)
        y = dataset['target'].astype(int)

        # Classifiers use non-negative class IDs; map the public labels temporarily.
        label_map = {-1: 0, 0: 1, 1: 2}
        y_mapped = y.map(label_map)

        if split_at < 1 or split_at >= len(dataset):
            raise ValueError('Dataset is too small for the requested test_size.')
        X_train, X_test = X.iloc[:split_at].copy(), X.iloc[split_at:].copy()
        y_train, y_test = y.iloc[:split_at], y.iloc[split_at:]
        y_mapped_train, y_mapped_test = y_mapped.iloc[:split_at], y_mapped.iloc[split_at:]
        # Impute using training-only statistics; using the complete dataset here
        # would leak information from the future holdout into model fitting.
        medians = X_train.median().fillna(0.0)
        X_train = X_train.fillna(medians)
        X_test = X_test.fillna(medians)

        candidate_models = {
            'random_forest': RandomForestClassifier(
                n_estimators=250, random_state=random_state,
                class_weight='balanced', n_jobs=-1,
            ),
            'hist_gradient_boost': HistGradientBoostingClassifier(random_state=random_state),
        }

        metrics = {}
        best_name = None
        best_model = None
        best_score = -1.0

        for name, model in candidate_models.items():
            try:
                model.fit(X_train, y_mapped_train)
            except Exception:
                continue
            preds = model.predict(X_test)
            # Remap predictions back from {0, 1, 2} to {-1, 0, 1} for evaluation
            reverse_map = {0: -1, 1: 0, 2: 1}
            preds = np.array([reverse_map.get(int(p), 0) for p in preds])
            accuracy = accuracy_score(y_test, preds)
            macro_f1 = f1_score(y_test, preds, average='macro', zero_division=0)
            precision = precision_score(y_test, preds, average='macro', zero_division=0)
            recall = recall_score(y_test, preds, average='macro', zero_division=0)

            metrics[name] = {
                'accuracy': float(accuracy),
                'f1_macro': float(macro_f1),
                'precision_macro': float(precision),
                'recall_macro': float(recall),
            }

            if macro_f1 > best_score:
                best_score = macro_f1
                best_name = name
                best_model = model

        if best_model is None:
            raise RuntimeError('No model could be trained.')

        self.model = best_model
        self.metadata = {
            'dataset_version': DATASET_VERSION,
            'regime_feature_source': 'causal_gaussian_hmm',
            'selected_model': best_name,
            'metrics': metrics,
            'features': features,
            'test_size': test_size,
            'split': 'chronological_final_block',
            'rows': int(len(dataset)),
            'date_range': {
                'train_end': str(dataset.iloc[len(X_train) - 1]['Date']) if 'Date' in dataset else None,
                'test_start': str(dataset.iloc[len(X_train)]['Date']) if 'Date' in dataset and len(X_test) else None,
            },
        }

        with open(self.feature_path, 'w', encoding='utf-8') as f:
            json.dump(features, f, indent=2)
        with open(self.metrics_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)

        with open(self.model_path, 'wb') as f:
            import pickle
            pickle.dump(best_model, f)

        return self.metadata

    def is_ready(self) -> bool:
        required = (self.model_path, self.metrics_path, self.feature_path)
        if not all(os.path.exists(path) for path in required):
            return False
        try:
            with open(self.metrics_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            with open(self.feature_path, 'r', encoding='utf-8') as f:
                features = json.load(f)
            metadata_is_current = (
                metadata.get('dataset_version') == DATASET_VERSION
                and features == FEATURE_COLUMNS
                and metadata.get('features') == FEATURE_COLUMNS
                and metadata.get('split') == 'chronological_final_block'
            )
            if not metadata_is_current:
                return False
            # A current manifest is not sufficient: reject a stale or unreadable
            # pickle and models trained with a different number of features.
            with open(self.model_path, 'rb') as f:
                import pickle
                estimator = pickle.load(f)
            return getattr(estimator, 'n_features_in_', len(FEATURE_COLUMNS)) == len(FEATURE_COLUMNS)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return False
        except Exception:
            return False

    def load(self):
        if not self.is_ready():
            return False
        with open(self.model_path, 'rb') as f:
            import pickle
            self.model = pickle.load(f)
        if os.path.exists(self.feature_path):
            with open(self.feature_path, 'r', encoding='utf-8') as f:
                self.feature_columns = json.load(f)
        if os.path.exists(self.metrics_path):
            with open(self.metrics_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        return True

    def predict_single(self, row: pd.DataFrame):
        if self.model is None:
            raise ValueError('The model is not loaded.')
        if row.empty:
            raise ValueError('No row available for prediction.')
        missing_features = [c for c in self.feature_columns if c not in row.columns]
        if missing_features:
            raise ValueError(f'Input row is missing required feature columns: {missing_features}')
        features = self.feature_columns
        x = row[features].replace([np.inf, -np.inf], np.nan)
        if 'regime_code' in x and self.metadata.get('regime_feature_source') != 'causal_gaussian_hmm':
            x['regime_code'] = x['regime_code'].map({0: 1, 1: 0, 2: -1})
        # A live row must be finite. Use conservative neutral values rather than
        # forward/backward filling from another observation or from the holdout.
        x = x.fillna(0.0)
        probs = self.model.predict_proba(x)[0]
        class_labels = self.model.classes_
        idx = int(np.argmax(probs))
        label = int(class_labels[idx])
        confidence = float(probs[idx])
        # Map {0, 1, 2} back to {-1, 0, 1} and recommendation
        reverse_map = {0: -1, 1: 0, 2: 1}
        mapped_label = reverse_map.get(label, 0)
        return {
            'recommendation': 'BUY' if mapped_label == 1 else ('SELL' if mapped_label == -1 else 'HOLD'),
            'score': int(mapped_label),
            'confidence': round(confidence, 4),
            'directional_probabilities': {name: float(dict(zip(class_labels, probs)).get(label, 0.0))
                for name, label in [('buy', 2), ('hold', 1), ('sell', 0)]},
            'class_probabilities': {str(int(c)): float(p) for c, p in zip(class_labels, probs)},
        }

    def predict_for_ticker(self, ticker: str, horizon: int = 5):
        if not self.is_ready() and not self.load():
            raise FileNotFoundError('Meta model not found. Run the training script first.')
        df = get_processed_data(ticker=ticker, period='3y', interval='1d')
        if df is None or df.empty:
            raise ValueError(f'No data available for {ticker}.')
        df = self._build_signal_features(df, ticker=ticker)
        sentiment_score = self._sentiment_score(ticker)
        df['sentiment_score'] = sentiment_score
        row = df.tail(1).copy()

        row = row[[c for c in self.feature_columns if c in row.columns]].copy()
        result = self.predict_single(row)
        latest = df.iloc[-1]
        available = bool(latest['regime_available'])
        result['regime'] = {'state_id': int(latest['hmm_state']) if available else None,
            'state_probabilities': [float(latest[f'regime_prob_{k}']) for k in range(3)] if available else None,
            'available': available, 'feature_encoding': ('canonical_0_1_2' if self.metadata.get('regime_feature_source') == 'causal_gaussian_hmm' else 'legacy_1_0_minus1'),
            'source': 'causal_gaussian_hmm', 'legacy_model_requires_revalidation': self.metadata.get('regime_feature_source') != 'causal_gaussian_hmm'}
        return result
