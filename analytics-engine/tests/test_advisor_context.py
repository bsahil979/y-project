import unittest
from unittest.mock import patch, MagicMock
from services.advisor_context import portfolio_documents


class AdvisorContextTests(unittest.TestCase):
    def test_gemini_receives_question_and_system_context_without_storage(self):
        from agents.ai_advisor import AIAdvisor
        advisor = AIAdvisor()
        client = MagicMock()
        client.ok = True
        client.status_code = 200
        client.json.return_value = {'steps': [{'type': 'model_output', 'content': [{'type': 'text', 'text': 'You own 12 Reliance shares.'}]}]}
        with patch('requests.post', return_value=client) as request:
            reply, _ = advisor._generate_gemini('Use only selected portfolio records.', 'Tell me about Reliance. Quantity: 12.')
        self.assertIn('12 Reliance', reply)
        self.assertFalse(request.call_args.kwargs['json']['store'])
        self.assertIn('Reliance', request.call_args.kwargs['json']['input'])

    def test_gemini_quota_error_is_not_retried(self):
        from agents.ai_advisor import AIAdvisor
        response = MagicMock(status_code=429)
        with patch('requests.post', return_value=response) as request:
            with self.assertRaisesRegex(RuntimeError, 'quota reached'):
                AIAdvisor()._generate_gemini('Use portfolio data.', 'Explain risk.')
        self.assertEqual(request.call_count, 1)

    def test_chat_uses_owned_values_and_never_legacy_analysis(self):
        from agents.ai_advisor import AIAdvisor
        advisor = AIAdvisor()
        advisor.api_key = None
        context = {'portfolio_id': 'one', 'currency': 'INR', 'holdings': [
            {'ticker': 'TCS.NS', 'currency': 'INR', 'quantity': 2, 'market_value': 6000},
            {'ticker': 'INFY.NS', 'currency': 'INR', 'quantity': 1, 'market_value': 2000},
        ]}
        with patch('services.portfolio_pipeline.run_portfolio_pipeline', return_value={'risk_budget': {}}) as pipeline, \
                patch.object(advisor, 'gather_structured_context', side_effect=AssertionError('legacy context')), \
                patch.object(advisor._retriever, 'collect_knowledge_base', return_value=[]):
            result = advisor.chat('What are my holdings?', tickers=['OTHER'], portfolio_context=context)
        self.assertEqual(pipeline.call_args.kwargs['portfolio_value'], 8000)
        self.assertEqual(pipeline.call_args.kwargs['weights'], [0.75, 0.25])
        self.assertEqual(pipeline.call_args.kwargs['benchmark'], '^NSEI')
        self.assertNotIn('OTHER', result['content'])
        self.assertIn('TCS.NS', result['content'])

    def test_private_documents_remain_request_local(self):
        first = portfolio_documents({'portfolio_id': 'first', 'currency': 'INR', 'holdings': [{'ticker': 'TCS.NS', 'currency': 'INR'}]})
        second = portfolio_documents({'portfolio_id': 'second', 'currency': 'USD', 'holdings': [{'ticker': 'AAPL', 'currency': 'USD'}]})
        self.assertNotIn('TCS.NS', str(second))
        self.assertNotIn('AAPL', str(first))
        self.assertEqual(first[0]['portfolio_id'], 'first')

    def test_rejects_unselected_and_mixed_currency_context(self):
        with self.assertRaises(ValueError):
            portfolio_documents({})
        with self.assertRaises(ValueError):
            portfolio_documents({'portfolio_id': 'first', 'currency': 'INR', 'transactions': [{'currency': 'USD'}]})
