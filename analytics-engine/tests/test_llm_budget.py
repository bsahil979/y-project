import json
import os
import unittest
from unittest.mock import MagicMock, patch
from services.llm_budget import budget_messages, compact_json, encoded_size
from agents.ai_advisor import AIAdvisor


class BudgetTests(unittest.TestCase):
    def test_large_analytics_become_valid_compact_json(self):
        data = {'portfolio_value': 12345, 'portfolio_returns': [0.001]*50000,
                'risk': {'volatility': .12}, 'equity_curve': list(range(10000))}
        result = compact_json(data)
        parsed = json.loads(result)
        self.assertEqual(parsed['portfolio_value'], 12345)
        self.assertEqual(parsed['risk']['volatility'], .12)
        self.assertTrue(parsed['portfolio_returns_omitted'])
        self.assertLessEqual(len(result.encode('utf-8')), 2400)

    def test_named_holding_is_preserved_among_many(self):
        holdings = [{'ticker':f'STOCK{i}', 'quantity':i} for i in range(100)]
        holdings.append({'ticker':'TCS.NS', 'quantity':12})
        result=json.loads(compact_json({'holdings':holdings}, 'Explain TCS'))
        self.assertEqual(result['holdings'][0]['ticker'], 'TCS.NS')
        self.assertIn('_omitted_records', result['holdings'][-1])

    def test_unicode_budget_and_input_not_mutated(self):
        messages=[{'role':'system','content':'Use supplied data only.'},
                  {'role':'user','content':'Explain risk: ' + '₹你好'*50000}]
        result=budget_messages(messages)
        self.assertLessEqual(encoded_size({'messages':result,'tools':[]}),6000)
        self.assertTrue(result[1]['content'].startswith('Explain risk:'))
        self.assertGreater(len(messages[1]['content']), 100000)

    def test_all_openai_paths_are_bounded_including_tools(self):
        advisor=AIAdvisor()
        client=MagicMock()
        client.chat.completions.create.return_value.choices[0].message.content='Summary'
        client.chat.completions.create.return_value.choices[0].message.tool_calls=[]
        messages=[{'role':'system','content':'Use supplied metrics.'},
                  {'role':'user','content':'Explain risk '+('data '*50000)}]
        with patch.object(advisor, '_get_client', return_value=client):
            advisor._generate_openai(messages)
            client.chat.completions.create.return_value=[]
            list(advisor._stream_openai(messages))
            client.chat.completions.create.return_value=MagicMock()
            client.chat.completions.create.return_value.choices[0].message.tool_calls=[]
            advisor._openai_chat_with_tools(messages)
        for call in client.chat.completions.create.call_args_list:
            payload=call.kwargs
            self.assertLessEqual(encoded_size({'messages':payload['messages'], 'tools':payload.get('tools',[])}),6000)
            self.assertLessEqual(payload['max_tokens'],768)

    def test_output_env_cannot_reserve_huge_completion(self):
        with patch.dict(os.environ, {'LLM_MAX_TOKENS':'50000'}):
            self.assertEqual(AIAdvisor().max_tokens,768)

    def test_tool_relationships_survive_compaction(self):
        messages=[{'role':'assistant','tool_calls':[{'id':'call_1','type':'function','function':{'name':'risk','arguments':'{}'}}]},
                  {'role':'tool','tool_call_id':'call_1','content':'x'*100000}]
        result=budget_messages(messages)
        self.assertEqual(result[0]['tool_calls'][0]['id'],result[1]['tool_call_id'])
        self.assertLessEqual(encoded_size({'messages':result,'tools':[]}),6000)

if __name__ == '__main__': unittest.main()
