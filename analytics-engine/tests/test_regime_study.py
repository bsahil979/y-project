import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from services.regime_allocation import (AllocationConfig, _convergence_summary,
                                        fit_allocations, minimum_variance)
from research.regime_study import run_study


class RegimeStudyTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(51)
        daily = rng.normal(.0003, [.012, .022, .03], size=(130, 3))
        daily[40:80] += rng.normal(-.002, .02, size=(40, 1))
        self.prices = pd.DataFrame(100 * np.exp(np.cumsum(daily, axis=0)),
                                   index=pd.bdate_range('2020-01-01', periods=130),
                                   columns=['A', 'B', 'C'])
        self.config = AllocationConfig(lookback=60, min_observations=30, max_weight=.6)

    def test_optimizer_respects_cap_and_prefers_lower_risk(self):
        weights = minimum_variance(np.diag([.001, .02, .1]), .6)
        self.assertAlmostEqual(weights.sum(), 1)
        self.assertTrue((weights >= 0).all())
        self.assertTrue((weights <= .600001).all())
        self.assertGreater(weights[0], weights[1])
        with self.assertRaises(ValueError):
            minimum_variance(np.eye(3), .2)

    def test_hmm_convergence_summary_flags_iteration_cap(self):
        capped = SimpleNamespace(n_iter=200, monitor_=SimpleNamespace(iter=200, history=[-10.0, -9.5]))
        summary = _convergence_summary(capped, 1e-4)
        self.assertFalse(summary['converged'])
        self.assertTrue(summary['iteration_limit_reached'])
        self.assertAlmostEqual(summary['last_log_likelihood_change'], .5)

        converged = SimpleNamespace(n_iter=200, monitor_=SimpleNamespace(iter=17, history=[-10.0, -9.99995]))
        summary = _convergence_summary(converged, 1e-4)
        self.assertTrue(summary['converged'])
        self.assertFalse(summary['iteration_limit_reached'])

    def test_fit_is_reproducible_and_uses_requested_window(self):
        returns = self.prices.pct_change().dropna()
        first = fit_allocations(returns, self.config)
        second = fit_allocations(returns, self.config)
        self.assertEqual(first, second)
        self.assertEqual(first['observations'], 60)
        self.assertEqual(first['training_start'], str(returns.index[-60].date()))
        self.assertAlmostEqual(sum(state['probability'] for state in first['states']), 1)
        self.assertTrue(all(state['covariance_fallback'] == (state['training_membership_mass'] < 2)
                            for state in first['states']))
        self.assertAlmostEqual(sum(first['weights'].values()), 1)
        self.assertTrue(all(0 <= weight <= .600001 for weight in first['weights'].values()))

    def test_future_changes_cannot_change_earlier_decisions_or_equity(self):
        original = run_study(self.prices, self.config)
        changed_prices = self.prices.copy()
        changed_prices.iloc[110:] *= np.array([1.8, .5, 1.2])
        changed = run_study(changed_prices, self.config)
        cutoff = self.prices.index[110]
        pd.testing.assert_frame_equal(original['equity'].loc[:self.prices.index[109]],
                                      changed['equity'].loc[:self.prices.index[109]])
        for old, new in zip(original['decisions'], changed['decisions']):
            if pd.Timestamp(old['training_end']) < cutoff:
                self.assertEqual(old['training_end'], new['training_end'])
                for key in ('weights', 'baseline_weights'):
                    np.testing.assert_allclose(list(old[key].values()), list(new[key].values()), atol=1e-10, rtol=1e-10)
                np.testing.assert_allclose([state['probability'] for state in old['states']],
                                           [state['probability'] for state in new['states']], atol=1e-10, rtol=1e-10)
            self.assertLess(old['training_end'], old['execution_date'])
            self.assertLess(old['execution_date'], old['first_return_date'])

    def test_first_loss_cost_and_buy_hold_drift_are_retained(self):
        prices = pd.DataFrame(100.0, index=pd.bdate_range('2020-01-01', periods=35), columns=['A', 'B', 'C'])
        prices.iloc[32] = [90, 110, 100]
        prices.iloc[33] = [99, 110, 95]
        prices.iloc[34] = [108.9, 99, 95]
        fixed = {'weights': {'A': .5, 'B': .3, 'C': .2},
                 'baseline_weights': {'A': .5, 'B': .3, 'C': .2},
                 'training_end': str(prices.index[30].date())}
        config = AllocationConfig(lookback=30, min_observations=30, max_weight=.6)
        with patch('research.regime_study.fit_allocations', return_value=fixed):
            result = run_study(prices, config, cost_bps=10)
        self.assertAlmostEqual(result['equity']['Minimum variance'].iloc[1], .999 * .98)
        expected = .999 * (prices.iloc[-1] / prices.iloc[31]).mean()
        self.assertAlmostEqual(result['equity']['Buy and hold'].iloc[-1], expected)
        ledger = result['ledger'].query("strategy == 'Buy and hold'")
        self.assertAlmostEqual(ledger.turnover.sum(), 1)
        self.assertEqual(result['metrics'].loc['Buy and hold', 'observation_count'], 3)
        self.assertLess(result['metrics'].loc['Minimum variance', 'max_drawdown'], -.02)

    def test_short_or_invalid_history_fails_explicitly(self):
        with self.assertRaises(ValueError):
            run_study(self.prices.iloc[:20], self.config)
        with self.assertRaises(ValueError):
            run_study(self.prices.iloc[::-1], self.config)
        invalid = self.prices.copy()
        invalid.iloc[50, 1] = np.nan
        with self.assertRaises(ValueError):
            run_study(invalid, self.config)


if __name__ == '__main__':
    unittest.main()
