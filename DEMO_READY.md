# Working demo — October 12, 2026

## Start

Double-click `run_all.bat` from this folder, then open http://localhost:5173.
Keep the frontend and backend processes running during the demo. If they are already running, use the existing page instead of starting duplicate servers.

The backend uses `analytics-engine/venv/Scripts/python.exe`. The frontend stays on port 5173 and reports a conflict instead of silently selecting a different port. `START_BACKEND.bat` and `run_analytics.bat` use the same environment. Startup no longer installs backend dependencies on every launch.

## Demonstrate

1. Open the sign-in page and choose **Try Demo (Temporary Account)**. Cloud registration is not needed for this path.
2. Create a portfolio and add holdings. A useful INR example is RELIANCE.NS, TCS.NS, HDFCBANK.NS, INFY.NS and ITC.NS. Enter quantities and purchase costs as example data.
3. Show the portfolio value, price source/date and risk analysis. Internet access is required for current market data.
4. Add a sample buy transaction, then inspect the updated holding. A sale exceeding available inventory should be rejected.
5. Open Improvements to compare allocations, then Research to discuss the separate saved historical experiment.
6. Reload to check that the local demo workspace persists. Stay signed in until the demonstration ends; a new demo login creates a new identity.

## Verified this session

- 42 frontend tests passed, including three authentication regressions; production build succeeded.
- 28 backend tests passed for the core pipeline, analytics contract, research study and delivered reproduction.
- Fresh frontend startup returned HTTP 200; backend served live API requests.
- Live AAPL and RELIANCE.NS quotes returned USD and INR respectively, including source and session dates.
- A five-stock INR analysis returned SUCCESS for market data, risk, risk budget, benchmark, attribution, regime, stress test, optimization and recommendations. Regime allocation returned `ready`. The response is saved in `scripts/qa-portfolio-response.json` using synthetic portfolio inputs.
- Research returned `ready`, four holdout strategies and 1,471 equity rows.

## Changes made

- Fixed local login/registration response shapes so the auth page recognizes successful sessions.
- Cloud registration that requires email confirmation no longer claims the user is signed in. Regression tests use a mocked cloud client; real cloud account creation was not tested.
- Replaced misleading sign-in copy with instructions for the explicit demo path.
- Unified Windows backend launchers around the installed virtual environment and fixed frontend port selection.

## Remaining acceptance checks

Chrome browser acceptance was completed on October 12: demo login and onboarding, empty portfolio, five INR opening positions, live quote display, a two-share buy updating RELIANCE.NS from 10 to 12, rejection of a 999-share sell, reload persistence, portfolio analysis, Improvements and Research rendering. Adding two AAPL shares produced a separate USD total without combining currencies. Sample data remains in the open demo workspace.

A narrow viewport holdings check showed stacked navigation/content without document-level horizontal overflow. The desktop viewport was restored. Fixed dark gradient cards that were unreadable under the light theme and visually confirmed the corrected dashboard. Browser console inspection reported chart-sizing warnings, but no errors in the inspected messages.

Additional browser checks passed: an invalid ticker left valid quotes visible and the affected currency total unavailable; removing that sample restored totals. Stopping the backend produced the expected connection error and unavailable values, and restarting it plus refreshing restored live quotes. This checks backend disconnection, not every upstream provider or internet outage.

Still untested in the browser: real cloud sign-up/login and all optional tools. This is a core demo acceptance check, not exhaustive product QA.

The Research page now serves `regime_reproduction_2026-10-12`, a verified replay from the same saved prices. All compared numeric results matched the original; the API reports `stale: false`. Original artifacts are preserved. This is not a new independent holdout. See `analytics-engine/research/REPRODUCTION_2026-10-12.md`.

Presentation cleanup removed invented testimonials and usage statistics, labeled the illustrative preview and standardized the name to SmartPortfolio. Rehearse with `DEMO_SCRIPT.md`. A new backup video remains to be recorded manually.

The frontend build reports a bundle over 500 kB. This is a performance warning, not a build failure.
