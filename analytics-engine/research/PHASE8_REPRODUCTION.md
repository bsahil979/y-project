# Reproducing Phase 8

Run from analytics-engine with the project virtual environment:

```powershell
.\venv\Scripts\python.exe -m research.personalized_study
```

The runner refuses to overwrite a completed study. For an independent reproduction, supply a new directory through the module's output variable:

```powershell
.\venv\Scripts\python.exe -c "from pathlib import Path; import research.personalized_study as s; s.OUTPUT = Path('research/phase8_reproduction'); s.main()"
```

The protocol is `PHASE8_PROTOCOL.md`. No market/news download is required. The frozen HMM prices and ledger plus `models/meta_model/meta_dataset.csv` must be present. The latter supplies only historical ADX; it supplies no stored targets, sentiment, predictions or regime codes to the study. The cached causal features contain separate future labels solely for training after their maturity dates; they are never predictor columns.

The production classifier artifacts are not modified. The study retrains a separate 250-tree RF each rebalance. Output files preserve label cutoffs, all 70 decision sets, views, weights, daily ledger and paired uncertainty results. The serving layer checks hashes and marks changed inputs/sources stale; output corruption fails closed.

The frozen result directory additionally includes a human-readable report derived from the JSON. Its hash and runtime versions were recorded after the computation. Full-precision JSON/CSV are the authoritative numerical records.
