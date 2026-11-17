import pytest
from services.fund_nav import parse_nav
def test_amfi_nav_fields_and_missing_scheme():
    text='123456;INF000;INF001;Example Growth;25.75;13-Nov-2026'
    result=parse_nav(text,'123456')
    assert result['nav']==25.75
    assert result['date']=='2026-11-13'
    assert result['source']=='AMFI'
    with pytest.raises(LookupError):
        parse_nav(text,'654321')
    with pytest.raises(ValueError):
        parse_nav(text.replace('25.75','nan'),'123456')

def test_amfi_extended_plan_option_columns_and_isin_lookup():
    text='Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date\n118778;INF204K01K15;-;Nippon India Small Cap Fund;Direct Plan;Growth Option;203.3310;16-Nov-2026'
    result=parse_nav(text,'INF204K01K15')
    assert result['scheme_code']=='118778'
    assert result['nav']==203.3310
    assert result['date']=='2026-11-16'
    assert result['name']=='Nippon India Small Cap Fund - Direct Plan - Growth Option'
