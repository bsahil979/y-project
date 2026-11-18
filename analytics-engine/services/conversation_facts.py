"""Request-local chat facts. Compute totals before context compaction."""
import math
import re


def number(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def conversation_facts(context):
    currency = context.get('currency')
    holdings = [r for r in context.get('holdings', []) if r.get('currency') == currency]
    assets = [r for r in context.get('tracked_assets', []) if r.get('currency') == currency]
    def total(rows, key):
        values = [number(r.get(key)) for r in rows]
        return round(sum(values), 2) if all(v is not None for v in values) else None
    totals = {'stocks': total(holdings, 'market_value')}
    for kind in ('mutual_fund', 'cash', 'real_estate', 'private_equity', 'other', 'liability'):
        totals[kind] = total([r for r in assets if r.get('type') == kind], 'recorded_value')
    totals['net_worth'] = (round(sum(totals.values()), 2)
                           if all(v is not None for v in totals.values()) else None)
    allocation = (context.get('available_analysis') or {}).get('personalized_allocation') or {}
    return {'currency': currency, 'totals': totals,
            'stock_count': len(holdings), 'tracked_asset_count': len(assets),
            'allocation_available': bool(allocation.get('success') and allocation.get('weights')),
            'fund_names': list(dict.fromkeys(str(r.get('name', '')) for r in assets if r.get('type') == 'mutual_fund'))}


def unsupported_money(reply, context, facts):
    """Fail closed on unsupported currency amounts; not a general truth checker."""
    allowed = [v for v in facts['totals'].values() if v is not None]
    for row in context.get('holdings', []):
        if row.get('currency') == facts['currency']:
            allowed.extend(v for k in ('market_value', 'average_cost') if (v := number(row.get(k))) is not None)
    for row in context.get('tracked_assets', []):
        if row.get('currency') == facts['currency'] and (v := number(row.get('recorded_value'))) is not None:
            allowed.append(v)
    pattern = r'(₹|\$|INR\s*|USD\s*)\s*([-+]?\d[\d,]*(?:\.\d+)?)\s*(thousand|million|crore|lakh|[kKmM]\b)?'
    for match in re.finditer(pattern, reply):
        currency = 'INR' if match[1].strip() in ('₹', 'INR') else 'USD'
        scale = {'k': 1000, 'thousand': 1000, 'm': 1000000, 'million': 1000000, 'lakh': 100000, 'crore': 10000000}.get((match[3] or '').lower(), 1)
        value = float(match[2].replace(',', '')) * scale
        if currency != facts['currency'] or not any(abs(value - v) <= .51 for v in allowed):
            return True
    return False


def factual_summary(facts):
    currency = facts.get('currency') or 'Selected currency'
    lines = ['Here are the recorded figures for your selected portfolio:']
    for key, label in [('stocks', 'Stocks'), ('mutual_fund', 'Mutual funds'), ('cash', 'Cash'), ('net_worth', 'Net worth')]:
        value = facts['totals'][key]
        lines.append(f'- {label}: {currency} {value:,.2f}' if value is not None else f'- {label}: unavailable (incomplete prices or valuations).')
    if any('small cap' in name.lower().replace('-', ' ') for name in facts['fund_names']):
        lines.append('Your fund names include small-cap funds. Multiple funds can share similar exposures; their names alone do not establish diversification.')
    lines.append('These totals combine stock market values and dated asset valuations; they are not a measure of today’s return.')
    return '\n\n'.join(lines)
