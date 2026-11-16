# Current-code reproduction — October 12, 2026

Replayed the frozen study on its archived input, without changing the original output or retuning parameters:

```powershell
venv\Scripts\python.exe -m research.run_regime_study --prices research/regime_holdout_2026-09-27_v2/prices.csv --output research/regime_reproduction_2026-10-12
```

The output directory now exists. For another replay, choose a new directory instead of replacing this run.

`services/regime_allocation.py` was the only tracked study-source hash that differed from the original manifest. The current-code replay yielded zero numeric difference in metrics, holdout metrics, 1,471 equity rows, 5,880 ledger rows and 24 sensitivity rows. Configuration, input snapshot hash and bootstrap JSON also matched. See `regime_reproduction_2026-10-12/reproduction_check.json` and `manifest.json`.

The API now serves this replay and checks its current source and snapshot hashes. The original `regime_holdout_2026-09-27_v2` is preserved. This is a reproduction of already-inspected data, not a newly held-out evaluation. It does not remove the convergence, universe, cost-model or statistical limitations documented in `PROTOCOL_V1.md`.
