# Test discovery and manual diagnostics

Run `python -m pytest` from the project root or analytics-engine. Both configurations collect the complete maintained `analytics-engine/tests` suite. No maintained tests are excluded.

Three obsolete standalone scripts are intentionally outside pytest discovery:

- `test_recs.py`: live-data portfolio-intelligence demonstration; executes at import and assumes scalar metrics from an older API.
- `training/test_fx_quote.py`: live Yahoo quote probe with an obsolete `fetch_market_quotes` import.
- `training/test_recs_output.py`: example for an older recommendation keyword contract.

These are archived manual diagnostics, not passing automated tests. They are retained for traceability and must not be used as validation commands. Current offline coverage is in `tests/test_midterm_pipeline.py`, `tests/test_stress_fx.py`, and the recommendation/profile integration tests. Other root scripts such as `test_e2e_pipeline.py` require a running service and are also manual diagnostics. Pytest configuration avoids network requests and side effects from importing these scripts.
