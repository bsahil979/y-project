import pandas as pd
from services import fund_benchmarks as b
from services.fund_disclosures import disclosure_for, disclosed_overlaps


def test_only_common_dates_are_used(monkeypatch):
    dates = pd.bdate_range('2025-01-01', periods=64)
    nav = pd.Series(range(100,164), index=dates)
    index = pd.Series(range(200,262), index=dates[1:-1])
    monkeypatch.setattr(b, 'index_history', lambda *args: index)
    result = b.compare_benchmark('quant Small Cap Fund - Direct Growth', nav, {})
    assert result['observations'] == 62
    assert result['fund_return'] == 162/101-1
    assert result['index_return'] == 261/200-1
    assert 'reason' in b.compare_benchmark('Unmapped Growth', nav, {})


def test_disclosed_overlap_and_plan_fee():
    funds = [{'name':name,'disclosure':disclosure_for(name)} for name in
             ['quant small cap fund - Direct Growth','quant flexi cap fund - Growth',
              'Nippon India Small Cap Fund - Growth']]
    assert funds[0]['disclosure']['expense_ratio_pct'] == .99
    overlap, = disclosed_overlaps(funds)
    assert abs(overlap['minimum_pct'] - 13.96) < 1e-9


def test_unreachable_index_uses_dated_plan_specific_amc_returns(monkeypatch):
    import requests
    def offline(*args):
        raise requests.Timeout()
    monkeypatch.setattr(b, 'index_history', offline)
    dates = pd.bdate_range('2026-01-01', '2026-11-13')
    nav = pd.Series(100., index=dates)
    result = b.compare_benchmark('Nippon India Small Cap Fund - Direct Growth', nav, {})
    assert result['period_label'].endswith('2026-05-29')
    assert abs(result['fund_return'] - .0531) < 1e-9
    assert abs(result['difference']-.0378)<1e-9
    assert 'reason' in b.compare_benchmark('quant Small Cap Fund - IDCW', nav, {})
