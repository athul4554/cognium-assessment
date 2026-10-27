import copy
from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from app.recommendation import builder, search
from app.recommendation.builder import allocate_amounts, build_recommendation, eligible, group_weights, load_rules, load_universe
from app.recommendation.portfolio import (
    MarketDataUnavailable, estimate_returns_and_covariance, historical_risk, validate_returns,
)
from app.recommendation.search import choose_weights, optimize_weights
from app.constants import CASH_TICKER
from pypfopt.exceptions import OptimizationError
from app.schemas import PortfolioMetrics


def returns(**series):
    return pd.DataFrame(series, index=pd.bdate_range('2023-01-02', periods=len(next(iter(series.values())))))


def fund(ticker, fee=0.1):
    return {'ticker': ticker, 'category': ticker, 'sleeve': 'us_equity', 'expense_ratio_pct': fee}


def simple_rules():
    rules = copy.deepcopy(load_rules())
    rules['diversification'].update(max_holding_pct=100, max_category_pct=100)
    rules['asset_class_max_pct']['1']['equity'] = 100
    return rules


def test_first_day_loss_is_in_drawdown():
    metrics = historical_risk(returns(A=[-0.5, 0.0, 1.0]), [1.0])
    assert metrics['max_drawdown_pct'] == pytest.approx(50)


def test_historical_risk_uses_weighted_daily_returns():
    r = returns(A=[0.1, 0.0], B=[0.0, -0.1])
    metrics = historical_risk(r, [0.5, 0.5])
    daily = np.array([0.05, -0.05])
    nav = np.r_[1.0, np.cumprod(1 + daily)]
    assert metrics['volatility_pct'] == pytest.approx(daily.std(ddof=1) * np.sqrt(252) * 100)
    assert metrics['max_drawdown_pct'] == pytest.approx(-(nav / np.maximum.accumulate(nav) - 1).min() * 100)
    assert metrics['trading_days'] == 2
    assert 'historical_return_pct' not in metrics
    assert 'annual_turnover_pct' not in metrics


def test_risk_uses_combined_path_not_average_fund_risk():
    r = returns(A=[0.1, -0.1], B=[-0.1, 0.1])
    combined = historical_risk(r, [0.5, 0.5])
    a = historical_risk(r, [1.0, 0.0])
    b = historical_risk(r, [0.0, 1.0])
    assert combined['max_drawdown_pct'] == pytest.approx(0)
    assert combined['volatility_pct'] != pytest.approx((a['volatility_pct'] + b['volatility_pct']) / 2)


def test_full_period_volatility_includes_old_shock():
    r = returns(A=[-0.2] + [0.0] * 600)
    metrics = historical_risk(r, [1.0])
    assert metrics['volatility_pct'] > 0


@pytest.mark.parametrize('r', [None, pd.DataFrame(), returns(A=[0.0, np.nan]),
                              returns(A=[0.0, np.inf]), returns(A=[-1.0, 0.0])])
def test_missing_or_invalid_history_never_uses_snapshot(r):
    with pytest.raises(MarketDataUnavailable):
        validate_returns(r)


def test_invalid_weights_cannot_be_treated_as_uninvested_cash():
    with pytest.raises(ValueError):
        historical_risk(returns(A=[0.0, 0.0]), [0.4])


def test_return_and_covariance_estimates_use_daily_returns():
    shocks = np.tile([0.01, -0.01], 300)
    r = returns(A=0.0005 + shocks, B=0.0002 - shocks)
    expected, covariance = estimate_returns_and_covariance(r)
    assert expected['A'] == pytest.approx(0.0005 * 252)
    assert expected['B'] == pytest.approx(0.0002 * 252)
    assert covariance.loc['A', 'B'] < 0
    assert np.linalg.eigvalsh(covariance).min() >= -1e-10


def test_standard_optimizer_uses_cash_to_meet_risk_budget():
    rules = simple_rules()
    rules['limits']['1']['max_volatility'] = 10
    expected = pd.Series({'A': 0.10, CASH_TICKER: 0.0})
    covariance = pd.DataFrame([[0.04, 0], [0, 0]], index=expected.index, columns=expected.index)
    weights = optimize_weights(1, {'A': fund('A')}, expected, covariance, rules)
    # 50% of a 20%-volatility asset gives the highest return at 10% volatility.
    assert weights == pytest.approx([0.5, 0.5], abs=1e-4)


def test_negative_covariance_allows_more_investment_than_positive():
    rules = simple_rules()
    rules['limits']['1']['max_volatility'] = 10
    expected = pd.Series({'A': 0.12, 'B': 0.08, CASH_TICKER: 0.0})
    funds = {t: fund(t) for t in ['A', 'B']}
    results = []
    for correlation in [-0.8, 0.8]:
        covariance = pd.DataFrame([[0.04, 0.04 * correlation, 0],
                                   [0.04 * correlation, 0.04, 0], [0, 0, 0]],
                                  index=expected.index, columns=expected.index)
        weights = optimize_weights(1, funds, expected, covariance, rules)
        results.append((weights, float(weights @ expected.to_numpy())))
        assert np.sqrt(weights @ covariance.to_numpy() @ weights) <= 0.10001
    assert results[0][0][1] > 0.1  # Lower-return B is useful as a diversifier.
    assert results[0][1] > results[1][1]
    assert results[0][0][-1] < results[1][0][-1]


def test_historical_drawdown_is_reported_without_changing_weights():
    rules = simple_rules()
    rules['limits']['1'] = {'max_volatility': 100, 'max_drawdown': 5}
    r = returns(A=[0.001] * 400 + [-0.5] + [0.001] * 355)
    weights, report = choose_weights(1, {'assets': [fund('A')]}, r, rules)
    assert report['status'] == 'optimized'
    assert weights['A'] == pytest.approx(100, abs=1e-3)
    assert report['max_drawdown_pct'] > 5
    assert 'risk_targets_met' not in report


def test_one_year_history_does_not_require_separate_holdout():
    r = returns(A=[0.001, -0.0005] * 126)
    _, report = choose_weights(1, {'assets': [fund('A')]}, r, simple_rules())
    assert report['volatility_pct'] is not None
    assert report['trading_days'] == 252


def test_optimizer_failure_returns_honest_unallocated_result(monkeypatch):
    def fail(*args):
        raise OptimizationError('test failure')
    monkeypatch.setattr(search, 'optimize_weights', fail)
    weights, report = choose_weights(1, {'assets': [fund('A')]}, returns(A=[0.001] * 300), simple_rules())
    assert weights == {CASH_TICKER: 100}
    assert report['reason'] == 'optimizer_failed'
    assert 'risk_targets_met' not in report
    assert 'historical_return_pct' not in report


def test_negative_return_estimates_can_select_cash():
    weights, report = choose_weights(1, {'assets': [fund('A')]}, returns(A=[-0.001] * 300), simple_rules())
    assert weights == {CASH_TICKER: 100}
    assert report['status'] == 'cash_only'


@pytest.mark.parametrize('exclusions', [[], ['no_crypto'], ['esg_preference'], ['sharia_compliant']])
def test_eligibility_preserves_preferences(exclusions):
    for bucket in load_rules()['buckets']:
        funds = eligible(bucket, exclusions, load_universe())
        for f in funds:
            assert f['currency'] == 'USD'
            assert f['sharia_compliant'] == ('sharia_compliant' in exclusions)
            assert f['ticker'] not in load_rules()['exclude_tickers']
            assert f['region'] in load_rules()['regions']
            assert date.fromisoformat(f['inception_date']) <= date(2023, 9, 16)
            if 'no_crypto' in exclusions:
                assert not f['crypto']
            if 'esg_preference' not in exclusions:
                assert not f['esg']


def test_esg_filters_only_buckets_with_esg_options():
    assert all(f['esg'] for f in eligible('us_equity', ['esg_preference'], load_universe()))
    assert eligible('cash', ['esg_preference'], load_universe())


@pytest.fixture
def offline(monkeypatch):
    def history(tickers, min_days):
        rng = np.random.default_rng(10)
        daily = returns(**{t: 0.0002 + rng.normal(0, 0.002, 756) for t in tickers})
        initial = pd.DataFrame(100.0, index=[daily.index[0] - pd.offsets.BDay()], columns=tickers)
        return pd.concat([initial, 100 * (1 + daily).cumprod()])
    monkeypatch.setattr(builder, 'get_price_history', history)
    return load_rules()


@pytest.mark.parametrize('level', [1, 2, 3, 4, 5])
def test_complete_portfolio_obeys_limits_amounts_and_schema(level, offline):
    rec = build_recommendation(level, [], Decimal('10000.01'), Decimal('500.07'))
    holdings = rec['holdings']
    assert sum(h['weight'] for h in holdings) == pytest.approx(100)
    assert sum(Decimal(str(h['amount'])) for h in holdings) == Decimal('10000.01')
    assert sum(Decimal(str(h['monthly_amount'])) for h in holdings) == Decimal('500.07')
    for h in holdings:
        assert h['weight'] >= 0
        if h['ticker']:
            assert h['weight'] <= (40 if h['sleeve'] == 'cash' else 30)
    for group, cap in offline['asset_class_max_pct'][str(level)].items():
        assert sum(h['weight'] for h in holdings if h['group'] == group) <= cap + 1e-4
    categories = {}
    for h in holdings:
        if h['ticker']:
            key = (h['sleeve'] == 'cash', h['category'])
            categories[key] = categories.get(key, 0) + h['weight']
    assert all(w <= (40 if cash else 35) + 1e-4 for (cash, _), w in categories.items())
    report = PortfolioMetrics.model_validate(rec['portfolio'])
    limits = offline['limits'][str(level)]
    assert report.estimated_volatility_pct <= limits['max_volatility']
    assert report.volatility_pct is not None
    assert report.max_drawdown_pct is not None
    assert report.source == 'live'
    assert rec['rules_version'] == '1.4.0'


def test_sharia_portfolio_respects_exclusions_and_includes_sukuk(offline):
    assert 'SPSK' in {f['ticker'] for f in eligible('bonds', ['sharia_compliant'], load_universe())}
    rec = build_recommendation(3, ['sharia_compliant'], Decimal('10000'), Decimal('0'))
    assert all(h['sharia_compliant'] for h in rec['holdings'] if h['ticker'])
    assert sum(h['weight'] for h in rec['holdings']) == pytest.approx(100)


def test_download_failure_returns_cash_without_fabricated_metrics(monkeypatch):
    monkeypatch.setattr(builder, 'get_price_history', lambda *a, **kw: None)
    rec = build_recommendation(3, [], Decimal('10000'), Decimal('0'))
    assert len(rec['holdings']) == 1
    assert rec['holdings'][0]['ticker'] is None
    assert rec['holdings'][0]['amount'] == 10000
    report = PortfolioMetrics.model_validate(rec['portfolio'])
    assert report.reason == 'no_data'
    assert report.volatility_pct is None


def test_zero_loss_answer_skips_market_data_and_keeps_cash(monkeypatch):
    def unexpected(*a, **kw):
        raise AssertionError('Zero-loss illustration must not require Yahoo')
    monkeypatch.setattr(builder, 'get_price_history', unexpected)
    rec = build_recommendation(1, [], Decimal('10000'), Decimal('500'), max_loss='0')
    assert rec['portfolio']['reason'] == 'zero_loss'
    assert rec['holdings'][0]['ticker'] is None
    assert rec['holdings'][0]['weight'] == 100


def test_missing_eligible_funds_returns_unallocated_cash(monkeypatch):
    monkeypatch.setattr(builder, 'eligible', lambda *a: [])
    rec = build_recommendation(1, [], Decimal('10000'), Decimal('0'))
    assert rec['portfolio']['reason'] == 'no_funds'
    assert rec['holdings'][0]['weight'] == 100


def test_amounts_allocate_residual_cents():
    holdings = [{'weight': 33.3333}, {'weight': 33.3333}, {'weight': 33.3334}]
    allocate_amounts(holdings, Decimal('0.10'), 'amount')
    assert [h['amount'] for h in holdings] == [0.03, 0.03, 0.04]


def test_amounts_distribute_half_cent_without_losing_total():
    holdings = [{'weight': 5}, {'weight': 95}]
    allocate_amounts(holdings, Decimal('0.10'), 'amount')
    assert [h['amount'] for h in holdings] == [0.01, 0.09]


def test_group_weights_follow_rules_order():
    holdings = [dict(group=g, weight=w, amount=w * 10, monthly_amount=w) for g, w in
                [('cash', 20), ('equity', 50), ('equity', 30)]]
    assert group_weights(holdings) == [
        dict(group='equity', weight=80, amount=800, monthly_amount=80),
        dict(group='cash', weight=20, amount=200, monthly_amount=20),
    ]
