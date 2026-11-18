from unittest.mock import patch
from services.conversation_facts import conversation_facts, unsupported_money
from agents.ai_advisor import AIAdvisor

def context():
    return {'currency':'INR', 'holdings':[{'ticker':'TCS.NS','currency':'INR','market_value':100}],
            'tracked_assets':[{'name':'Small Cap Fund','type':'mutual_fund','currency':'INR','recorded_value':v} for v in (6778.65,1996.71,8206.63)] +
            [{'type':'cash','currency':'INR','recorded_value':5555}]}

def test_totals_separate_funds_cash_and_missing_prices():
    c=context(); f=conversation_facts(c)
    assert f['totals']['mutual_fund']==16981.99
    assert f['totals']['cash']==5555
    assert unsupported_money('Your funds total ₹22,000.',c,f)
    assert not unsupported_money('Your funds total INR 16,981.99.',c,f)
    c['holdings'][0]['market_value']=None
    assert conversation_facts(c)['totals']['net_worth'] is None

def test_wrong_total_is_withheld_and_allocation_not_invented():
    a=AIAdvisor(); a.api_key='test'; a.provider='openai'
    with patch.object(a,'_generate_openai',return_value=('Your mutual funds total ₹22,000.',None)) as generate:
        r=a.conversation('Review my portfolio',context())
        assert '22,000' not in r['content']
        assert '16,981.99' in r['content']
        assert r['grounding_check']['status']=='unsupported_claims_withheld'
        generate.reset_mock()
        r=a.conversation('Explain my suggested allocation',context())
        generate.assert_not_called()
        assert 'not available' in r['content']
