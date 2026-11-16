"""
Paper Trading Engine - Simulates real trading without financial risk.

This module provides:
1. Virtual portfolio management
2. Order execution simulation
3. Real-time P&L tracking
4. Performance analytics
5. Trade journal and audit trail
6. Multi-strategy support
"""

import json
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    id: str
    ticker: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float]
    status: str
    created_at: str
    filled_at: Optional[str] = None
    filled_price: Optional[float] = None
    commission: float = 0.0
    strategy: Optional[str] = None
    reason: Optional[str] = None


@dataclass
class Position:
    ticker: str
    quantity: float
    average_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


@dataclass
class PaperTradingAccount:
    account_id: str
    initial_capital: float
    current_capital: float
    cash: float
    positions: Dict[str, Dict]
    orders: List[Dict]
    trades: List[Dict]
    daily_pnl: List[Dict]
    created_at: str
    last_updated: str


class PaperTradingEngine:
    """
    Paper trading engine for simulating trading strategies.
    """
    
    def __init__(
        self,
        account_id: str = "default",
        initial_capital: float = 100000.0,
        commission_rate: float = 0.001,  # 0.1% per trade
        slippage_rate: float = 0.0005,   # 0.05% slippage
        data_dir: str = "./paper_trading_data"
    ):
        """
        Initialize paper trading engine.
        
        Args:
            account_id: Unique identifier for the account
            initial_capital: Starting capital
            commission_rate: Commission rate per trade
            slippage_rate: Expected slippage per trade
            data_dir: Directory to store paper trading data
        """
        self.account_id = account_id
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.data_dir = data_dir
        self.data_file = os.path.join(data_dir, f"{account_id}.json")
        
        os.makedirs(data_dir, exist_ok=True)
        
        # Load existing account or create new
        self.account = self._load_account() or self._create_account()
        
    def _create_account(self) -> PaperTradingAccount:
        """Create a new paper trading account."""
        now = datetime.now().isoformat()
        return PaperTradingAccount(
            account_id=self.account_id,
            initial_capital=self.initial_capital,
            current_capital=self.initial_capital,
            cash=self.initial_capital,
            positions={},
            orders=[],
            trades=[],
            daily_pnl=[],
            created_at=now,
            last_updated=now
        )
    
    def _load_account(self) -> Optional[PaperTradingAccount]:
        """Load existing account from disk."""
        if not os.path.exists(self.data_file):
            return None
        
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                return PaperTradingAccount(**data)
        except Exception as e:
            print(f"Error loading account: {e}")
            return None
    
    def _save_account(self):
        """Save account state to disk."""
        self.account.last_updated = datetime.now().isoformat()
        with open(self.data_file, 'w') as f:
            json.dump(asdict(self.account), f, indent=2, default=str)
    
    def place_order(
        self,
        ticker: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: Optional[float] = None,
        strategy: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Dict:
        """
        Place a paper trading order.
        
        Args:
            ticker: Stock ticker symbol
            side: 'buy' or 'sell'
            quantity: Number of shares
            order_type: 'market', 'limit', or 'stop'
            price: Limit or stop price (required for non-market orders)
            strategy: Strategy that generated this order
            reason: Explanation for the trade
            
        Returns:
            Dict with order details and execution result
        """
        order_id = f"{self.account_id}_{datetime.now().timestamp()}"
        
        # Validate order
        validation = self._validate_order(ticker, side, quantity, order_type, price)
        if not validation['valid']:
            return {
                'success': False,
                'error': validation['error'],
                'order_id': order_id
            }
        
        # Create order
        order = Order(
            id=order_id,
            ticker=ticker.upper(),
            side=side.lower(),
            order_type=order_type.lower(),
            quantity=quantity,
            price=price,
            status=OrderStatus.PENDING.value,
            created_at=datetime.now().isoformat(),
            strategy=strategy,
            reason=reason
        )
        
        # Execute order (simplified - immediate execution for market orders)
        execution_result = self._execute_order(order)
        
        # Update account
        self.account.orders.append(asdict(order))
        if execution_result['filled']:
            self.account.trades.append(execution_result['trade'])
        
        self._save_account()
        
        return {
            'success': True,
            'order': asdict(order),
            'execution': execution_result
        }
    
    def _validate_order(
        self,
        ticker: str,
        side: str,
        quantity: float,
        order_type: str,
        price: Optional[float]
    ) -> Dict:
        """Validate order parameters."""
        if side.lower() not in ['buy', 'sell']:
            return {'valid': False, 'error': 'Invalid side'}
        
        if quantity <= 0:
            return {'valid': False, 'error': 'Quantity must be positive'}
        
        if order_type.lower() in ['limit', 'stop'] and price is None:
            return {'valid': False, 'error': 'Price required for limit/stop orders'}
        
        if side.lower() == 'sell':
            current_position = self.account.positions.get(ticker.upper(), {})
            if current_position.get('quantity', 0) < quantity:
                return {'valid': False, 'error': 'Insufficient position'}
        
        if side.lower() == 'buy':
            # Estimate cost (simplified - would need real-time price)
            estimated_cost = quantity * (price or 100) * (1 + self.commission_rate)
            if self.account.cash < estimated_cost:
                return {'valid': False, 'error': 'Insufficient cash'}
        
        return {'valid': True}
    
    def _execute_order(self, order: Order) -> Dict:
        """
        Execute order (simplified simulation).
        In production, this would use real-time market data.
        """
        try:
            # Get current price (simplified - would use real API)
            current_price = order.price or self._get_current_price(order.ticker)
            
            # Apply slippage
            if order.side == 'buy':
                execution_price = current_price * (1 + self.slippage_rate)
            else:
                execution_price = current_price * (1 - self.slippage_rate)
            
            # Calculate commission
            commission = execution_price * order.quantity * self.commission_rate
            
            # Update positions and cash
            if order.side == 'buy':
                total_cost = (execution_price * order.quantity) + commission
                self.account.cash -= total_cost
                
                # Update position
                if order.ticker not in self.account.positions:
                    self.account.positions[order.ticker] = {
                        'quantity': 0,
                        'average_cost': 0,
                        'total_cost': 0
                    }
                
                pos = self.account.positions[order.ticker]
                old_quantity = pos['quantity']
                old_total_cost = pos['total_cost']
                
                pos['quantity'] += order.quantity
                pos['total_cost'] += total_cost
                pos['average_cost'] = pos['total_cost'] / pos['quantity']
                
            else:  # sell
                total_proceeds = (execution_price * order.quantity) - commission
                self.account.cash += total_proceeds
                
                # Update position
                pos = self.account.positions[order.ticker]
                pos['quantity'] -= order.quantity
                pos['total_cost'] -= (pos['average_cost'] * order.quantity)
                
                if pos['quantity'] <= 0:
                    del self.account.positions[order.ticker]
            
            # Update order status
            order.status = OrderStatus.FILLED.value
            order.filled_at = datetime.now().isoformat()
            order.filled_price = execution_price
            order.commission = commission
            
            # Create trade record
            trade = {
                'order_id': order.id,
                'ticker': order.ticker,
                'side': order.side,
                'quantity': order.quantity,
                'price': execution_price,
                'commission': commission,
                'timestamp': order.filled_at,
                'strategy': order.strategy,
                'reason': order.reason
            }
            
            return {
                'filled': True,
                'trade': trade,
                'execution_price': execution_price,
                'commission': commission
            }
            
        except Exception as e:
            order.status = OrderStatus.REJECTED.value
            return {
                'filled': False,
                'error': str(e)
            }
    
    def _get_current_price(self, ticker: str) -> float:
        """
        Get current price (simplified placeholder).
        In production, this would call a real-time market data API.
        """
        # Placeholder - would use yfinance or other API
        try:
            import yfinance as yf
            ticker_obj = yf.Ticker(ticker)
            data = ticker_obj.history(period="1d")
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except:
            pass
        
        # Fallback to last known price or default
        return 100.0  # Default fallback
    
    def update_positions(self, price_data: Dict[str, float]) -> Dict:
        """
        Update positions with current market prices.
        
        Args:
            price_data: Dict mapping tickers to current prices
            
        Returns:
            Dict with updated position values and P&L
        """
        positions_summary = []
        total_market_value = 0
        total_unrealized_pnl = 0
        
        for ticker, pos in self.account.positions.items():
            current_price = price_data.get(ticker, self._get_current_price(ticker))
            quantity = pos['quantity']
            average_cost = pos['average_cost']
            
            market_value = quantity * current_price
            total_cost = quantity * average_cost
            unrealized_pnl = market_value - total_cost
            unrealized_pnl_pct = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0
            
            position_data = {
                'ticker': ticker,
                'quantity': quantity,
                'average_cost': average_cost,
                'current_price': current_price,
                'market_value': market_value,
                'total_cost': total_cost,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_pct': unrealized_pnl_pct
            }
            
            positions_summary.append(position_data)
            total_market_value += market_value
            total_unrealized_pnl += unrealized_pnl
        
        # Update account capital
        self.account.current_capital = self.account.cash + total_market_value
        
        return {
            'positions': positions_summary,
            'total_market_value': total_market_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'cash': self.account.cash,
            'total_capital': self.account.current_capital
        }
    
    def get_account_summary(self) -> Dict:
        """Get comprehensive account summary."""
        # Get current prices for all positions
        price_data = {}
        for ticker in self.account.positions.keys():
            price_data[ticker] = self._get_current_price(ticker)
        
        # Update positions
        positions_data = self.update_positions(price_data)
        
        # Calculate performance metrics
        total_return = (self.account.current_capital - self.account.initial_capital) / self.account.initial_capital
        
        # Calculate daily P&L (simplified)
        daily_pnl_summary = self._calculate_daily_pnl()
        
        return {
            'account_id': self.account.account_id,
            'account_summary': {
                'initial_capital': self.account.initial_capital,
                'current_capital': self.account.current_capital,
                'cash': self.account.cash,
                'total_return_pct': round(total_return * 100, 2),
                'total_pnl': round(self.account.current_capital - self.account.initial_capital, 2)
            },
            'positions': positions_data['positions'],
            'performance': {
                'total_trades': len(self.account.trades),
                'open_positions': len(self.account.positions),
                'win_rate': self._calculate_win_rate(),
                'daily_pnl': daily_pnl_summary
            },
            'recent_orders': self.account.orders[-10:] if self.account.orders else [],
            'recent_trades': self.account.trades[-10:] if self.account.trades else []
        }
    
    def _calculate_win_rate(self) -> float:
        """Calculate win rate from completed trades."""
        if not self.account.trades:
            return 0.0
        
        # Simplified win rate calculation
        # In production, would pair buy/sell trades to calculate realized P&L
        winning_trades = sum(1 for trade in self.account.trades if trade.get('side') == 'sell')
        total_trades = len(self.account.trades)
        
        return round(winning_trades / total_trades * 100, 2) if total_trades > 0 else 0.0
    
    def _calculate_daily_pnl(self) -> Dict:
        """Calculate daily P&L summary."""
        if not self.account.daily_pnl:
            return {
                'total_days': 0,
                'avg_daily_pnl': 0,
                'best_day': 0,
                'worst_day': 0
            }
        
        daily_pnls = [day.get('pnl', 0) for day in self.account.daily_pnl]
        
        return {
            'total_days': len(daily_pnls),
            'avg_daily_pnl': round(np.mean(daily_pnls), 2),
            'best_day': round(max(daily_pnls), 2),
            'worst_day': round(min(daily_pnls), 2)
        }
    
    def reset_account(self, new_initial_capital: Optional[float] = None):
        """Reset account to initial state."""
        self.initial_capital = new_initial_capital or self.initial_capital
        self.account = self._create_account()
        self._save_account()
    
    def export_trades(self, format: str = 'csv') -> str:
        """Export trade history."""
        if format == 'csv':
            df = pd.DataFrame(self.account.trades)
            export_file = os.path.join(self.data_dir, f"{self.account_id}_trades.csv")
            df.to_csv(export_file, index=False)
            return export_file
        elif format == 'json':
            export_file = os.path.join(self.data_dir, f"{self.account_id}_trades.json")
            with open(export_file, 'w') as f:
                json.dump(self.account.trades, f, indent=2)
            return export_file


def create_paper_trading_account(
    account_id: str = "default",
    initial_capital: float = 100000.0
) -> PaperTradingEngine:
    """
    Convenience function to create a new paper trading account.
    """
    return PaperTradingEngine(
        account_id=account_id,
        initial_capital=initial_capital
    )


if __name__ == "__main__":
    # Example usage
    engine = create_paper_trading_account("demo_account", 100000)
    
    # Place some sample orders
    engine.place_order("AAPL", "buy", 10, strategy="momentum", reason="Positive momentum signal")
    engine.place_order("MSFT", "buy", 5, strategy="trend", reason="Uptrend continuation")
    
    # Get account summary
    summary = engine.get_account_summary()
    print(json.dumps(summary, indent=2, default=str))