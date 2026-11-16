from services.portfolio_intelligence import PortfolioIntelligenceEngine, PortfolioInput
import json
engine = PortfolioIntelligenceEngine()
inp = PortfolioInput(
    tickers=['AAPL'],
    weights=[1.0],
    portfolio_value=100000.0,
    start_date='2023-01-01',
    end_date='2026-08-24'
)
res = engine.analyze_portfolio(inp)
print(json.dumps(res.to_dict()['recommendations'], indent=2))