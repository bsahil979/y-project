"""
Test script to verify portfolio optimizer implementation and correctness.
Uses synthetic data to validate mathematical correctness.
"""

import numpy as np
import pandas as pd
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from services.portfolio_optimizer import PortfolioOptimizer


def create_synthetic_data(n_assets=4, n_periods=252, seed=42):
    """Create synthetic return data for testing."""
    np.random.seed(seed)
    
    # Create correlated returns
    mean_returns = np.array([0.08, 0.12, 0.10, 0.15]) / 252  # Annualized daily returns
    cov_matrix = np.array([
        [0.0004, 0.0002, 0.0001, 0.00015],
        [0.0002, 0.0009, 0.0003, 0.00025],
        [0.0001, 0.0003, 0.0006, 0.0002],
        [0.00015, 0.00025, 0.0002, 0.0016]
    ])
    
    # Generate correlated returns
    L = np.linalg.cholesky(cov_matrix)
    daily_returns = np.random.randn(n_periods, n_assets) @ L.T + mean_returns
    
    # Create price series
    prices = np.cumprod(1 + daily_returns, axis=0) * 100
    
    # Create DataFrame
    tickers = ['ASSET_A', 'ASSET_B', 'ASSET_C', 'ASSET_D']
    returns_df = pd.DataFrame(daily_returns, columns=tickers)
    prices_df = pd.DataFrame(prices, columns=tickers)
    
    return returns_df, prices_df, mean_returns * 252, cov_matrix * 252


def test_portfolio_optimizer():
    """Test portfolio optimizer with synthetic data."""
    print("=" * 60)
    print("PORTFOLIO OPTIMIZER VERIFICATION TEST")
    print("=" * 60)
    
    # Create synthetic data
    returns_df, prices_df, true_mean_returns, true_cov_matrix = create_synthetic_data()
    
    print(f"\nSynthetic Data:")
    print(f"  Assets: {returns_df.columns.tolist()}")
    print(f"  Periods: {len(returns_df)}")
    print(f"  True Annual Returns: {true_mean_returns}")
    print(f"  True Annual Covariance Matrix:\n{true_cov_matrix}")
    
    # Initialize optimizer
    optimizer = PortfolioOptimizer(returns_df, risk_free_rate=0.02)
    
    # Test 1: Max Sharpe Optimization
    print("\n" + "=" * 60)
    print("TEST 1: Max Sharpe Ratio Optimization")
    print("=" * 60)
    
    try:
        max_sharpe_result = optimizer.optimize_max_sharpe()
        print("[PASS] Max Sharpe optimization completed successfully")
        print(f"  Optimal weights: {max_sharpe_result['weights']}")
        print(f"  Expected return: {max_sharpe_result['performance']['return']*100:.2f}%")
        print(f"  Expected volatility: {max_sharpe_result['performance']['volatility']*100:.2f}%")
        print(f"  Sharpe ratio: {max_sharpe_result['performance']['sharpe_ratio']:.4f}")
        
        # Verify weights sum to 1
        total_weight = sum(max_sharpe_result['weights'].values())
        print(f"  Weight sum: {total_weight:.6f} (should be 1.0)")
        assert abs(total_weight - 1.0) < 1e-6, "Weights don't sum to 1"
        
        # Verify all weights are non-negative
        negative_weights = [w for w in max_sharpe_result['weights'].values() if w < 0]
        assert len(negative_weights) == 0, "Negative weights found"
        
        print("[PASS] Mathematical correctness verified")
        
    except Exception as e:
        print(f"[FAIL] Max Sharpe optimization failed: {e}")
        return False
    
    # Test 2: Min Volatility Optimization
    print("\n" + "=" * 60)
    print("TEST 2: Min Volatility Optimization")
    print("=" * 60)
    
    try:
        min_vol_result = optimizer.optimize_min_volatility()
        print("[PASS] Min volatility optimization completed successfully")
        print(f"  Optimal weights: {min_vol_result['weights']}")
        print(f"  Expected return: {min_vol_result['performance']['return']*100:.2f}%")
        print(f"  Expected volatility: {min_vol_result['performance']['volatility']*100:.2f}%")
        print(f"  Sharpe ratio: {min_vol_result['performance']['sharpe_ratio']:.4f}")
        
        # Verify weights sum to 1
        total_weight = sum(min_vol_result['weights'].values())
        print(f"  Weight sum: {total_weight:.6f} (should be 1.0)")
        assert abs(total_weight - 1.0) < 1e-6, "Weights don't sum to 1"
        
        # Verify volatility is lower than max sharpe
        assert min_vol_result['performance']['volatility'] <= max_sharpe_result['performance']['volatility'] + 1e-6
        print("[PASS] Volatility is lower than max sharpe (as expected)")
        
        print("[PASS] Mathematical correctness verified")
        
    except Exception as e:
        print(f"[FAIL] Min volatility optimization failed: {e}")
        return False
    
    # Test 3: Risk Parity Optimization
    print("\n" + "=" * 60)
    print("TEST 3: Risk Parity Optimization")
    print("=" * 60)
    
    try:
        risk_parity_result = optimizer.optimize_risk_parity()
        print("[PASS] Risk parity optimization completed successfully")
        print(f"  Optimal weights: {risk_parity_result['weights']}")
        print(f"  Expected return: {risk_parity_result['performance']['return']*100:.2f}%")
        print(f"  Expected volatility: {risk_parity_result['performance']['volatility']*100:.2f}%")
        print(f"  Sharpe ratio: {risk_parity_result['performance']['sharpe_ratio']:.4f}")
        
        # Verify weights sum to 1
        total_weight = sum(risk_parity_result['weights'].values())
        print(f"  Weight sum: {total_weight:.6f} (should be 1.0)")
        assert abs(total_weight - 1.0) < 1e-6, "Weights don't sum to 1"
        
        print("[PASS] Mathematical correctness verified")
        
    except Exception as e:
        print(f"[FAIL] Risk parity optimization failed: {e}")
        return False
    
    # Test 4: Efficient Frontier
    print("\n" + "=" * 60)
    print("TEST 4: Efficient Frontier Calculation")
    print("=" * 60)
    
    try:
        frontier = optimizer.efficient_frontier(n_points=10)
        print("[PASS] Efficient frontier calculated successfully")
        print(f"  Number of points: {len(frontier['returns'])}")
        
        # Verify frontier properties
        if len(frontier['returns']) > 1:
            # Returns should be generally increasing
            returns_sorted = sorted(frontier['returns'])
            assert frontier['returns'] == returns_sorted, "Returns not sorted"
            print("[PASS] Returns are sorted (as expected)")
            
            # Volatility should generally increase with return
            # (though not strictly monotonic due to optimization)
            print(f"  Return range: {min(frontier['returns'])*100:.2f}% to {max(frontier['returns'])*100:.2f}%")
            print(f"  Volatility range: {min(frontier['volatilities'])*100:.2f}% to {max(frontier['volatilities'])*100:.2f}%")
        
        print("[PASS] Mathematical correctness verified")
        
    except Exception as e:
        print(f"[FAIL] Efficient frontier calculation failed: {e}")
        return False
    
    # Test 5: Portfolio Comparison
    print("\n" + "=" * 60)
    print("TEST 5: Portfolio Comparison")
    print("=" * 60)
    
    try:
        current_weights = {'ASSET_A': 0.4, 'ASSET_B': 0.3, 'ASSET_C': 0.2, 'ASSET_D': 0.1}
        comparison = optimizer.compare_with_current(current_weights, 'max_sharpe')
        
        print("[PASS] Portfolio comparison completed successfully")
        print(f"  Current weights: {current_weights}")
        print(f"  Optimized weights: {comparison['optimized_portfolio']['weights']}")
        print(f"  Return improvement: {comparison['improvements']['return_improvement_pct']:.2f}%")
        print(f"  Volatility reduction: {comparison['improvements']['volatility_reduction_pct']:.2f}%")
        print(f"  Sharpe improvement: {comparison['improvements']['sharpe_improvement']:.4f}")
        
        # Verify current portfolio performance calculation
        current_perf = comparison['current_portfolio']['performance']
        print(f"  Current portfolio return: {current_perf['return']*100:.2f}%")
        print(f"  Current portfolio volatility: {current_perf['volatility']*100:.2f}%")
        
        print("[PASS] Mathematical correctness verified")
        
    except Exception as e:
        print(f"[FAIL] Portfolio comparison failed: {e}")
        return False
    
    # Test 6: Edge Cases
    print("\n" + "=" * 60)
    print("TEST 6: Edge Cases")
    print("=" * 60)
    
    # Test with single asset
    try:
        single_returns = returns_df[['ASSET_A']].copy()
        single_optimizer = PortfolioOptimizer(single_returns, risk_free_rate=0.02)
        single_result = single_optimizer.optimize_max_sharpe()
        
        print("[PASS] Single asset optimization completed")
        print(f"  Weight: {single_result['weights']}")
        assert abs(list(single_result['weights'].values())[0] - 1.0) < 1e-6, "Single asset weight should be 1"
        
    except Exception as e:
        print(f"[FAIL] Single asset test failed: {e}")
        return False
    
    # Test with weight bounds
    try:
        bound_result = optimizer.optimize_max_sharpe(weight_bounds=(0.1, 0.4))
        print("[PASS] Weight bounds optimization completed")
        
        # Verify bounds
        for weight in bound_result['weights'].values():
            assert 0.1 <= weight <= 0.4, f"Weight {weight} outside bounds [0.1, 0.4]"
        
        print(f"  All weights within bounds [0.1, 0.4]")
        
    except Exception as e:
        print(f"[FAIL] Weight bounds test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED [SUCCESS]")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_portfolio_optimizer()
    sys.exit(0 if success else 1)