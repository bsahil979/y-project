from copy import deepcopy

import pytest

from evaluations.forecast_tracking import score


def test_prospective_forecast_compares_same_observed_sessions_and_rejects_lookahead():
    record = {
        "recorded_at": "2026-11-16T22:00:00Z",
        "forecast": {
            "ticker": "MSFT", "model_family": "TimesFM-2.5", "price_as_of": "2026-11-16",
            "spot_price": 100, "forecast": [{"predicted_price": 103}, {"predicted_price": 106}],
        },
    }
    actuals = [
        {"session_date": "2026-11-16", "close_at": "2026-11-16T21:00:00Z", "close": 100},
        {"session_date": "2026-11-17", "close_at": "2026-11-17T21:00:00Z", "close": 102},
        {"session_date": "2026-11-18", "close_at": "2026-11-18T21:00:00Z", "close": 104},
    ]
    result = score(record, actuals)
    assert result["model_mae_pct_of_spot"] == 1.5
    assert result["last_close_mae_pct_of_spot"] == 3
    assert result["terminal_direction_correct"]
    assert not result["last_close_terminal_direction_correct"]

    with pytest.raises(ValueError, match="Need 2 observed trading sessions"):
        score(record, actuals[:-1])

    late = deepcopy(record)
    late["recorded_at"] = actuals[1]["close_at"]
    with pytest.raises(ValueError, match="follow forecast capture"):
        score(late, actuals)
