# App verification checkpoint — 2026-10-09

## Verified

- Frontend: `npm.cmd test` — 39 tests passed; `npm.cmd run build` succeeded. Build reports a JavaScript chunk above 500 kB.
- Backend: `venv\Scripts\python.exe -m pytest tests/test_midterm_pipeline.py tests/test_portfolio_analytics_contract.py tests/test_regime_study.py -q -p no:cacheprovider` — 26 tests passed.
- Installed the missing pytest runner into the existing backend virtual environment. No application source changes were required for these checks.
- Fresh frontend and FastAPI startup succeeded. Frontend HTTP returned 200.
- Research endpoint returned `status: ready`, saved metrics and equity data. It also returned `stale: true`: `services/regime_allocation.py` differs from the recorded source hash. Preserve the historical artifacts; a separately named reproduction is needed before claiming the current implementation reproduces them.
- Live quote checks outside the sandbox returned an AAPL USD quote and a RELIANCE.NS INR quote with daily-session dates and retrieval times. An invalid symbol returned `invalid_symbol` without suppressing valid quotes.
- The sandboxed backend returned structured `provider_unavailable` errors. The same request succeeded outside the sandbox, identifying access restrictions as the cause of that failure.

## Still pending

No browser was available through the Browser runtime (discovery returned an empty list). Consequently, these checks are **not** a completed browser acceptance test.

Connect a browser and verify onboarding/login, empty portfolio, one holding, five INR holdings, mixed currencies, transactions and oversell rejection, quote refresh, missing-price/outage messages, account persistence after reload, Research rendering and responsive layout. Capture visual evidence/demo recording. Existing automated tests cover several underlying contracts, but do not establish that these UI interactions work.

## Resume

Frontend: http://localhost:5173

Backend: http://localhost:8000

The services were started for this verification session; restart them if they are no longer running. Browser testing remains the next task.
