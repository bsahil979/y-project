import unittest
from unittest.mock import patch, MagicMock
from services.advisor_context import portfolio_documents


class AdvisorContextTests(unittest.TestCase):
    def test_provider_length_limit_returns_complete_analytics_fallback(self):
        from agents.ai_advisor import AIAdvisor
        advisor = AIAdvisor()
        advisor.api_key = 'test'
        advisor.provider = 'openai'
        client = MagicMock()
        choice = client.chat.completions.create.return_value.choices[0]
        choice.finish_reason = 'length'
        choice.message.content = 'Below is a side-by-side'
        with patch.object(advisor, '_get_client', return_value=client), \
             patch.object(advisor, 'gather_structured_context', return_value={'tickers': ['MSFT']}), \
             patch.object(advisor._retriever, 'collect_all', return_value=[]):
            response = advisor.chat('Explain portfolio risk')
        self.assertFalse(response['llm_used'])
        self.assertIn('could not be completed', response['content'])
        self.assertNotIn('Below is a side-by-side', response['content'])

    def test_owned_chat_reuses_matching_advisor_analysis(self):
        import api
        context = {
            'portfolio_id': 'reuse-test', 'portfolio_revision': 'rev-test', 'currency': 'USD',
            'holdings': [{'ticker': 'MSFT', 'currency': 'USD', 'market_value': 500}],
        }
        request = api.PortfolioAnalyzeRequest(
            tickers=['MSFT'], weights=[1.0], portfolio_value=500, start='2023-01-01',
            currency='USD', portfolio_id='reuse-test', portfolio_revision='rev-test',
            include_optional_ml=False,
        )
        with patch.object(api, 'portfolio_analyze_cache', {}), \
             patch('services.portfolio_pipeline.run_portfolio_pipeline',
                   return_value={'analysis_id': 'cached-analysis'}) as pipeline:
            api.portfolio_analyze(request)
            advisor = api.AIAdvisor(owned_analysis_loader=api.load_chat_portfolio_analysis)
            structured, _ = advisor._owned_context(context, [], [], 0, '2023-01-01', None, 30, 'Explain risk')
        self.assertEqual(pipeline.call_count, 1)
        self.assertEqual(structured['canonical_analysis']['analysis_id'], 'cached-analysis')

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

class ConversationTests(unittest.TestCase):
    def test_conversation_uses_history_without_running_analytics(self):
        from agents.ai_advisor import AIAdvisor
        advisor = AIAdvisor()
        advisor.api_key = 'test'
        advisor.provider = 'openai'
        with patch.object(advisor, '_generate_openai', return_value=('Diversification spreads exposure.', None)) as generate, \
             patch.object(advisor, '_owned_context', side_effect=AssertionError('unexpected analytics')):
            result = advisor.conversation('Explain that simply', {
                'recent_turns': [{'role': 'user', 'text': 'What is diversification?'}],
                'holdings': [{'ticker': 'MSFT', 'market_value': None}],
            })
        self.assertTrue(result['llm_used'])
        self.assertIn('What is diversification?', generate.call_args.args[0][1]['content'])
        self.assertIn('Explain that simply', generate.call_args.args[0][1]['content'])

    def test_conversation_preserves_partial_answer_with_notice(self):
        from agents.ai_advisor import AIAdvisor
        advisor = AIAdvisor()
        client = MagicMock()
        client.chat.completions.create.return_value.choices = [MagicMock(
            finish_reason='length', message=MagicMock(content='Here is the explanation.'))]
        with patch.object(advisor, '_get_client', return_value=client):
            reply, _ = advisor._generate_openai([], max_tokens=1536, allow_partial=True)
        self.assertIn('Here is the explanation.', reply)
        self.assertIn('output limit', reply)

    def test_conversation_exposes_quota_failure_without_provider_payload(self):
        from agents.ai_advisor import AIAdvisor
        advisor = AIAdvisor()
        advisor.api_key = 'test'
        advisor.provider = 'openai'
        error = Exception('private upstream payload')
        error.status_code = 429
        with patch.object(advisor, '_generate_openai', side_effect=error):
            result = advisor.conversation('hello')
        self.assertIn('quota', result['content'])
        self.assertNotIn('private upstream', result['content'])
