"""
Monitoring and Alerts System - Real-time portfolio monitoring with intelligent alerting.

This module provides:
1. Portfolio performance monitoring
2. Risk threshold monitoring
3. Custom alert rules
4. Multiple notification channels
5. Alert history and management
6. Automated watchdog functions
"""

import json
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    PERFORMANCE = "performance"
    RISK = "risk"
    POSITION = "position"
    MARKET = "market"
    SYSTEM = "system"


@dataclass
class Alert:
    id: str
    alert_type: str
    severity: str
    title: str
    message: str
    timestamp: str
    portfolio_id: str
    metrics: Dict[str, Any]
    acknowledged: bool = False
    resolved: bool = False
    resolved_at: Optional[str] = None


@dataclass
class AlertRule:
    id: str
    name: str
    alert_type: str
    condition: str  # e.g., "drawdown > 0.10"
    threshold: float
    severity: str
    enabled: bool = True
    cooldown_minutes: int = 60
    last_triggered: Optional[str] = None


@dataclass
class MonitoringConfig:
    portfolio_id: str
    check_interval_minutes: int = 60
    performance_thresholds: Dict[str, float] = None
    risk_thresholds: Dict[str, float] = None
    position_thresholds: Dict[str, float] = None
    alert_rules: List[Dict] = None
    
    def __post_init__(self):
        if self.performance_thresholds is None:
            self.performance_thresholds = {
                'max_drawdown': 0.15,      # 15% max drawdown
                'min_daily_return': -0.05, # -5% daily return
                'volatility_limit': 0.30   # 30% annual volatility
            }
        if self.risk_thresholds is None:
            self.risk_thresholds = {
                'var_95_limit': 0.05,      # 5% daily VaR
                'concentration_limit': 0.30, # 30% single position
                'sector_concentration': 0.50 # 50% single sector
            }
        if self.position_thresholds is None:
            self.position_thresholds = {
                'min_position_size': 0.01,  # 1% minimum position
                'max_position_size': 0.40   # 40% maximum position
            }
        if self.alert_rules is None:
            self.alert_rules = []


class MonitoringEngine:
    """
    Real-time monitoring and alerting engine for portfolios.
    """
    
    def __init__(
        self,
        config: MonitoringConfig,
        data_dir: str = "./monitoring_data"
    ):
        """
        Initialize monitoring engine.
        
        Args:
            config: Monitoring configuration
            data_dir: Directory to store monitoring data
        """
        self.config = config
        self.data_dir = data_dir
        self.alerts_file = os.path.join(data_dir, f"{config.portfolio_id}_alerts.json")
        self.rules_file = os.path.join(data_dir, f"{config.portfolio_id}_rules.json")
        
        os.makedirs(data_dir, exist_ok=True)
        
        # Load existing data
        self.alerts = self._load_alerts()
        self.rules = self._load_rules()
        
        # Notification handlers
        self.notification_handlers = []
        
    def _load_alerts(self) -> List[Dict]:
        """Load existing alerts from disk."""
        if not os.path.exists(self.alerts_file):
            return []
        
        try:
            with open(self.alerts_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading alerts: {e}")
            return []
    
    def _save_alerts(self):
        """Save alerts to disk."""
        with open(self.alerts_file, 'w') as f:
            json.dump(self.alerts, f, indent=2, default=str)
    
    def _load_rules(self) -> List[Dict]:
        """Load alert rules from disk."""
        if not os.path.exists(self.rules_file):
            return []
        
        try:
            with open(self.rules_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading rules: {e}")
            return []
    
    def _save_rules(self):
        """Save alert rules to disk."""
        with open(self.rules_file, 'w') as f:
            json.dump(self.rules, f, indent=2, default=str)
    
    def add_notification_handler(self, handler: Callable):
        """Add a notification handler for alerts."""
        self.notification_handlers.append(handler)
    
    def _send_notification(self, alert: Alert):
        """Send alert to all registered handlers."""
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in notification handler: {e}")
    
    def create_alert_rule(
        self,
        name: str,
        alert_type: str,
        condition: str,
        threshold: float,
        severity: str = "warning",
        cooldown_minutes: int = 60
    ) -> Dict:
        """
        Create a new alert rule.
        
        Args:
            name: Rule name
            alert_type: Type of alert (performance, risk, position, market, system)
            condition: Condition description
            threshold: Threshold value
            severity: Alert severity (info, warning, critical)
            cooldown_minutes: Minimum time between alerts for this rule
            
        Returns:
            Created rule
        """
        rule = AlertRule(
            id=f"rule_{datetime.now().timestamp()}",
            name=name,
            alert_type=alert_type,
            condition=condition,
            threshold=threshold,
            severity=severity,
            cooldown_minutes=cooldown_minutes
        )
        
        self.rules.append(asdict(rule))
        self._save_rules()
        
        return asdict(rule)
    
    def check_performance_alerts(
        self,
        portfolio_data: Dict,
        current_returns: pd.Series
    ) -> List[Alert]:
        """
        Check performance-related alerts.
        
        Args:
            portfolio_data: Current portfolio data
            current_returns: Recent returns series
            
        Returns:
            List of triggered alerts
        """
        alerts = []
        thresholds = self.config.performance_thresholds
        
        # Calculate performance metrics
        if len(current_returns) > 0:
            daily_return = current_returns.iloc[-1]
            cumulative_return = (1 + current_returns).prod() - 1
            rolling_volatility = current_returns.rolling(20).std().mean() * np.sqrt(252)
            
            # Max drawdown check
            if 'drawdown' in portfolio_data:
                current_drawdown = portfolio_data['drawdown']
                if current_drawdown < -thresholds['max_drawdown']:
                    alerts.append(self._create_alert(
                        alert_type=AlertType.PERFORMANCE,
                        severity=AlertSeverity.CRITICAL,
                        title="Maximum Drawdown Exceeded",
                        message=f"Portfolio drawdown {current_drawdown*100:.2f}% exceeds threshold {thresholds['max_drawdown']*100:.2f}%",
                        metrics={'drawdown': current_drawdown, 'threshold': thresholds['max_drawdown']}
                    ))
            
            # Daily return check
            if daily_return < thresholds['min_daily_return']:
                alerts.append(self._create_alert(
                    alert_type=AlertType.PERFORMANCE,
                    severity=AlertSeverity.WARNING,
                    title="Large Daily Loss",
                    message=f"Daily return {daily_return*100:.2f}% below threshold {thresholds['min_daily_return']*100:.2f}%",
                    metrics={'daily_return': daily_return, 'threshold': thresholds['min_daily_return']}
                ))
            
            # Volatility check
            if rolling_volatility > thresholds['volatility_limit']:
                alerts.append(self._create_alert(
                    alert_type=AlertType.RISK,
                    severity=AlertSeverity.WARNING,
                    title="High Volatility Detected",
                    message=f"Rolling volatility {rolling_volatility*100:.2f}% exceeds threshold {thresholds['volatility_limit']*100:.2f}%",
                    metrics={'volatility': rolling_volatility, 'threshold': thresholds['volatility_limit']}
                ))
        
        return alerts
    
    def check_risk_alerts(
        self,
        portfolio_data: Dict,
        risk_metrics: Dict
    ) -> List[Alert]:
        """
        Check risk-related alerts.
        
        Args:
            portfolio_data: Current portfolio data
            risk_metrics: Risk metrics from risk engine
            
        Returns:
            List of triggered alerts
        """
        alerts = []
        thresholds = self.config.risk_thresholds
        
        # VaR check
        if 'var_95' in risk_metrics:
            current_var = risk_metrics['var_95']
            if abs(current_var) > thresholds['var_95_limit']:
                alerts.append(self._create_alert(
                    alert_type=AlertType.RISK,
                    severity=AlertSeverity.WARNING,
                    title="VaR Threshold Exceeded",
                    message=f"Daily VaR(95%) {current_var*100:.2f}% exceeds threshold {thresholds['var_95_limit']*100:.2f}%",
                    metrics={'var_95': current_var, 'threshold': thresholds['var_95_limit']}
                ))
        
        # Concentration check
        if 'positions' in portfolio_data:
            positions = portfolio_data['positions']
            max_weight = max([p.get('weight', 0) for p in positions]) if positions else 0
            
            if max_weight > thresholds['concentration_limit']:
                alerts.append(self._create_alert(
                    alert_type=AlertType.RISK,
                    severity=AlertSeverity.WARNING,
                    title="High Concentration Risk",
                    message=f"Maximum position weight {max_weight*100:.2f}% exceeds threshold {thresholds['concentration_limit']*100:.2f}%",
                    metrics={'max_weight': max_weight, 'threshold': thresholds['concentration_limit']}
                ))
        
        return alerts
    
    def check_position_alerts(
        self,
        portfolio_data: Dict
    ) -> List[Alert]:
        """
        Check position-related alerts.
        
        Args:
            portfolio_data: Current portfolio data
            
        Returns:
            List of triggered alerts
        """
        alerts = []
        thresholds = self.config.position_thresholds
        
        if 'positions' not in portfolio_data:
            return alerts
        
        positions = portfolio_data['positions']
        
        for position in positions:
            weight = position.get('weight', 0)
            ticker = position.get('ticker', 'Unknown')
            
            # Check maximum position size
            if weight > thresholds['max_position_size']:
                alerts.append(self._create_alert(
                    alert_type=AlertType.POSITION,
                    severity=AlertSeverity.WARNING,
                    title=f"Large Position: {ticker}",
                    message=f"Position {ticker} weight {weight*100:.2f}% exceeds maximum {thresholds['max_position_size']*100:.2f}%",
                    metrics={'ticker': ticker, 'weight': weight, 'threshold': thresholds['max_position_size']}
                ))
        
        return alerts
    
    def _create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        metrics: Dict[str, Any]
    ) -> Alert:
        """Create an alert object."""
        return Alert(
            id=f"alert_{datetime.now().timestamp()}",
            alert_type=alert_type.value,
            severity=severity.value,
            title=title,
            message=message,
            timestamp=datetime.now().isoformat(),
            portfolio_id=self.config.portfolio_id,
            metrics=metrics
        )
    
    def process_alerts(self, alerts: List[Alert]) -> List[Dict]:
        """
        Process and store alerts, send notifications.
        
        Args:
            alerts: List of alerts to process
            
        Returns:
            Processed alerts
        """
        processed = []
        
        for alert in alerts:
            # Check cooldown for similar alerts
            if self._should_trigger_alert(alert):
                alert_dict = asdict(alert)
                self.alerts.append(alert_dict)
                processed.append(alert_dict)
                
                # Send notifications
                self._send_notification(alert)
                logger.info(f"Alert triggered: {alert.title}")
        
        if processed:
            self._save_alerts()
        
        return processed
    
    def _should_trigger_alert(self, new_alert: Alert) -> bool:
        """Check if alert should trigger based on cooldown rules."""
        # Filter recent alerts of same type
        recent_alerts = [
            a for a in self.alerts 
            if a['alert_type'] == new_alert.alert_type and 
            a['severity'] == new_alert.severity
        ]
        
        if not recent_alerts:
            return True
        
        # Check most recent alert timing
        most_recent = max(recent_alerts, key=lambda x: x['timestamp'])
        last_time = datetime.fromisoformat(most_recent['timestamp'])
        current_time = datetime.now()
        
        # Find applicable cooldown
        applicable_rule = next(
            (r for r in self.rules if r['alert_type'] == new_alert.alert_type),
            None
        )
        
        cooldown_minutes = applicable_rule.get('cooldown_minutes', 60) if applicable_rule else 60
        
        time_diff = (current_time - last_time).total_seconds() / 60
        
        return time_diff >= cooldown_minutes
    
    def run_monitoring_cycle(
        self,
        portfolio_data: Dict,
        current_returns: pd.Series,
        risk_metrics: Dict
    ) -> Dict:
        """
        Run a complete monitoring cycle.
        
        Args:
            portfolio_data: Current portfolio data
            current_returns: Recent returns series
            risk_metrics: Risk metrics
            
        Returns:
            Monitoring results with any triggered alerts
        """
        all_alerts = []
        
        # Check different alert types
        all_alerts.extend(self.check_performance_alerts(portfolio_data, current_returns))
        all_alerts.extend(self.check_risk_alerts(portfolio_data, risk_metrics))
        all_alerts.extend(self.check_position_alerts(portfolio_data))
        
        # Process alerts
        processed_alerts = self.process_alerts(all_alerts)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'portfolio_id': self.config.portfolio_id,
            'alerts_triggered': len(processed_alerts),
            'alerts': processed_alerts,
            'total_active_alerts': len([a for a in self.alerts if not a['acknowledged']])
        }
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self.alerts:
            if alert['id'] == alert_id:
                alert['acknowledged'] = True
                alert['acknowledged_at'] = datetime.now().isoformat()
                self._save_alerts()
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        for alert in self.alerts:
            if alert['id'] == alert_id:
                alert['resolved'] = True
                alert['resolved_at'] = datetime.now().isoformat()
                self._save_alerts()
                return True
        return False
    
    def get_active_alerts(self) -> List[Dict]:
        """Get all unacknowledged alerts."""
        return [a for a in self.alerts if not a['acknowledged']]
    
    def get_alert_history(
        self,
        limit: int = 100,
        alert_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Get alert history with optional filtering.
        
        Args:
            limit: Maximum number of alerts to return
            alert_type: Optional filter by alert type
            
        Returns:
            Filtered alert history
        """
        filtered = self.alerts
        
        if alert_type:
            filtered = [a for a in filtered if a['alert_type'] == alert_type]
        
        # Sort by timestamp descending
        filtered = sorted(filtered, key=lambda x: x['timestamp'], reverse=True)
        
        return filtered[:limit]
    
    def get_monitoring_summary(self) -> Dict:
        """Get summary of monitoring status."""
        active_alerts = self.get_active_alerts()
        critical_alerts = [a for a in active_alerts if a['severity'] == 'critical']
        warning_alerts = [a for a in active_alerts if a['severity'] == 'warning']
        
        return {
            'portfolio_id': self.config.portfolio_id,
            'total_alerts': len(self.alerts),
            'active_alerts': len(active_alerts),
            'critical_alerts': len(critical_alerts),
            'warning_alerts': len(warning_alerts),
            'enabled_rules': len([r for r in self.rules if r['enabled']]),
            'last_check': datetime.now().isoformat()
        }


def create_monitoring_engine(
    portfolio_id: str,
    custom_thresholds: Optional[Dict] = None
) -> MonitoringEngine:
    """
    Convenience function to create a monitoring engine.
    
    Args:
        portfolio_id: Portfolio identifier
        custom_thresholds: Optional custom threshold configuration
        
    Returns:
        Configured monitoring engine
    """
    config = MonitoringConfig(portfolio_id=portfolio_id)
    
    if custom_thresholds:
        if 'performance' in custom_thresholds:
            config.performance_thresholds.update(custom_thresholds['performance'])
        if 'risk' in custom_thresholds:
            config.risk_thresholds.update(custom_thresholds['risk'])
        if 'position' in custom_thresholds:
            config.position_thresholds.update(custom_thresholds['position'])
    
    return MonitoringEngine(config)


# Example notification handlers
def console_notification_handler(alert: Alert):
    """Simple console notification handler."""
    print(f"[{alert.severity.upper()}] {alert.title}")
    print(f"  {alert.message}")
    print(f"  Time: {alert.timestamp}")
    print()


def email_notification_handler(alert: Alert, email_config: Dict):
    """Email notification handler (placeholder)."""
    # In production, this would send actual emails
    logger.info(f"Email notification would be sent for alert: {alert.title}")
    # Implementation would use smtplib or email API


if __name__ == "__main__":
    # Example usage
    config = MonitoringConfig(portfolio_id="demo_portfolio")
    engine = MonitoringEngine(config)
    
    # Add console notification handler
    engine.add_notification_handler(console_notification_handler)
    
    # Create some sample alert rules
    engine.create_alert_rule(
        name="High Drawdown Alert",
        alert_type="performance",
        condition="drawdown > 0.10",
        threshold=0.10,
        severity="critical"
    )
    
    # Simulate monitoring cycle
    sample_portfolio = {
        'positions': [
            {'ticker': 'AAPL', 'weight': 0.35},
            {'ticker': 'MSFT', 'weight': 0.30}
        ],
        'drawdown': -0.12
    }
    
    sample_returns = pd.Series([-0.02, -0.03, -0.01, 0.01, -0.04])
    sample_risk = {'var_95': -0.06}
    
    results = engine.run_monitoring_cycle(sample_portfolio, sample_returns, sample_risk)
    print(json.dumps(results, indent=2, default=str))