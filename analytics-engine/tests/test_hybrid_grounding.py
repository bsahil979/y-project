import json
from unittest.mock import Mock, patch
import numpy as np
import pytest
from agents.ai_advisor import AIAdvisor, RAGRetriever, verify_explanation_numbers
from agents.portfolio_grounding import canonical_portfolio_facts, attach_corrections

ANALYSIS = {'analysis_id':'run1', 'base_currency':'USD','tickers':['AAPL','MSFT'],'weights':[.4,.6],
    'portfolio_risk':{'portfolio_sharpe':1.23,'portfolio_sortino':1.5,'portfolio_volatility':.12,
                      'portfolio_annualized_return':.08,'portfolio_max_drawdown':-.21,'portfolio_var_95':-.023,
                      'portfolio_cvar_95':-.031},'portfolio_score':{'score':740},
    'market_regime':{'current_regime':'Neutral'},'personalized_allocation':{'success':True,'weights':{'AAPL':.3}},
    'ai_black_litterman_allocation':{'success':True,'weights':{'AAPL':.35}}}


def test_hybrid_reranks_with_offline_fallback():
    docs = [{'content':'safety safety'}, {'content':'diversification smooths asset risk'}]
    r = RAGRetriever()
    with patch('agents.ai_advisor._local_sentence_encoder',return_value=None):
        lexical, method = r.retrieve_with_method('safety', docs)
    assert method == 'tfidf_fallback' and lexical == docs[:1]
    encoder = Mock()
    encoder.encode.return_value = np.array([[0.,1.],[1.,0.],[1.,0.]])
    with patch('agents.ai_advisor._local_sentence_encoder', return_value=encoder):
        hybrid, method = r.retrieve_with_method('safety',docs)
        assert method == 'hybrid_semantic_tfidf' and hybrid[0] == docs[1]
        encoder.encode.side_effect = RuntimeError('offline')
        assert r.retrieve_with_method('safety',docs) == (lexical,'tfidf_fallback')


def test_rounding_units_and_weight_sources():
    facts = canonical_portfolio_facts(ANALYSIS)
    text = ('Sharpe ratio is 1.25. Sortino ratio: 1.5. Volatility: 12.4%. CAGR: 8%. '
            'Max drawdown: -21%. VaR (95%): -2.3%. CVaR: -3.1%. Health score: 741/1000. '
            'Current weight of AAPL is 40%. AAPL target weight: 30%. AI allocation for AAPL: 35%.')
    report = verify_explanation_numbers(text,facts)
    assert report['status'] == 'verified',report
    assert len(report['checked_claims']) == 11,report
    assert verify_explanation_numbers('Review diversification.',facts)['status']=='no_numeric_claims'


def test_wrong_and_missing_facts_receive_corrections():
    facts = canonical_portfolio_facts(ANALYSIS)
    report = verify_explanation_numbers('Sharpe: 2.5. AAPL weight: 70%. XYZ weight: 5%.',facts)
    assert report['status']=='mismatch_detected'
    corrected = attach_corrections('Answer',report)
    for exact in ['1.23','40%','unavailable']:
        assert exact in corrected
    assert len(report['mismatches']) == 3
    assert verify_explanation_numbers('Volatility is 12.6%.',facts)['status']=='mismatch_detected'


@pytest.mark.parametrize('stream',[False,True])
def test_generated_answer_and_sse_share_grounding_contract(stream):
    a = AIAdvisor()
    a.api_key = 'test'
    a.provider = 'openai'
    with patch.object(a,'gather_structured_context',return_value={'canonical_analysis':ANALYSIS}), \
         patch.object(a._retriever,'collect_all',return_value=[]), \
         patch.object(a,'_generate_openai',return_value=('Sharpe ratio: 9.8.',None)) as generate:
        if stream:
            events = list(a.stream_chat('Explain risk'))
            assert len(events)==1
            result = json.loads(events[0].removeprefix('data: '))
            assert result['done']
        else:
            result = a.chat('Explain risk')
    system = generate.call_args.args[0][0]['content']
    block = json.loads(system.split('<verified_portfolio_facts>')[1].split('</verified_portfolio_facts>')[0])
    assert block['sharpe_ratio']==1.23 and block['display_percent']['current_weights']['MSFT']==60
    assert result['grounding_check']['status']=='mismatch_detected'
    assert result['advisor_provenance']['analysis_id']=='run1'
    assert 'Quant engine corrections' in result['content'] and '1.23' in result['content']


def test_prompt_budget_preserves_complete_facts():
    from services.llm_budget import budget_messages
    system = '<verified_portfolio_facts>{"sharpe_ratio":1.23}</verified_portfolio_facts> Strict rules.'
    result = budget_messages([{'role':'system','content':system},
                              {'role':'user','content':'explain '*10000}], max_bytes=600)
    assert result[0]['content'] == system


def test_chat_api_and_stream_carry_corrected_reply():
    from api import app
    from fastapi.testclient import TestClient
    a = AIAdvisor()
    a.api_key = 'test'
    a.provider = 'openai'
    with patch('api.get_ai_advisor',return_value=a), \
         patch.object(a,'gather_structured_context',return_value={'canonical_analysis':ANALYSIS}), \
         patch.object(a._retriever,'collect_all',return_value=[]), \
         patch.object(a,'_generate_openai',return_value=('AAPL weight: 99%.',None)):
        client = TestClient(app)
        for endpoint in ['/chat','/chat/stream']:
            response = client.post(endpoint,json={'query':'Explain weights'})
            assert response.status_code == 200
            result = response.json() if endpoint == '/chat' else json.loads(response.text.removeprefix('data: '))
            assert result['grounding_check']['status'] == 'mismatch_detected'
            assert '40%' in result['content']
            assert result['advisor_provenance']['analysis_id'] == 'run1'


def test_allocation_section_heading_and_signed_risk():
    facts = canonical_portfolio_facts(ANALYSIS)
    result = verify_explanation_numbers('## Personalized allocation\n- AAPL: 30%\n\n## Current weights\n- AAPL: 40%',facts)
    assert result['status'] == 'verified' and len(result['checked_claims']) == 2
    assert verify_explanation_numbers('Max drawdown: 21%.',facts)['status'] == 'mismatch_detected'
    assert verify_explanation_numbers('VaR at 95%: -2.3%.',facts)['status'] == 'verified'


def test_nonbreaking_hyphen_in_markdown_drawdown_is_checked():
    response = '**Maximum drawdown:**\u202f\u201123.42\u202f%'
    for expected, status in [(-.2342, 'verified'), (-.12, 'mismatch_detected')]:
        report = verify_explanation_numbers(response, {'max_drawdown': expected})
        assert report['status'] == status
        assert len(report['checked_claims']) == 1
