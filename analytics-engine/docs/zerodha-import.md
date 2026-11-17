# Zerodha portfolio import

Set ZERODHA_CLIENT_ID (the Kite developer API key), ZERODHA_CLIENT_SECRET, and
ZERODHA_REDIRECT_URI in the backend .env only. Shared SUPABASE_URL,
SUPABASE_ANON_KEY, and FRONTEND_ORIGIN must also be configured.
Register http://127.0.0.1:8000/brokers/zerodha/callback as the redirect URL
in the Kite developer console for local use, then restart the backend.

Choose Add account > Zerodha > Connect Zerodha. After authorization, Fetch
portfolio, review the holdings, and Confirm import. Each app user has a separate
broker session. Tokens are held in server memory; restarting requires reconnecting.
This connector retrieves data only; it never places orders.

Equities and Coin mutual funds are importable. Positions, SIPs, recent fund orders
(last seven days), and margins are reference data only, avoiding double counting.
Missing fund NAV dates are resolved from the public AMFI publication when possible;
unresolved funds are reported in preview warnings, never given invented dates.
Existing account labels reject duplicate imports; automatic refresh/upsert is not implemented.

Kite login sends an expiring, single-use state through redirect_params. The backend
exchanges the request token using a SHA-256 checksum. Neither token nor API secret
is returned to the browser. Do not log callback query strings in production proxies.

Official documentation: https://kite.trade/docs/connect/v3/user/
https://kite.trade/docs/connect/v3/portfolio/
https://kite.trade/docs/connect/v3/mutual-funds/
