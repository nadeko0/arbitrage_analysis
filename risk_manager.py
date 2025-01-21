import numpy as np
from typing import Dict, List, Tuple, Any
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class AdvancedRiskManager:
    def __init__(self, 
                 max_position_size: Decimal, 
                 max_loss_percentage: Decimal,
                 volatility_lookback: int = 20,
                 max_daily_loss: Decimal = Decimal('0.02'),
                 max_drawdown: Decimal = Decimal('0.1')):
        self.max_position_size = max_position_size
        self.max_loss_percentage = max_loss_percentage
        self.volatility_lookback = volatility_lookback
        self.max_daily_loss = max_daily_loss
        self.max_drawdown = max_drawdown
        self.daily_pnl = Decimal('0')
        self.peak_value = Decimal('0')
        self.current_drawdown = Decimal('0')
        self.trades_history = []
        self.performance_metrics = {
            'win_rate': Decimal('0'),
            'profit_factor': Decimal('1'),
            'sharpe_ratio': Decimal('0'),
            'max_consecutive_losses': 0
        }

    def calculate_position_size(self, 
                                account_balance: Decimal, 
                                entry_price: Decimal, 
                                stop_loss: Decimal, 
                                volatility: float) -> Decimal:
        risk_amount = account_balance * self.max_loss_percentage
        price_difference = abs(entry_price - stop_loss)
        volatility_adjusted_size = risk_amount / (price_difference * Decimal(str(volatility)))
        
        # Adjust position size based on recent performance
        performance_factor = self.calculate_performance_factor()
        adjusted_size = volatility_adjusted_size * performance_factor
        
        return min(adjusted_size, self.max_position_size)

    def validate_trade(self, 
                       entry_price: Decimal, 
                       position_size: Decimal, 
                       stop_loss: Decimal, 
                       account_balance: Decimal) -> bool:
        if position_size > self.max_position_size:
            logger.warning(f"Position size {position_size} exceeds maximum allowed {self.max_position_size}")
            return False

        potential_loss = (entry_price - stop_loss) * position_size
        max_allowed_loss = account_balance * self.max_loss_percentage
        if potential_loss > max_allowed_loss:
            logger.warning(f"Potential loss {potential_loss} exceeds maximum allowed {max_allowed_loss}")
            return False

        if self.daily_pnl.copy_abs() + potential_loss > (account_balance * self.max_daily_loss):
            logger.warning("Trade exceeds maximum daily loss limit")
            return False

        if self.should_pause_trading():
            logger.warning("Trading paused due to risk limits")
            return False

        return True

    def update_daily_pnl(self, pnl: Decimal):
        self.daily_pnl += pnl
        logger.info(f"Updated daily PNL: {self.daily_pnl}")

    def reset_daily_pnl(self):
        self.daily_pnl = Decimal('0')
        logger.info("Daily PNL reset")

    def update_drawdown(self, account_value: Decimal) -> bool:
        if account_value > self.peak_value:
            self.peak_value = account_value
        
        self.current_drawdown = (self.peak_value - account_value) / self.peak_value
        if self.current_drawdown > self.max_drawdown:
            logger.warning(f"Maximum drawdown exceeded: {self.current_drawdown} > {self.max_drawdown}")
            return False
        return True

    def calculate_kelly_criterion(self, win_rate: float, avg_win: Decimal, avg_loss: Decimal) -> Decimal:
        if avg_loss == Decimal('0'):
            return Decimal('0')
        q = 1 - win_rate
        return (win_rate * avg_win - q * avg_loss) / avg_win

    def calculate_optimal_position_size(self, 
                                        account_balance: Decimal, 
                                        win_rate: float, 
                                        avg_win: Decimal, 
                                        avg_loss: Decimal) -> Decimal:
        kelly_percentage = self.calculate_kelly_criterion(win_rate, avg_win, avg_loss)
        return min(account_balance * kelly_percentage, self.max_position_size)

    def calculate_value_at_risk(self, 
                                position_size: Decimal, 
                                entry_price: Decimal, 
                                historical_returns: List[float], 
                                confidence_level: float = 0.95) -> Decimal:
        returns = np.array(historical_returns)
        var = np.percentile(returns, (1 - confidence_level) * 100)
        return position_size * entry_price * Decimal(str(abs(var)))

    def should_close_position(self, 
                              entry_price: Decimal, 
                              current_price: Decimal, 
                              stop_loss: Decimal, 
                              take_profit: Decimal) -> bool:
        if current_price <= stop_loss or current_price >= take_profit:
            return True
        return False

    def add_trade_to_history(self, trade: Dict[str, Any]):
        self.trades_history.append(trade)
        if len(self.trades_history) > 1000:
            self.trades_history.pop(0)
        self.update_performance_metrics()
        logger.info(f"Added trade to history. Total trades: {len(self.trades_history)}")

    def calculate_win_rate(self) -> float:
        if not self.trades_history:
            return 0.0
        winning_trades = sum(1 for trade in self.trades_history if trade['profit'] > 0)
        return winning_trades / len(self.trades_history)

    def calculate_risk_reward_ratio(self) -> Decimal:
        if not self.trades_history:
            return Decimal('0')
        avg_win = Decimal(sum(trade['profit'] for trade in self.trades_history if trade['profit'] > 0) / max(1, sum(1 for trade in self.trades_history if trade['profit'] > 0)))
        avg_loss = Decimal(abs(sum(trade['profit'] for trade in self.trades_history if trade['profit'] < 0)) / max(1, sum(1 for trade in self.trades_history if trade['profit'] < 0)))
        return avg_win / avg_loss if avg_loss != 0 else Decimal('0')

    def adjust_position_size_based_on_performance(self, base_position_size: Decimal) -> Decimal:
        performance_factor = self.calculate_performance_factor()
        adjusted_size = base_position_size * performance_factor
        logger.info(f"Adjusted position size from {base_position_size} to {adjusted_size}")
        return min(adjusted_size, self.max_position_size)

    def calculate_optimal_stop_loss(self, entry_price: Decimal, historical_volatility: float) -> Decimal:
        volatility_based_stop = entry_price * (Decimal('1') - Decimal(str(historical_volatility * 2)))
        max_loss_based_stop = entry_price * (Decimal('1') - self.max_loss_percentage)
        optimal_stop = max(volatility_based_stop, max_loss_based_stop)
        logger.info(f"Calculated optimal stop loss: {optimal_stop}")
        return optimal_stop

    def should_pause_trading(self) -> bool:
        if self.daily_pnl < -self.max_daily_loss:
            logger.warning("Daily loss limit reached. Pausing trading.")
            return True
        if self.current_drawdown > self.max_drawdown:
            logger.warning("Maximum drawdown exceeded. Pausing trading.")
            return True
        return False

    def update_performance_metrics(self):
        self.performance_metrics['win_rate'] = Decimal(str(self.calculate_win_rate()))
        self.performance_metrics['profit_factor'] = self.calculate_profit_factor()
        self.performance_metrics['sharpe_ratio'] = self.calculate_sharpe_ratio()
        self.performance_metrics['max_consecutive_losses'] = self.calculate_max_consecutive_losses()
        logger.info(f"Updated performance metrics: {self.performance_metrics}")

    def calculate_profit_factor(self) -> Decimal:
        total_profit = sum(trade['profit'] for trade in self.trades_history if trade['profit'] > 0)
        total_loss = abs(sum(trade['profit'] for trade in self.trades_history if trade['profit'] < 0))
        return Decimal(str(total_profit / total_loss)) if total_loss != 0 else Decimal('1')

    def calculate_sharpe_ratio(self, risk_free_rate: Decimal = Decimal('0.02')) -> Decimal:
        if not self.trades_history:
            return Decimal('0')
        returns = [Decimal(str(trade['profit'])) for trade in self.trades_history]
        avg_return = sum(returns) / len(returns)
        std_dev = Decimal(str(np.std(returns)))
        if std_dev == Decimal('0'):
            return Decimal('0')
        return (avg_return - risk_free_rate) / std_dev

    def calculate_max_consecutive_losses(self) -> int:
        max_losses = 0
        current_losses = 0
        for trade in self.trades_history:
            if trade['profit'] < 0:
                current_losses += 1
                max_losses = max(max_losses, current_losses)
            else:
                current_losses = 0
        return max_losses

    def calculate_performance_factor(self) -> Decimal:
        win_rate_factor = self.performance_metrics['win_rate']
        profit_factor_weight = Decimal('0.3')
        sharpe_ratio_weight = Decimal('0.3')
        consecutive_losses_weight = Decimal('0.2')

        profit_factor_component = min(self.performance_metrics['profit_factor'], Decimal('2')) / Decimal('2')
        sharpe_ratio_component = min(self.performance_metrics['sharpe_ratio'], Decimal('3')) / Decimal('3')
        consecutive_losses_component = Decimal('1') - (Decimal(str(self.performance_metrics['max_consecutive_losses'])) / Decimal('10'))

        performance_factor = (
            win_rate_factor +
            profit_factor_weight * profit_factor_component +
            sharpe_ratio_weight * sharpe_ratio_component +
            consecutive_losses_weight * consecutive_losses_component
        ) / (Decimal('1') + profit_factor_weight + sharpe_ratio_weight + consecutive_losses_weight)

        return max(min(performance_factor, Decimal('1.5')), Decimal('0.5'))

    def get_risk_report(self) -> Dict[str, Any]:
        return {
            'daily_pnl': float(self.daily_pnl),
            'current_drawdown': float(self.current_drawdown),
            'win_rate': float(self.performance_metrics['win_rate']),
            'profit_factor': float(self.performance_metrics['profit_factor']),
            'sharpe_ratio': float(self.performance_metrics['sharpe_ratio']),
            'max_consecutive_losses': self.performance_metrics['max_consecutive_losses'],
            'total_trades': len(self.trades_history)
        }

logger.info("AdvancedRiskManager initialized and ready for use.")