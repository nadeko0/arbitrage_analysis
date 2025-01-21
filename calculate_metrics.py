from scipy import stats
import numpy as np
import logging
from typing import List, Dict, Optional

logger = logging.getLogger("volatility")

def calculate_log_returns(prices: List[float]) -> Optional[np.ndarray]:
    prices_np = np.array(prices)
    if prices_np.size < 2 or np.any(prices_np <= 0):
        logger.warning("Invalid price data for log returns calculation")
        return None
    return np.diff(np.log(prices_np))

def calculate_adr(prices: np.ndarray, period: int = 24) -> float:
    daily_ranges = []
    for i in range(0, len(prices) - period + 1, period):
        daily_prices = prices[i:i+period]
        daily_range = np.max(daily_prices) - np.min(daily_prices)
        daily_ranges.append(daily_range)
    return np.mean(daily_ranges) if daily_ranges else np.nan

def safe_division(numerator: float, denominator: float, default: float = np.nan) -> float:
    return numerator / denominator if denominator != 0 else default

def calculate_all_metrics(prices: List[float], risk_free_rate: float = 0, target_return: float = 0) -> Dict[str, float]:
    log_returns = calculate_log_returns(prices)
    if log_returns is None or len(log_returns) < 2:  # Need at least 2 points for statistical calculations
        return {}

    prices_np = np.array(prices)
    returns = np.diff(prices_np) / prices_np[:-1]

    # Pre-calculate returns above/below target for omega ratio
    returns_above = returns[returns > target_return]
    returns_below = returns[returns < target_return]
    
    # Only calculate statistical moments if we have enough variation in the data
    price_std = np.std(prices_np)
    price_range = np.ptp(prices_np)
    can_calculate_moments = price_std > 1e-8 and price_range > 1e-8

    metrics = {
        "volatility": np.nanstd(log_returns, ddof=1) * np.sqrt(240) if len(log_returns) > 1 else np.nan,
        "adr": calculate_adr(prices_np),
        "mean_deviation": np.nanmean(np.abs(prices_np - np.nanmean(prices_np))),
        "roc": safe_division(prices_np[-1] - prices_np[0], prices_np[0]),
        "max_drawdown": np.nanmax((np.maximum.accumulate(prices_np) - prices_np) / np.maximum.accumulate(prices_np)),
        "sharpe_ratio": safe_division(np.nanmean(returns) - risk_free_rate/252, np.nanstd(returns, ddof=1)) * np.sqrt(252),
        "var": np.percentile(log_returns, 5) if len(log_returns) > 1 else np.nan,
        "cvar": np.nanmean(log_returns[log_returns <= np.percentile(log_returns, 5)]) if len(log_returns) > 1 else np.nan,
        "calmar_ratio": safe_division(np.nanmean(log_returns) * 240, np.nanmax((np.maximum.accumulate(prices_np) - prices_np) / np.maximum.accumulate(prices_np))),
        "sortino_ratio": safe_division(np.nanmean(returns) - risk_free_rate/252, np.nanstd(returns[returns < 0], ddof=1)) * np.sqrt(252),
        "momentum": prices_np[-1] - prices_np[-14] if len(prices_np) >= 14 else np.nan,
        "cumulative_return": safe_division(prices_np[-1] - prices_np[0], prices_np[0]),
        "omega_ratio": safe_division(
            np.nanmean(returns_above) if len(returns_above) > 0 else 0,
            np.abs(np.nanmean(returns_below)) if len(returns_below) > 0 else 1
        ),
        "hurst_exponent": calculate_hurst_exponent(prices_np),
        "autocorrelation": np.corrcoef(prices_np[:-1], prices_np[1:])[0, 1] if len(prices_np) > 1 else np.nan,
        "kurtosis": stats.kurtosis(prices_np) if can_calculate_moments else np.nan,
        "skewness": stats.skew(prices_np) if can_calculate_moments else np.nan,
        "fractal_dimension": calculate_fractal_dimension(prices_np)
    }

    return {k: v for k, v in metrics.items() if not np.isnan(v) and not np.isinf(v)}

def calculate_hurst_exponent(prices: np.ndarray) -> float:
    lags = range(2, min(100, len(prices) // 2))
    tau = [np.std(np.subtract(prices[lag:], prices[:-lag])) for lag in lags]
    
    # Add a small constant to avoid log(0)
    epsilon = 1e-8
    log_lags = np.log(np.array(lags) + epsilon)
    log_tau = np.log(np.array(tau) + epsilon)
    
    reg = np.polyfit(log_lags, log_tau, 1)
    return reg[0] * 2.0

def calculate_fractal_dimension(prices: np.ndarray) -> float:
    n = len(prices)
    lag = 2
    while n >= lag:
        rescaled_range = np.max(prices[:lag]) - np.min(prices[:lag])
        lag *= 2
    return np.log(n) / np.log(lag / 2) if lag > 2 else np.nan