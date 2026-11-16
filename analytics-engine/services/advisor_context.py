"""Request-local portfolio documents. Never index private records globally."""
import json


def portfolio_documents(context):
    if not context or not context.get('portfolio_id'):
        raise ValueError('Select a portfolio before asking the advisor.')
    currency = context.get('currency')
    if currency not in ('INR', 'USD'):
        raise ValueError('Select INR or USD holdings for analysis.')
    documents = []
    for category in ('holdings', 'transactions'):
        for index, record in enumerate(context.get(category, [])):
            if record.get('currency') != currency:
                raise ValueError('Portfolio context cannot mix currencies.')
            documents.append({
                'type': 'portfolio', 'title': f'{category} {index + 1}',
                'portfolio_id': context['portfolio_id'],
                'content': json.dumps(record, ensure_ascii=False),
            })
    return documents
