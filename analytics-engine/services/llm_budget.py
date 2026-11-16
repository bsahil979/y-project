"""Compact LLM context and conservative provider-independent request bounds."""
import copy
import json
import re


def encoded_size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8'))


def clip(text, byte_limit):
    raw = str(text).encode('utf-8')
    if len(raw) <= byte_limit:
        return str(text)
    marker = '\n[Context shortened; omitted records are unknown.]'
    if byte_limit < len(marker.encode('utf-8')):
        return raw[:max(0, byte_limit)].decode('utf-8', errors='ignore')
    return raw[:byte_limit-len(marker.encode('utf-8'))].decode('utf-8', errors='ignore') + marker


_BULK_KEYS = {'prices', 'price_history', 'history', 'equity_curve', 'equity_curves',
              'portfolio_returns', 'daily_returns', 'drawdown_series', 'cumulative_returns',
              'predictions', 'covariance_matrix', 'correlation_matrix'}


def compact(value, query='', depth=0):
    """Keep scalar metrics and relevant records; never serialize complete series."""
    if depth > 6:
        return '[Details omitted]'
    if isinstance(value, dict):
        out = {}
        for key, item in list(value.items())[:40]:
            if key.lower() in _BULK_KEYS or key.lower().endswith('_series'):
                out[key + '_omitted'] = True
            else:
                out[key] = compact(item, query, depth+1)
        if len(value) > 40:
            out['_omitted_fields'] = len(value)-40
        return out
    if isinstance(value, (list, tuple)):
        records = list(value)
        if records and isinstance(records[0], dict):
            terms = set(re.findall(r'[a-z0-9]+', query.lower()))
            def relevance(record):
                identity = ' '.join(str(record.get(k, '')) for k in
                                    ('ticker', 'symbol', 'name', 'company_name', 'company')).lower()
                return len(terms & set(re.findall(r'[a-z0-9]+', identity)))
            records.sort(key=relevance, reverse=True)
        selected = [compact(item, query, depth+1) for item in records[:8]]
        if len(records) > 8:
            selected.append({'_omitted_records': len(records)-8})
        return selected
    if isinstance(value, str):
        return clip(value, 400)
    if isinstance(value, float):
        return round(value, 6)
    return value


def compact_json(value, query='', max_bytes=2400):
    result = compact(value, query)
    # Remove whole fields rather than cutting JSON in the middle of a number.
    while encoded_size(result) > max_bytes:
        containers = []
        def visit(obj):
            if isinstance(obj, dict):
                for key, item in obj.items():
                    if key.startswith('_'):
                        continue
                    containers.append((encoded_size(item), obj, key))
                    visit(item)
            elif isinstance(obj, list):
                for item in obj:
                    visit(item)
        visit(result)
        if not containers:
            return json.dumps({'_omitted': 'Context exceeded budget'})
        _, parent, key = max(containers, key=lambda entry: entry[0])
        if isinstance(parent[key], list) and len(parent[key]) > 1:
            parent[key].pop()  # least relevant records are at the end
        else:
            del parent[key]
        parent['_context_shortened'] = True
    return json.dumps(result, ensure_ascii=False, separators=(',', ':'), default=str)


def budget_messages(messages, tools=None, max_bytes=6000):
    """UTF-8 bytes conservatively bound text tokens, including tool schemas.

    Leave extra headroom below the 8k TPM tier for output and chat framing.
    Preserve roles/tool-call relationships; shorten content on a copied payload.
    """
    result = copy.deepcopy(messages)
    def size():
        return encoded_size({'messages': result, 'tools': tools or []})
    while size() > max_bytes:
        candidates = [m for m in result if isinstance(m.get('content'), str)
                      and len(m['content'].encode('utf-8')) > 80]
        if not candidates:
            raise ValueError('Tool definitions or message metadata exceed the LLM request budget. Reduce the tool set.')
        largest = max(candidates, key=lambda m: len(m['content'].encode('utf-8')))
        length = len(largest['content'].encode('utf-8'))
        if largest.get('role') == 'system' and '<verified_portfolio_facts>' in largest['content']:
            # Keep the authoritative JSON and its instructions intact. Shorten the user context first.
            alternatives = [m for m in candidates if m is not largest]
            if not alternatives:
                raise ValueError('Portfolio facts exceed the configured model input budget')
            largest = max(alternatives, key=lambda m: len(m['content'].encode('utf-8')))
            length = len(largest['content'].encode('utf-8'))
        largest['content'] = clip(largest['content'], max(80, length-max(128, size()-max_bytes)))
    return result
