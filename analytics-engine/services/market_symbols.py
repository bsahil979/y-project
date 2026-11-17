"""Verified broker-to-market-data aliases; never strip arbitrary security suffixes."""
# NSE BE is a trading series. HFCL's Yahoo listing is HFCL.NS.
# Keep original ledger symbols and map only provider requests.
_ALIASES = {"HFCL-BE.NS": "HFCL.NS"}


def market_data_symbol(symbol):
    normalized = str(symbol).strip().upper()
    return _ALIASES.get(normalized, normalized)
