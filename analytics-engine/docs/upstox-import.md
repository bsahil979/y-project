# Brokerage import

Manage holdings includes Add account / Import portfolio. CSV uploads are parsed locally and previewed before confirmation. Supported formats are comma-separated holdings and complete buy/sell history, with the displayed column headings. XLSX and PDF require conversion to CSV. A real exported Upstox statement has not yet been validated.

Each confirmed import creates a named portfolio snapshot and brokerage account. Identical record sets are rejected across existing portfolios. Snapshot imports and trade-history imports are separate portfolios. Existing manually entered holdings should be reconciled by the user before treating them as a combined investment total. Snapshot updates cannot establish historical sale prices or dates.

Upstox setup uses server environment variables in .env.example. Create a developer app and register the callback URL exactly. Configure Supabase server URL and anon key for the same project used by the frontend. Cloud login is required. The browser sends its Supabase access token, which the backend validates against Supabase before any user-bound broker action.

Use Connect Upstox, authorize, then Fetch holdings and Confirm import. This version fetches long-term equity holdings on demand. Automatic recurring synchronization, broker quote valuation and historical Upstox trade API ingestion are future work. CSV supports buy/sell history. BSE holdings require numeric BSE symbols; unsupported instruments fail validation.

Upstox credentials and access tokens stay on the server. Connection tokens are stored only in process memory. Run one backend worker. Reconnect after restart or broker token expiration. OAuth states expire after ten minutes and are single-use. Disconnect clears local connection state. The integration calls authorization and holdings endpoints only. Upstox token permissions themselves depend on the broker.

Live authorization requires configured credentials and user consent and has not been exercised here. For deployment, use HTTPS callback and frontend URLs, disable callback query access logging, and implement encrypted persistent token storage before enabling multiple workers.

Official references
- https://upstox.com/developer/api-documentation/authentication/
- https://upstox.com/developer/api-documentation/get-holdings/

## Expanded read-only portfolio import

Fetch portfolio now requests equity holdings, mutual fund holdings, short-term positions, MTF positions, mutual fund SIPs, mutual fund orders, and funds/margin. SIP and order pagination is followed (maximum 100 pages, explicitly marked partial if exceeded). Each section reports unavailable separately from an empty result. MF routes require Upstox subscription access.

Equity and mutual fund holdings can be confirmed into a portfolio snapshot. Funds use their ISIN, units, average cost, broker NAV and actual NAV date. Multiple folios in the same scheme are aggregated with weighted average cost; duplicate folio rows and incomplete valuations are reported rather than silently accepted. AMFI NAV refresh accepts an ISIN or scheme code. Existing multi_asset_schema.sql columns are required for cloud NAV persistence.

Positions, MTF loans/exposure, SIP registrations, orders and trading margin are read-only reference views in the import dialog, not saved as additional owned holdings or cash. This prevents double counting and avoids treating margin availability as net worth. These reference views are fetched on demand, not persisted. Mutual funds are included in tracked net worth; the stock risk/forecast optimization pipeline still excludes funds. Automated synchronization, a complete historical transaction ledger and fund risk optimization are not implemented.

API references: https://upstox.com/developer/api-documentation/mutual-fund/ and https://upstox.com/developer/api-documentation/get-mutual-fund-holdings/
