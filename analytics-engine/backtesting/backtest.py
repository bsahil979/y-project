import numpy as np
import pandas as pd


def sharpe_ratio(returns, risk_free=0.0):
    if returns is None or len(returns) == 0:
        return 0.0
    mean = returns.mean() - risk_free
    std = returns.std()
    if std == 0:
        return 0.0
    return float((np.sqrt(252) * mean) / std)


def max_drawdown(equity_curve):
    if equity_curve is None or len(equity_curve) == 0:
        return 0.0
    roll_max = np.maximum.accumulate(equity_curve)
    drawdowns = (equity_curve - roll_max) / roll_max
    return float(drawdowns.min())


def win_rate(returns):
    if returns is None or len(returns) == 0:
        return 0.0
    wins = (returns > 0).sum()
    total = len(returns)
    return float(wins / total) if total > 0 else 0.0


def _coerce_series(prices, signals):
    if prices is None or signals is None:
        return None, None

    p = pd.Series(prices).copy()
    s = pd.Series(signals).copy()

    if p.empty or s.empty:
        return None, None

    if len(p) != len(s):
        common_len = min(len(p), len(s))
        p = p.iloc[:common_len]
        s = s.iloc[:common_len]

    if not p.index.equals(s.index):
        combined = pd.DataFrame({"price": p, "signal": s}).dropna()
        if combined.empty:
            return None, None
        p = combined["price"]
        s = combined["signal"]

    return p, s


def backtest_from_signals(prices: pd.Series, signals: pd.Series):
    """Simple backtest: signals are -1,0,1 for sell,hold,buy.

    If price data or signals are missing or invalid, the function returns a safe,
    non-crashing fallback with neutral metrics instead of raising an exception.
    """
    p, s = _coerce_series(prices, signals)
    if p is None or s is None:
        empty_metrics = {
            'sharpe': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'total_return': 0.0,
            'status': 'fallback_no_data',
        }
        return empty_metrics, pd.Series(dtype=float)

    cash = 100000.0
    position = 0.0
    equity = []

    for price, sig in zip(p, s):
        try:
            price = float(price)
            sig = int(sig)
        except (TypeError, ValueError):
            continue

        if sig == 1 and cash > 0 and price > 0:
            position = cash / price
            cash = 0.0
        elif sig == -1 and position > 0 and price > 0:
            cash = position * price
            position = 0.0
        net = cash + position * price
        equity.append(net)

    if not equity:
        empty_metrics = {
            'sharpe': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'total_return': 0.0,
            'status': 'fallback_no_valid_signals',
        }
        return empty_metrics, pd.Series(dtype=float)

    eq = pd.Series(equity, index=p.index[:len(equity)])
    returns = eq.pct_change().fillna(0)
    total_return = float(eq.iloc[-1] / eq.iloc[0] - 1) if len(eq) > 0 and eq.iloc[0] != 0 else 0.0

    metrics = {
        'sharpe': sharpe_ratio(returns),
        'max_drawdown': max_drawdown(eq.values),
        'win_rate': win_rate(returns),
        'total_return': total_return,
        'status': 'ok',
    }
    return metrics, eq
