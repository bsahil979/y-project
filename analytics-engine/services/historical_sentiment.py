"""Point-in-time historical sentiment lookup for offline MarketMind datasets.

The live sentiment endpoint is intentionally not used while constructing
historical rows.  A live response contains articles from the present and would
therefore leak future information into older observations.  This module reads
an explicitly dated, pre-computed sentiment file and only returns information
published on or before the observation date.

Supported CSV columns:
    ticker,date,sentiment_score

``date`` may be a date or timestamp.  When multiple records are available for
one ticker/day, their scores are averaged after the point-in-time filter.
"""

import os
from typing import Optional

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {"ticker", "date", "sentiment_score"}


class HistoricalSentimentStore:
    """Load and query dated sentiment without allowing look-ahead."""

    def __init__(self, path: Optional[str] = None):
        self.path = path
        self._data = pd.DataFrame(columns=["ticker", "date", "sentiment_score"])
        if path and os.path.exists(path):
            self._data = self._load(path)

    @staticmethod
    def _load(path: str) -> pd.DataFrame:
        data = pd.read_csv(path)
        missing = REQUIRED_COLUMNS.difference(data.columns)
        if missing:
            raise ValueError(
                f"Historical sentiment file is missing required columns: {sorted(missing)}"
            )

        out = data[["ticker", "date", "sentiment_score"]].copy()
        out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
        out["date"] = pd.to_datetime(out["date"], errors="coerce", utc=True)
        out["sentiment_score"] = pd.to_numeric(out["sentiment_score"], errors="coerce")
        out = out.dropna(subset=["ticker", "date", "sentiment_score"])
        if out.empty:
            return out
        out["sentiment_score"] = out["sentiment_score"].clip(-1.0, 1.0)
        return out.sort_values(["ticker", "date"]).reset_index(drop=True)

    @property
    def available(self) -> bool:
        return not self._data.empty

    def score_as_of(self, ticker: str, observation_date, default: float = 0.0) -> float:
        """Return the mean score known by ``observation_date`` only."""
        if self._data.empty:
            return float(default)
        ticker_key = str(ticker).upper().strip()
        cutoff = pd.Timestamp(observation_date)
        if cutoff.tzinfo is None:
            cutoff = cutoff.tz_localize("UTC")
        else:
            cutoff = cutoff.tz_convert("UTC")
        eligible = self._data[
            (self._data["ticker"] == ticker_key) & (self._data["date"] <= cutoff)
        ]
        if eligible.empty:
            return float(default)
        return float(np.clip(eligible["sentiment_score"].mean(), -1.0, 1.0))
