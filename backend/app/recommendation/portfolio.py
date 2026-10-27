"""Return, covariance and simple historical portfolio-risk calculations."""

import numpy as np
import pandas as pd
from pypfopt import risk_models

from ..constants import TRADING_DAYS_PER_YEAR


class MarketDataUnavailable(ValueError):
    pass


def validate_returns(returns, min_days=2):
    if (
        returns is None or returns.empty or len(returns) < min_days
        or not isinstance(returns.index, pd.DatetimeIndex)
        or not returns.index.is_monotonic_increasing or not returns.index.is_unique
        or not returns.columns.is_unique
        or not np.isfinite(returns.to_numpy()).all()
        or (returns.to_numpy() <= -1).any()
    ):
        raise MarketDataUnavailable("Invalid or missing daily price history")


def estimate_returns_and_covariance(returns):
    """Annual arithmetic return estimates and a stabilized covariance matrix."""
    expected = returns.mean() * TRADING_DAYS_PER_YEAR
    covariance = risk_models.CovarianceShrinkage(
        returns, returns_data=True, frequency=TRADING_DAYS_PER_YEAR
    ).ledoit_wolf()
    return expected, covariance


def historical_risk(returns, weights):
    """Historical volatility and drawdown for constant target weights."""
    weights = np.asarray(weights)
    if (
        weights.shape != (returns.shape[1],)
        or not np.isfinite(weights).all() or (weights < 0).any()
        or not np.isclose(weights.sum(), 1)
    ):
        raise ValueError("Portfolio weights must be nonnegative and sum to one")

    daily = returns.to_numpy() @ weights
    nav = np.r_[1.0, np.cumprod(1 + daily)]
    return {
        "volatility_pct": float(daily.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR) * 100),
        "max_drawdown_pct": float(-(nav / np.maximum.accumulate(nav) - 1).min() * 100),
        "start_date": returns.index[0].date().isoformat(),
        "end_date": returns.index[-1].date().isoformat(),
        "trading_days": len(daily),
    }
