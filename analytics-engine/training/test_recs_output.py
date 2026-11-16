import json
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services.recommendation_engine import generate_recommendations

recs = generate_recommendations(
    tickers=['AAPL', 'MSFT', 'GOOGL'],
    weights=[0.6, 0.2, 0.2],
    risk_budget_res={
        'risk_contributions': [
            {'ticker': 'AAPL', 'percentage_contribution_to_risk': 75.0, 'volatility': 0.25}
        ]
    },
    portfolio_score_res={'score': 72},
    marketmind_details={
        'AAPL': {'recommendation': 'BUY', 'confidence': 0.85, 'score': 0.9, 'class_probabilities': {'-1': 0.05, '0': 0.1, '1': 0.85}}
    },
    attribution_res={'portfolio_total_return': 0.12},
    regime_res={'current_regime': 'Bullish'}
)
print(json.dumps(recs, indent=2))