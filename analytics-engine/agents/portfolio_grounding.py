"""Numerical grounding for labeled portfolio metrics. Rates and weights are fractions."""
import math
import re
from decimal import Decimal


RISK_KEYS = {
    'cagr': 'portfolio_annualized_return', 'annualized_volatility': 'portfolio_volatility',
    'sharpe_ratio': 'portfolio_sharpe', 'sortino_ratio': 'portfolio_sortino',
    'max_drawdown': 'portfolio_max_drawdown', 'var_95': 'portfolio_var_95',
    'cvar_95': 'portfolio_cvar_95',
}
RATE_KEYS = set(RISK_KEYS) - {'sharpe_ratio', 'sortino_ratio'}
WEIGHTS = ('current_weights', 'personalized_allocation', 'ai_black_litterman_allocation')


def canonical_portfolio_facts(analysis):
    def number(value):
        return float(value) if isinstance(value, (float, int)) and math.isfinite(value) else None

    risk = analysis.get('portfolio_risk') or {}
    facts = {key: number(risk.get(source)) for key, source in RISK_KEYS.items()}
    facts.update(portfolio_health_score=number((analysis.get('portfolio_score') or {}).get('score')),
                 base_currency=analysis.get('base_currency') or analysis.get('currency'),
                 hmm_regime=(analysis.get('market_regime') or {}).get('current_regime'))
    facts['current_weights'] = {ticker: number(weight) for ticker, weight in
                                zip(analysis.get('tickers', []), analysis.get('weights', []))}
    for key in WEIGHTS[1:]:
        allocation = analysis.get(key) or {}
        facts[key] = {ticker: number(weight) for ticker, weight in allocation.get('weights', {}).items()} if allocation.get('success') else {}
    return facts


LABELS = {
    'cagr': r'CAGR|(?:compound |geometric )?annual(?:ized)? (?:growth rate|return)',
    'annualized_volatility': r'(?:annual(?:ized)? )?volatility',
    'sharpe_ratio': r'Sharpe(?: ratio)?', 'sortino_ratio': r'Sortino(?: ratio)?',
    'max_drawdown': r'max(?:imum)? drawdown',
    'cvar_95': r'(?:95%\s*)?(?:CVaR|conditional value.at.risk|expected shortfall)(?:\s*(?:at\s+)?\(?95%\)?)?',
    'var_95': r'(?:95%\s*)?(?:VaR|value.at.risk)(?:\s*(?:at\s+)?\(?95%\)?)?',
    'portfolio_health_score': r'(?:portfolio )?(?:health score|portfolio score|health rating)',
}
NUMBER = r'(?P<number>[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|[-+]?\.\d+)(?P<unit>\s*(?:%|percent\b))?'
LINK = r"(?:\s*(?:[:=|]|is|was|of|at|equals|stands at|accounts for|represents|makes up|has|with|about|approximately|around|~)\s*)*\s*"
METRIC = re.compile(r'\b(?:' + '|'.join(f'(?P<{k}>{v})' for k,v in LABELS.items()) + r')(?![A-Za-z_])(?!\s*(?:\(?\d+%\)?\s*)?(?:confidence|confidence level))' + LINK + NUMBER, re.I)
REVERSE = re.compile(NUMBER + r'\s+(?:annualized\s+)?(?P<label>volatility|maximum drawdown|max drawdown|CAGR|Sharpe ratio|Sortino ratio)\b',re.I)


def _scope(context):
    if re.search(r'black[\s_-]*litterman|\bAI\b', context, re.I):
        return 'ai_black_litterman_allocation'
    if re.search(r'personalized|target|recommended|suggested|optimal', context, re.I):
        return 'personalized_allocation'
    return 'current_weights'


def verify_explanation_numbers(response, canonical_facts, retrieval_method='tfidf_fallback'):
    """Check recognized labeled claims. Percentage tolerance is 0.5 percentage points."""
    checked, mismatches = [], []
    text = response.replace('**','').replace('`','').translate(str.maketrans({'\u2212': '-', '\u2011': '-', '\u2010': '-'}))
    def check(match, key, expected, percentage=False, ticker=None):
        value = Decimal(match['number'].replace(',',''))
        unit = bool(match['unit'])
        # A bare fraction is in engine units. A percent sign explicitly scales by 100.
        scale = Decimal(100) if percentage and unit else Decimal(1)
        exact = Decimal(str(expected)) * scale if expected is not None else None
        tolerance = Decimal('.005')*scale if percentage else Decimal(1 if key == 'portfolio_health_score' else '.02')
        valid = exact is not None and (percentage or not unit) and abs(value-exact) <= tolerance
        item = {'metric': key, 'claim': match.group().strip(), 'claimed': float(value),
                'expected': float(exact) if exact is not None else None, 'unit': '%' if unit else 'number',
                'matches': valid}
        if ticker:
            item['ticker'] = ticker
        checked.append(item)
        if not valid:
            label = key.replace('_',' ') + (' for '+ticker if ticker else '')
            formatted = format(exact.normalize(), 'f') + ('%' if percentage and unit else '') if exact is not None else 'unavailable in this portfolio snapshot'
            mismatches.append({**item, 'correction': f'{label}: {formatted}'})
    spans = []
    for match in METRIC.finditer(text):
        key = next(k for k in LABELS if match[k] is not None)
        check(match, key, canonical_facts.get(key), key in RATE_KEYS)
        spans.append(match.span())
    for match in REVERSE.finditer(text):
        if any(a < match.end() and b > match.start() for a,b in spans):
            continue
        key = next(k for k,v in LABELS.items() if re.fullmatch(v,match['label'],re.I))
        check(match,key,canonical_facts.get(key),key in RATE_KEYS)
    tickers = set().union(*(canonical_facts.get(k, {}) for k in WEIGHTS))
    known = '|'.join(re.escape(t) for t in sorted(tickers,key=len,reverse=True))
    # Unknown uppercase tickers require an explicit weight label.
    symbol = r'(?P<ticker>(?-i:[A-Z][A-Z0-9.-]{0,19}))'
    weight_word = r'(?:current |personalized |target |recommended |AI |Black[- ]Litterman )*(?:weight|allocation|holding)'
    patterns = [symbol + r"(?:['’]s)?\s+(?:(?:has|with)\s+a\s+)?(?:portfolio\s+)?" + weight_word + LINK + NUMBER,
                weight_word + r'\s+(?:of |for |in |to )?' + symbol + LINK + NUMBER]
    if known:
        patterns += [r'(?P<ticker>'+known+r')' + LINK + NUMBER + r'(?<=%)',
                     NUMBER + r'\s+(?:weight\s+)?(?:in|to|for|of)\s+(?P<ticker>'+known+r')']
    weight_spans = []
    for pattern in patterns:
        for match in re.finditer(r'(?<![\w.-])'+pattern,text,re.I):
            if any(a < match.end() and b > match.start() for a,b in spans+weight_spans):
                continue
            ticker = match['ticker'].upper()
            # Restrict allocation scope to this clause or its section heading.
            prefix = text[:match.start()]
            clause = re.split(r'[;.!?]\s+|,\s*|\n', prefix)[-1]
            local_context = clause+' '+match.group()
            scope = _scope(local_context)
            if not re.search(r'current|personalized|target|recommended|suggested|optimal|black[ -]*litterman|\bAI\b', local_context, re.I):
                headings = re.findall(r'(?m)^\s*(?:#{1,6}\s*)?((?:Current|Personalized|Target|Recommended|AI|Black[- ]Litterman)[^\n.]*?(?:weights|allocation))\s*:?\s*$', prefix, re.I)
                if headings:
                    scope = _scope(headings[-1])
            check(match, scope, canonical_facts.get(scope,{}).get(ticker), True, ticker)
            weight_spans.append(match.span())
    return {'status': 'mismatch_detected' if mismatches else ('verified' if checked else 'no_numeric_claims'),
            'checked_claims': checked, 'mismatches': mismatches, 'retrieval_method': retrieval_method}


def attach_corrections(response, report):
    corrections = list(dict.fromkeys(item['correction'] for item in report['mismatches']))
    if corrections:
        return response.rstrip() + '\n\n**Quant engine corrections**\n\n' + '\n'.join('- '+line for line in corrections)
    return response
