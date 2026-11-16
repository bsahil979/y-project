"""Experiment B: shared MarketMind MLP with categorical embeddings.

This module is intentionally separate from ``trading_engine.meta_model``.
Experiment A remains the frozen scikit-learn control.  Experiment B consumes
the same engineered numeric columns, labels, and chronological split; the only
new inputs are normalized ticker, market, and sector IDs.
"""

import json
import os
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, Mapping, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import Dataset
from torch.utils.data import DataLoader


CLASS_TO_INDEX = {-1: 0, 0: 1, 1: 2}
INDEX_TO_CLASS = {value: key for key, value in CLASS_TO_INDEX.items()}
UNK_TOKEN = "__UNK__"


def normalize_ticker(value) -> str:
    return str(value).upper().strip()


def default_market(ticker: str) -> str:
    return "India" if normalize_ticker(ticker).endswith(".NS") else "US"


def load_ticker_metadata(path: Optional[str] = None) -> pd.DataFrame:
    """Load authoritative static ticker metadata (not inferred from prices)."""
    path = path or os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "ticker_metadata.csv")
    metadata = pd.read_csv(path, dtype=str)
    required = {"ticker", "market", "sector"}
    missing = sorted(required.difference(metadata.columns))
    if missing:
        raise ValueError(f"Ticker metadata is missing columns: {missing}")
    metadata = metadata[["ticker", "market", "sector"]].copy()
    for column in metadata.columns:
        metadata[column] = metadata[column].fillna("").astype(str).str.strip()
    metadata["ticker"] = metadata["ticker"].map(normalize_ticker)
    if metadata.duplicated("ticker").any() or (metadata[["ticker", "market", "sector"]] == "").any().any():
        raise ValueError("Ticker metadata must contain unique tickers and non-empty values.")
    return metadata


def attach_ticker_metadata(dataset: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    """Join metadata by ticker and fail closed when any dataset ticker is absent."""
    if "ticker" not in dataset.columns:
        raise ValueError("Dataset requires a ticker column.")
    result = dataset.copy()
    result["ticker"] = result["ticker"].map(normalize_ticker)
    metadata = metadata.copy()
    metadata["ticker"] = metadata["ticker"].map(normalize_ticker)
    unknown = sorted(set(result["ticker"]) - set(metadata["ticker"]))
    if unknown:
        raise ValueError(f"Missing authoritative metadata for tickers: {unknown}")
    result = result.drop(columns=["market", "sector"], errors="ignore").merge(metadata, on="ticker", how="left", validate="many_to_one")
    return result


def validate_metadata_coverage(dataset: pd.DataFrame, metadata: pd.DataFrame) -> None:
    """Validate coverage without mutating the dataset."""
    attach_ticker_metadata(dataset, metadata)


def chronological_split(dataset: pd.DataFrame, test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split on unique dates, matching Experiment A's final-block split."""
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1.")
    dates = pd.to_datetime(dataset["Date"], errors="coerce")
    if dates.isna().any() or not dates.is_monotonic_increasing:
        raise ValueError("Dataset must have valid dates in chronological order.")
    unique_dates = dates.drop_duplicates().reset_index(drop=True)
    split_date_index = int(len(unique_dates) * (1 - test_size))
    if split_date_index < 1 or split_date_index >= len(unique_dates):
        raise ValueError("Dataset does not contain enough dates for the requested test_size.")
    split_date = unique_dates.iloc[split_date_index]
    return dataset.loc[dates < split_date].copy(), dataset.loc[dates >= split_date].copy()


def _mapping(values: Iterable[str]) -> Dict[str, int]:
    categories = sorted({str(value).strip() for value in values if str(value).strip()})
    return {UNK_TOKEN: 0, **{value: index for index, value in enumerate(categories, start=1)}}


@dataclass
class MarketMindMappings:
    ticker_to_index: Dict[str, int]
    market_to_index: Dict[str, int]
    sector_to_index: Dict[str, int]

    @classmethod
    def fit(cls, dataset: pd.DataFrame) -> "MarketMindMappings":
        if "ticker" not in dataset.columns:
            raise ValueError("Dataset requires a ticker column.")
        tickers = dataset["ticker"].map(normalize_ticker)
        if "market" not in dataset.columns or "sector" not in dataset.columns:
            raise ValueError("Experiment B requires authoritative market and sector columns.")
        markets = dataset["market"]
        sectors = dataset["sector"]
        return cls(_mapping(tickers), _mapping(markets), _mapping(sectors))

    def encode(self, dataset: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        tickers = dataset["ticker"].map(normalize_ticker)
        if "market" not in dataset.columns or "sector" not in dataset.columns:
            raise ValueError("Experiment B requires authoritative market and sector columns.")
        markets = dataset["market"]
        sectors = dataset["sector"]
        return (
            tickers.map(lambda value: self.ticker_to_index.get(value, 0)).to_numpy(dtype=np.int64),
            markets.map(lambda value: self.market_to_index.get(str(value).strip(), 0)).to_numpy(dtype=np.int64),
            sectors.map(lambda value: self.sector_to_index.get(str(value).strip(), 0)).to_numpy(dtype=np.int64),
        )

    def save(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        for name, values in asdict(self).items():
            with open(os.path.join(directory, f"{name}.json"), "w", encoding="utf-8") as file:
                json.dump(values, file, indent=2, sort_keys=True)

    @classmethod
    def load(cls, directory: str) -> "MarketMindMappings":
        values = {}
        for name in ("ticker_to_index", "market_to_index", "sector_to_index"):
            with open(os.path.join(directory, f"{name}.json"), "r", encoding="utf-8") as file:
                values[name] = {str(key): int(value) for key, value in json.load(file).items()}
        return cls(**values)


class MarketMindDataset(Dataset):
    """Tensor dataset keeping numeric and categorical inputs separate."""

    def __init__(self, frame: pd.DataFrame, feature_columns: Iterable[str], mappings: MarketMindMappings,
                 numeric_fill_values: Optional[Mapping[str, float]] = None):
        features = list(feature_columns)
        missing = [column for column in [*features, "ticker", "target"] if column not in frame.columns]
        if missing:
            raise ValueError(f"Dataset is missing required columns: {missing}")
        numeric_frame = frame[features].replace([np.inf, -np.inf], np.nan)
        if numeric_fill_values is None:
            numeric_fill_values = {feature: 0.0 for feature in features}
        numeric = numeric_frame.fillna(pd.Series(numeric_fill_values)).fillna(0.0).to_numpy(dtype=np.float32)
        ticker_ids, market_ids, sector_ids = mappings.encode(frame)
        targets = frame["target"].astype(int).map(CLASS_TO_INDEX)
        if targets.isna().any():
            raise ValueError("Targets must contain only -1, 0, and 1 labels.")
        self.numeric = torch.as_tensor(numeric, dtype=torch.float32)
        self.ticker_id = torch.as_tensor(ticker_ids, dtype=torch.long)
        self.market_id = torch.as_tensor(market_ids, dtype=torch.long)
        self.sector_id = torch.as_tensor(sector_ids, dtype=torch.long)
        self.target = torch.as_tensor(targets.to_numpy(), dtype=torch.long)

    def __len__(self):
        return len(self.target)

    def __getitem__(self, index):
        return {
            "numeric": self.numeric[index],
            "ticker_id": self.ticker_id[index],
            "market_id": self.market_id[index],
            "sector_id": self.sector_id[index],
            "target": self.target[index],
        }


class MarketMindMLP(nn.Module):
    def __init__(self, numeric_features: int, ticker_count: int, market_count: int, sector_count: int,
                 ticker_embedding_dim: int = 16, market_embedding_dim: int = 4,
                 sector_embedding_dim: int = 8):
        super().__init__()
        self.ticker_embedding = nn.Embedding(ticker_count, ticker_embedding_dim)
        self.market_embedding = nn.Embedding(market_count, market_embedding_dim)
        self.sector_embedding = nn.Embedding(sector_count, sector_embedding_dim)
        self.backbone = nn.Sequential(nn.Linear(numeric_features, 128), nn.ReLU(), nn.Linear(128, 64), nn.ReLU())
        fusion_size = 64 + ticker_embedding_dim + market_embedding_dim + sector_embedding_dim
        self.fusion = nn.Sequential(nn.Linear(fusion_size, 128), nn.ReLU(), nn.Linear(128, 64), nn.ReLU())
        self.classifier = nn.Linear(64, 3)

    def forward(self, numeric, ticker_id, market_id, sector_id):
        fused = torch.cat((self.backbone(numeric), self.ticker_embedding(ticker_id),
                           self.market_embedding(market_id), self.sector_embedding(sector_id)), dim=1)
        return self.classifier(self.fusion(fused))


def predict_probabilities(model: MarketMindMLP, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
    """Return inference probabilities; the model itself always returns logits."""
    model.eval()
    with torch.no_grad():
        logits = model(batch["numeric"], batch["ticker_id"], batch["market_id"], batch["sector_id"])
        return torch.softmax(logits, dim=-1)


def save_experiment_b(directory: str, model: MarketMindMLP, mappings: MarketMindMappings,
                      feature_columns: Iterable[str], config: Optional[Mapping] = None) -> None:
    os.makedirs(directory, exist_ok=True)
    torch.save(model.state_dict(), os.path.join(directory, "marketmind_b.pt"))
    mappings.save(directory)
    with open(os.path.join(directory, "feature_columns.json"), "w", encoding="utf-8") as file:
        json.dump(list(feature_columns), file, indent=2)
    with open(os.path.join(directory, "model_config.json"), "w", encoding="utf-8") as file:
        json.dump(dict(config or {}), file, indent=2)


def train_experiment_b(dataset: pd.DataFrame, feature_columns: Iterable[str], output_directory: str,
                       test_size: float = 0.2, epochs: int = 25, batch_size: int = 256,
                       learning_rate: float = 1e-3, seed: int = 42) -> dict:
    """Train and persist Experiment B using the frozen Experiment A split.

    Mappings are deliberately fitted on the training window.  A category first
    appearing in the test window therefore uses the reserved unknown ID rather
    than changing the model vocabulary after fitting.
    """
    if epochs < 1 or batch_size < 1:
        raise ValueError("epochs and batch_size must be positive.")
    torch.manual_seed(seed)
    np.random.seed(seed)
    features = list(feature_columns)
    train_frame, test_frame = chronological_split(dataset, test_size=test_size)
    mappings = MarketMindMappings.fit(train_frame)
    train_fill_values = (train_frame[features].replace([np.inf, -np.inf], np.nan)
                         .median().fillna(0.0).to_dict())
    train_data = MarketMindDataset(train_frame, features, mappings, train_fill_values)
    test_data = MarketMindDataset(test_frame, features, mappings, train_fill_values)
    model = MarketMindMLP(len(features), len(mappings.ticker_to_index),
                          len(mappings.market_to_index), len(mappings.sector_to_index))
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.CrossEntropyLoss()
    loader = DataLoader(train_data, batch_size=batch_size, shuffle=True)
    model.train()
    for _ in range(epochs):
        for batch in loader:
            optimizer.zero_grad()
            logits = model(batch["numeric"], batch["ticker_id"], batch["market_id"], batch["sector_id"])
            loss = criterion(logits, batch["target"])
            loss.backward()
            optimizer.step()

    model.eval()
    with torch.no_grad():
        logits = model(test_data.numeric, test_data.ticker_id, test_data.market_id, test_data.sector_id)
        predictions = logits.argmax(dim=1).cpu().numpy()
    actual = test_data.target.cpu().numpy()
    accuracy = float((predictions == actual).mean())
    # Avoid adding a new metrics dependency: calculate macro F1 directly.
    f1_values = []
    for class_id in range(3):
        true_positive = ((predictions == class_id) & (actual == class_id)).sum()
        false_positive = ((predictions == class_id) & (actual != class_id)).sum()
        false_negative = ((predictions != class_id) & (actual == class_id)).sum()
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1_values.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    metrics = {
        "accuracy": accuracy,
        "f1_macro": float(np.mean(f1_values)),
        "split": "chronological_final_block",
        "rows": int(len(dataset)),
        "test_size": test_size,
        "date_range": {"train_end": str(train_frame["Date"].iloc[-1]),
                       "test_start": str(test_frame["Date"].iloc[0])},
    }
    config = {
        "experiment": "B",
        "architecture": "MLP_with_embeddings",
        "numeric_features": len(features),
        "ticker_count": len(mappings.ticker_to_index),
        "market_count": len(mappings.market_to_index),
        "sector_count": len(mappings.sector_to_index),
        "ticker_embedding_dim": 16,
        "market_embedding_dim": 4,
        "sector_embedding_dim": 8,
        "hidden_layers": [128, 64],
        "class_to_index": {str(key): value for key, value in CLASS_TO_INDEX.items()},
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "seed": seed,
        "dataset_split": "chronological_final_block",
        "numeric_imputation": {str(key): float(value) for key, value in train_fill_values.items()},
        "metadata_source": "config/ticker_metadata.csv",
        "metrics": metrics,
    }
    save_experiment_b(output_directory, model, mappings, features, config)
    return {"model": model, "mappings": mappings, "metrics": metrics, "config": config}