"""Dated AMC factsheet extracts. Weights and fees here are percentage points."""
from itertools import combinations
import re

QUANT = 'https://quantmutual.com/Admin/Factsheet/quant_Factsheet_-_November_2026.pdf'
DISCLOSURES = {
    'quant small cap fund': ('2026-10-31', QUANT, {'direct': .99, 'regular': 1.74},
        {'HFCL':6.54, 'RBLBANK':4.38, 'ADANIENT':4.08, 'ADANIPOWER':3.58,
         'SONACOMS':3.51, 'Jio Platforms':3.05, 'AEGISLOG':2.93, 'ADANIGREEN':2.79,
         'SUNTV':2.63, 'PIRAMALFIN':2.60}),
    'quant flexi cap fund': ('2026-10-31', QUANT, {},
        {'BHARTIARTL':9.35, 'MOTHERSON':9.08, 'AUROPHARMA':8.23, 'ADANIPOWER':7.58,
         'ADANIENT':7.30, 'ICICIAMC':6.22, 'ADANIENSOL':4.30, 'SONACOMS':4.14,
         'ADANIGREEN':3.81, 'GLENMARK':3.46}),
    'nippon india small cap fund': ('2026-05-31',
        'https://mf.nipponindiaim.com/FundsAndPerformance/ProductNotes/NipponIndia-Small-Cap-Fund-May-2026.pdf',
        {}, {'BHEL':1.93, 'HDFCBANK':1.77, 'TDPOWERSYS':1.71, 'MCX':1.57, 'APARINDS':1.55,
             'SBIN':1.29, 'NLCINDIA':1.26, 'KARURVYSYA':1.23, 'ZYDUSWELL':1.17, 'TIINDIA':1.05}),
}


def disclosure_for(scheme):
    normalized = ' '.join(scheme.lower().split())
    for name, (date, source, fees, holdings) in DISCLOSURES.items():
        if re.match(re.escape(name) + r'(?:\s*-|$|\s+(?:direct|regular|growth)\b)', normalized):
            plan = next((p for p in fees if re.search(r'\b'+p+r'\b', normalized)), None)
            return {'as_of':date, 'source':source, 'expense_ratio_pct':fees.get(plan), 'holdings_pct':holdings}
    return None


def disclosed_overlaps(funds):
    result = []
    for a, b in combinations(funds, 2):
        x, y = a['disclosure'], b['disclosure']
        if not x or not y or x['as_of'] != y['as_of']:
            continue
        left, right = x['holdings_pct'], y['holdings_pct']
        shared = sorted(left.keys() & right.keys())
        result.append({'first':a['name'], 'second':b['name'], 'as_of':x['as_of'],
                       'shared':shared, 'minimum_pct':sum(min(left[k], right[k]) for k in shared)})
    return result
