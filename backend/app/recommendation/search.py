"""Mean–variance allocation with simple historical risk reporting."""

import logging

import cvxpy as cp
import numpy as np
from pypfopt import EfficientFrontier, objective_functions
from pypfopt.exceptions import OptimizationError

from ..constants import ALLOCATION_MESSAGES, CASH_TICKER
from .portfolio import (
    MarketDataUnavailable, estimate_returns_and_covariance, historical_risk, validate_returns,
)

logger = logging.getLogger(__name__)


def cash_result(level, rules, reason):
    limits = rules['limits'][str(level)]
    if reason == 'zero_loss':
        limits = {'max_volatility': 0, 'max_drawdown': 0}
    return {CASH_TICKER: 100.0}, {
        'volatility_pct': None, 'max_drawdown_pct': None,
        'start_date': None, 'end_date': None, 'trading_days': 0,
        'estimated_return_pct': None, 'estimated_volatility_pct': None,
        'source': 'none', 'currency': rules['history']['currency'],
        'status': 'unallocated', 'reason': reason, 'explanation': ALLOCATION_MESSAGES[reason],
        'risk_limits': limits, 'weighted_expense_ratio_pct': 0.0,
        'uninvested_cash_pct': 100.0, 'excluded_tickers': [], 'method': 'mean_variance',
    }


def optimize_weights(level, funds, expected, covariance, rules):
    """Maximize estimated return subject to variance and concentration bounds."""
    caps = rules['diversification']
    tickers = list(expected.index)
    bounds = [(0, 1) if t == CASH_TICKER else
              (0, caps['max_cash_holding_pct' if funds[t]['sleeve'] == 'cash' else 'max_holding_pct'] / 100)
              for t in tickers]
    ef = EfficientFrontier(expected, covariance, weight_bounds=bounds, solver=rules['optimizer']['solver'])
    groups = {t: rules['sleeve_groups'][funds[t]['sleeve']] for t in funds}
    groups[CASH_TICKER] = 'cash'
    for group, cap in rules['asset_class_max_pct'][str(level)].items():
        mask = np.array([groups[t] == group for t in tickers], dtype=float)
        ef.add_constraint(lambda w, mask=mask, cap=cap: mask @ w <= cap / 100)
    categories = {(f['sleeve'] == 'cash', f['category']) for f in funds.values()}
    for cash, category in sorted(categories):
        mask = np.array([t != CASH_TICKER and (funds[t]['sleeve'] == 'cash', funds[t]['category']) == (cash, category)
                         for t in tickers], dtype=float)
        cap = caps['max_cash_category_pct' if cash else 'max_category_pct']
        ef.add_constraint(lambda w, mask=mask, cap=cap: mask @ w <= cap / 100)
    target = rules['limits'][str(level)]['max_volatility'] / 100
    ef.add_constraint(lambda w: objective_functions.portfolio_variance(w, covariance.to_numpy()) <= target ** 2)
    # Same objective/constraints as efficient_risk. Its pseudoinverse-based
    # minimum-volatility precheck mishandles a zero-variance cash asset, so use
    # PyPortfolioOpt's public convex API for this standard mean–variance problem.
    result = ef.convex_objective(objective_functions.portfolio_return, expected_returns=expected.to_numpy())
    weights = np.array([result[t] for t in tickers])
    tolerance = rules['optimizer']['tolerance']
    if (not np.isfinite(weights).all() or (weights < -tolerance).any()
            or abs(weights.sum() - 1) > tolerance
            or any(weights[i] > bound[1] + tolerance for i, bound in enumerate(bounds))):
        raise OptimizationError('Invalid optimizer weights')
    return weights


def round_weights(selected, settings):
    """Round fund percentages down and leave the small remainder in cash."""
    unit = 10 ** settings['weight_decimals']
    invested = np.floor(np.maximum(selected[:-1], 0) * 100 * unit) / unit
    invested[invested < settings['min_holding_pct']] = 0
    return np.r_[invested, round(100 - invested.sum(), settings['weight_decimals'])]


def choose_weights(level, candidates, returns, rules):
    try:
        validate_returns(returns, min_days=rules['history']['min_days'])
    except MarketDataUnavailable:
        return cash_result(level, rules, 'no_data')
    funds = {f['ticker']: f for group in candidates.values() for f in group if f['ticker'] in returns.columns}
    if not funds:
        return cash_result(level, rules, 'no_funds')
    returns = returns[sorted(funds)].copy()
    source = returns.attrs.get('source', 'live')
    limits = rules['limits'][str(level)]
    try:
        expected, covariance = estimate_returns_and_covariance(returns)
        expected.loc[CASH_TICKER] = 0.0
        covariance = covariance.reindex(index=expected.index, columns=expected.index, fill_value=0.0)
        selected = optimize_weights(level, funds, expected, covariance, rules)
        returns[CASH_TICKER] = 0.0
        weights_pct = round_weights(selected, rules['optimizer'])
    except (ValueError, OptimizationError, cp.error.SolverError, np.linalg.LinAlgError) as exc:
        logger.warning('Portfolio optimization failed: %s', exc)
        return cash_result(level, rules, 'optimizer_failed')

    weights = weights_pct / 100
    report = historical_risk(returns, weights)
    model_vol = float(np.sqrt(max(0.0, weights @ covariance.to_numpy() @ weights)) * 100)
    status = 'cash_only' if not weights_pct[:-1].any() else 'optimized'
    fees = sum(weights[i] * funds[t]['expense_ratio_pct'] for i, t in enumerate(returns.columns[:-1]))
    return {t: float(w) for t, w in zip(returns.columns, weights_pct) if w > 0}, report | {
        'estimated_return_pct': float(weights @ expected.to_numpy() * 100),
        'estimated_volatility_pct': model_vol,
        'source': source, 'currency': rules['history']['currency'],
        'status': status, 'reason': status, 'explanation': ALLOCATION_MESSAGES[status],
        'risk_limits': limits,
        'weighted_expense_ratio_pct': float(fees), 'uninvested_cash_pct': float(weights_pct[-1]),
        'excluded_tickers': [], 'method': 'mean_variance',
    }
