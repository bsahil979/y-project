import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from trading_engine.meta_model import DATASET_VERSION, FEATURE_COLUMNS, MarketMindMetaModel
from trading_engine.data_manager import fetch_asset_data
from services.historical_sentiment import HistoricalSentimentStore
from training.leakage_audit import audit_dataset
from training.marketmind_pytorch import (MarketMindDataset, MarketMindMLP, MarketMindMappings,
                                          attach_ticker_metadata, chronological_split, load_ticker_metadata)


class MarketMindPipelineTests(unittest.TestCase):
    def test_historical_fetch_fails_closed_when_all_providers_fail(self):
        with patch('trading_engine.data_manager.yf.download', return_value=pd.DataFrame()), \
                patch('trading_engine.data_manager.fetch_stooq_daily_ohlcv', side_effect=ValueError('unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'No provider data available'):
                fetch_asset_data('TATAMOTORS.NS', period='max', interval='1d')

    def test_experiment_b_dataset_keeps_numeric_and_ids_separate(self):
        frame = self._dataset(12)
        frame['ticker'] = ['AAPL', 'MSFT'] * 6
        frame['market'] = ['US'] * 12
        frame['sector'] = ['Technology'] * 12
        mappings = MarketMindMappings.fit(frame)
        sample = MarketMindDataset(frame, FEATURE_COLUMNS, mappings)[0]
        self.assertEqual(tuple(sample['numeric'].shape), (len(FEATURE_COLUMNS),))
        self.assertEqual(sample['ticker_id'].dtype, __import__('torch').long)
        model = MarketMindMLP(len(FEATURE_COLUMNS), len(mappings.ticker_to_index),
                              len(mappings.market_to_index), len(mappings.sector_to_index))
        logits = model(sample['numeric'].unsqueeze(0), sample['ticker_id'].reshape(1),
                       sample['market_id'].reshape(1), sample['sector_id'].reshape(1))
        self.assertEqual(tuple(logits.shape), (1, 3))

    def test_experiment_b_requires_authoritative_metadata(self):
        frame = self._dataset(4)
        frame['ticker'] = ['AAPL'] * 4
        with self.assertRaises(ValueError):
            MarketMindMappings.fit(frame)
        enriched = attach_ticker_metadata(frame, pd.DataFrame([{
            'ticker': 'AAPL', 'market': 'US', 'sector': 'Information Technology'
        }]))
        self.assertEqual(enriched['sector'].iloc[0], 'Information Technology')

    def test_authoritative_metadata_covers_configured_universe(self):
        metadata = load_ticker_metadata()
        self.assertEqual(len(metadata), 100)
        self.assertFalse(metadata[['market', 'sector']].eq('').any().any())

    def test_experiment_b_mappings_are_persisted_and_unknowns_are_safe(self):
        frame = self._dataset(4)
        frame['ticker'] = ['AAPL'] * 4
        frame['market'] = ['US'] * 4
        frame['sector'] = ['Information Technology'] * 4
        mappings = MarketMindMappings.fit(frame)
        with tempfile.TemporaryDirectory() as directory:
            mappings.save(directory)
            loaded = MarketMindMappings.load(directory)
            unknown = frame.assign(ticker='NVDA', market='US', sector='Technology')
            ids = loaded.encode(unknown)
            self.assertEqual(int(ids[0][0]), 0)
            self.assertEqual(loaded.ticker_to_index, mappings.ticker_to_index)

    def test_experiment_b_uses_experiment_a_chronological_split(self):
        frame = self._dataset(10)
        train, test = chronological_split(frame, test_size=0.2)
        self.assertLess(train['Date'].max(), test['Date'].min())

    def test_historical_sentiment_excludes_future_news(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as file:
            file.write('ticker,date,sentiment_score\nAAPL,2020-01-02,0.8\nAAPL,2020-01-04,-0.2\n')
            path = file.name
        try:
            store = HistoricalSentimentStore(path)
            self.assertAlmostEqual(store.score_as_of('AAPL', '2020-01-03'), 0.8)
            self.assertAlmostEqual(store.score_as_of('AAPL', '2020-01-04'), 0.3)
            self.assertEqual(store.score_as_of('MSFT', '2020-01-04'), 0.0)
        finally:
            os.unlink(path)

    def test_historical_sentiment_rejects_missing_schema(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as file:
            file.write('ticker,date\nAAPL,2020-01-02\n')
            path = file.name
        try:
            with self.assertRaises(ValueError):
                HistoricalSentimentStore(path)
        finally:
            os.unlink(path)

    def test_leakage_audit_passes_point_in_time_schema(self):
        dataset = self._dataset(12)
        dataset['ticker'] = ['AAPL', 'MSFT'] * 6
        dataset['future_return'] = np.linspace(-0.02, 0.02, len(dataset))
        report = audit_dataset(dataset, FEATURE_COLUMNS, horizon=5)
        self.assertEqual(report['status'], 'passed')
        self.assertTrue(report['split_requirements']['imputation_fit_window_only'])

    def test_leakage_audit_rejects_future_feature_and_duplicate_observation(self):
        dataset = self._dataset(12)
        dataset['ticker'] = 'AAPL'
        dataset['future_return'] = 0.02
        with self.assertRaises(ValueError):
            audit_dataset(dataset.assign(forecast_signal=0.1), FEATURE_COLUMNS + ['forecast_signal'])
        duplicate = pd.concat([dataset, dataset.iloc[[0]]], ignore_index=True)
        with self.assertRaises(ValueError):
            audit_dataset(duplicate, FEATURE_COLUMNS)

    def test_leakage_audit_rejects_feature_timestamp_after_observation(self):
        dataset = self._dataset(12)
        dataset['ticker'] = [f'T{i}' for i in range(12)]
        dataset['future_return'] = 0.02
        dataset['returns_timestamp'] = dataset['Date'] + pd.Timedelta(days=1)
        with self.assertRaises(ValueError):
            audit_dataset(
                dataset,
                FEATURE_COLUMNS,
                feature_timestamp_columns={'returns': 'returns_timestamp'},
            )

    def test_production_schema_excludes_downstream_and_future_features(self):
        forbidden = {
            'target', 'future_return', 'forecast_signal', 'forecast_magnitude',
            'rf_signal', 'prediction', 'predicted_return',
        }
        self.assertTrue(set(FEATURE_COLUMNS).isdisjoint(forbidden))
        self.assertEqual(len(FEATURE_COLUMNS), len(set(FEATURE_COLUMNS)))

    def _dataset(self, rows=90):
        dates = pd.date_range('2020-01-01', periods=rows, freq='D')
        data = {feature: np.linspace(0.01, 0.2, rows) for feature in FEATURE_COLUMNS}
        data['Date'] = dates
        data['target'] = np.where(np.arange(rows) % 3 == 0, -1, np.where(np.arange(rows) % 3 == 1, 0, 1))
        return pd.DataFrame(data)

    def test_train_uses_chronological_holdout_and_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as model_dir:
            model = MarketMindMetaModel(model_dir=model_dir)
            metadata = model.train(self._dataset())

            self.assertEqual(metadata['split'], 'chronological_final_block')
            self.assertLess(pd.Timestamp(metadata['date_range']['train_end']),
                            pd.Timestamp(metadata['date_range']['test_start']))
            self.assertTrue(model.is_ready())
            self.assertTrue(os.path.exists(os.path.join(model_dir, 'meta_model_metrics.json')))

    def test_train_rejects_unsorted_dates(self):
        dataset = self._dataset()
        dataset.loc[[0, 1], 'Date'] = dataset.loc[[1, 0], 'Date'].to_numpy()
        with tempfile.TemporaryDirectory() as model_dir:
            with self.assertRaises(ValueError):
                MarketMindMetaModel(model_dir=model_dir).train(dataset)

    def test_same_date_is_not_split_between_train_and_test(self):
        dataset = pd.concat([self._dataset(30), self._dataset(30)], ignore_index=True)
        dataset['Date'] = pd.date_range('2020-01-01', periods=30, freq='D').repeat(2)
        with tempfile.TemporaryDirectory() as model_dir:
            metadata = MarketMindMetaModel(model_dir=model_dir).train(dataset, test_size=0.2)
            self.assertNotEqual(metadata['date_range']['train_end'], metadata['date_range']['test_start'])

    def test_future_label_does_not_use_current_return(self):
        future = pd.Series([0.02, -0.02, np.nan])
        labels = MarketMindMetaModel._label_for_future_return(future, 0.01, -0.01)
        self.assertEqual(labels.tolist(), [1, -1, 0])

    def test_dataset_manifest_uses_current_schema_version(self):
        self.assertEqual(DATASET_VERSION, 'marketmind-v1')
        self.assertEqual(FEATURE_COLUMNS, MarketMindMetaModel().feature_columns)

    def test_stale_artifacts_are_not_ready(self):
        with tempfile.TemporaryDirectory() as model_dir:
            with open(os.path.join(model_dir, 'meta_model.pkl'), 'wb') as f:
                f.write(b'old-model')
            with open(os.path.join(model_dir, 'feature_columns.json'), 'w', encoding='utf-8') as f:
                f.write('[]')
            with open(os.path.join(model_dir, 'meta_model_metrics.json'), 'w', encoding='utf-8') as f:
                f.write('{"dataset_version": "old"}')
            self.assertFalse(MarketMindMetaModel(model_dir=model_dir).is_ready())

    def test_train_rejects_partial_feature_schema(self):
        dataset = self._dataset().drop(columns=[FEATURE_COLUMNS[-1]])
        with tempfile.TemporaryDirectory() as model_dir:
            with self.assertRaises(ValueError):
                MarketMindMetaModel(model_dir=model_dir).train(dataset)

    def test_predict_rejects_partial_feature_schema(self):
        with tempfile.TemporaryDirectory() as model_dir:
            model = MarketMindMetaModel(model_dir=model_dir)
            model.model = object()
            row = pd.DataFrame([{feature: 0.1 for feature in FEATURE_COLUMNS[:-1]}])
            with self.assertRaises(ValueError):
                model.predict_single(row)


if __name__ == '__main__':
    unittest.main()