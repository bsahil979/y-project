import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
from services.validated_forecast import samples, predict


class ValidatedForecastTests(unittest.TestCase):
    def test_return_targets_start_after_origin_and_inputs_end_at_origin(self):
        prices = np.exp(np.arange(400) * .001) * 100
        x, y, origins = samples(prices)
        self.assertTrue(np.allclose(x[0], .1))
        self.assertTrue(np.allclose(y[0], np.arange(1, 31) * .1, atol=.00001))
        self.assertEqual(origins[0], 60)

    def test_baseline_uses_current_close_not_training_close(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / 'MSFT'
            folder.mkdir()
            (folder / 'report.json').write_text(json.dumps({'model': 'Last-close baseline'}))
            with patch('services.validated_forecast.ROOT', Path(directory)):
                output = predict(pd.Series([500., 543.45]), 'MSFT', 30)
            self.assertEqual(len(output['forecast']), 30)
            self.assertTrue(all(row['predicted_price'] == 543.45 for row in output['forecast']))
            self.assertEqual(output['model'], 'Last-close baseline')
