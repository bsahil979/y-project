import unittest
import numpy as np
import torch
from sklearn.preprocessing import MinMaxScaler
from research.audit_saved_forecasts import checkpoint_prediction


class ConstantModel:
    def __init__(self, value):
        self.value = value

    def __call__(self, _window):
        return torch.tensor([[self.value]])


class SavedForecastAuditTests(unittest.TestCase):
    def test_price_checkpoint_uses_saved_price_scaler_without_refitting(self):
        scaler = MinMaxScaler().fit(np.array([[100.], [200.]]))
        predictions = checkpoint_prediction(ConstantModel(.5), scaler, np.linspace(150, 250, 100), 3)
        np.testing.assert_allclose(predictions, [150, 150, 150])
        np.testing.assert_allclose(scaler.data_max_, [200])

    def test_return_checkpoint_uses_return_scaler_and_compounds_from_latest_close(self):
        scaler = MinMaxScaler().fit(np.array([[-.1], [.1]]))
        predictions = checkpoint_prediction(ConstantModel(.55), scaler, np.full(100, 500.), 2, returns=True)
        np.testing.assert_allclose(predictions, [505., 510.05], rtol=1e-6)
