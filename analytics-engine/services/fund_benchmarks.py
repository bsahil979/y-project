"""Matched-date growth NAV versus verified scheme TRI benchmarks."""
import json
import math
import re

import pandas as pd
import requests
from services.fund_disclosures import DISCLOSURES


# Scheme mandates from the Nippon India Small Cap product note and quant's
# scheme returns disclosure. Never infer an index from a similar category.
BENCHMARKS = {
    'nippon india small cap fund': 'NIFTY SMALLCAP 250',
    'quant small cap fund': 'NIFTY SMALLCAP 250',
    'quant mid cap fund': 'NIFTY MIDCAP 150',
    'quant flexi cap fund': 'NIFTY 500',
    'quant large cap fund': 'NIFTY 100',
}
SOURCE = 'https://www.niftyindices.com/reports/historical-data'


def index_history(name, start, end):
    fields = dict(name=name, indexName=name, startDate=start.strftime('%d-%b-%Y'),
                  endDate=end.strftime('%d-%b-%Y'))
    reply = requests.post('https://www.niftyindices.com/Backpage.aspx/getTotalReturnIndexString',
                          json={'cinfo': str(fields)}, headers={'Referer': SOURCE,
                          'X-Requested-With': 'XMLHttpRequest'}, timeout=8)
    reply.raise_for_status()
    values = {}
    for row in json.loads(reply.json()['d']):
        if row['Index Name'].strip().upper() != name:
            continue
        level = float(row['TotalReturnsIndex'])
        if math.isfinite(level) and level > 0:
            values[pd.to_datetime(row['Date'], dayfirst=True)] = level
    return pd.Series(values, dtype=float).sort_index()


def compare_benchmark(scheme, nav, cache):
    normalized = ' '.join(scheme.lower().split())
    name = next((index for fund, index in BENCHMARKS.items()
                 if re.match(re.escape(fund) + r'(?:\s*-|$|\s+(?:direct|regular|growth)\b)', normalized)), None)
    if not name:
        return {'reason': 'Verified scheme benchmark unavailable'}
    if 'growth' not in normalized or 'idcw' in normalized or 'dividend' in normalized:
        return {'reason': 'Total-return comparison requires a growth plan'}
    key = (name, nav.index[0], nav.index[-1])
    if key not in cache:
        try:
            cache[key] = index_history(*key)
        except (requests.RequestException, KeyError, TypeError, ValueError, AttributeError):
            cache[key] = pd.Series(dtype=float)
    matched = pd.concat([nav, cache[key]], axis=1, join='inner').dropna().sort_index()
    if len(matched) < 61:
        published = {
            'quant small cap fund': ('2026-10-30', 4.79, 3.91, -2.61),
            'nippon india small cap fund': ('2026-05-29', 5.31, 4.52, 1.53),
        }
        for scheme_name, (date, direct, regular, index_pct) in published.items():
            if not normalized.startswith(scheme_name) or pd.Timestamp(date) > nav.index[-1]:
                continue
            plan = re.search(r'\b(direct|regular)\b', normalized)
            if plan:
                fund_pct = direct if plan[1] == 'direct' else regular
                return {'name':name+' TRI', 'source':DISCLOSURES[scheme_name][1],
                        'period_label':'Published one-year return ending '+date,
                        'fund_return':fund_pct/100, 'index_return':index_pct/100,
                        'difference':(fund_pct-index_pct)/100}
        return {'name':name+' TRI', 'reason':'Insufficient matching NAV and index dates'}
    fund, index = (matched.iloc[-1] / matched.iloc[0] - 1).tolist()
    return {'name':name+' TRI', 'source':SOURCE, 'fund_return':fund, 'index_return':index,
            'difference':fund-index, 'start':str(matched.index[0].date()),
            'end':str(matched.index[-1].date()), 'observations':len(matched)}
