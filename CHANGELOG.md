# SmartPortfolio changelog

## Unreleased

### Features

- Connect Zerodha to preview and import equity and Coin mutual fund holdings. Review positions, SIPs, recent fund orders and margins separately. If a fund lacks a dated NAV, the importer checks the AMFI publication. [Zerodha setup and import guide](analytics-engine/docs/zerodha-import.md)
- Import broker holdings into the selected portfolio by default. Use **Combine all into My Portfolio** to bring previously separate portfolios together while retaining broker accounts, manual holdings and transaction history.

### Fixes

- Recognize a Zerodha authorization response sent to the older Upstox callback URL. The Zerodha handler still checks the signed-in user's single-use authorization state.
- Look up `HFCL-BE.NS` as `HFCL.NS` for quotes and historical analysis while preserving the original symbol in the ledger.
- Wait for the signed-in user's workspace to load before enabling edits. Queue that user's saves in order, preserve the local snapshot after a partial cloud read and limit deletion to previously known records removed locally.
- Keep financial goals associated with the user when combining portfolios. Retrying a pending save removes the unsupported `portfolio_id` field from goal records.
- Keep saved holdings visible during analysis and show a retry message for an outdated result or a two-minute wait. Track requests core analytics. Advisor also requests optional AI models.

### UI changes

- The Track dashboard uses locally bundled Inter, a 256-pixel desktop sidebar, searchable navigation and a portfolio pulse panel beside the holdings chart.
- Heatmap tile area represents market value. Green and red show unrealized gains and losses against recorded purchase cost. Hovering reveals the holding's weight, value and return. Gray indicates unavailable performance.

### Validation results

- 82 frontend tests passed and the production build succeeded after the dashboard changes.
- 27 targeted broker tests passed after the callback fix, including account isolation and rejection of reused authorization states.
- Three quote and historical-price regression tests passed. A live quote request also resolved the imported HFCL symbol.
- A live sign-out and sign-in check of the combined portfolio remains outstanding.

## Recent commits

### Features

- Added Upstox portfolio previews, CSV imports, mutual fund analysis using NAV history and tracking for manually valued assets. [2fcc018](https://github.com/bsahil979/y-project/commit/2fcc018)
- Added pinned runtime requirements and setup instructions for running the app on another PC. [c348153](https://github.com/bsahil979/y-project/commit/c348153)

### Fixes

- OAuth tests now generate temporary dummy credentials for each run. [adc80df](https://github.com/bsahil979/y-project/commit/adc80df)

### UI changes

- The sidebar distinguishes broker accounts from unassigned holdings. The advisor renders allocation tables, and portfolios containing only mutual funds have a holdings view. [2fcc018](https://github.com/bsahil979/y-project/commit/2fcc018)

### Validation results

- The broker-import update passed 24 targeted backend tests, 80 frontend tests and the production build. The subsequent OAuth fixture change passed all 18 Upstox tests.
