import math
import statistics

import pandas as pd
import pytest

from app.recommendation import market_data
from app.recommendation.market_data import _round, compute_metrics, get_price_history, get_metrics


@pytest.fixture(autouse=True)
def isolated_history(monkeypatch, tmp_path):
    monkeypatch.setattr(market_data.c, 'PRICE_HISTORY_PATH', tmp_path / 'history.json')


def prices(values) -> pd.Series:
    return pd.Series(values, index=pd.bdate_range("2023-01-02", periods=len(values)), dtype=float)


# Metrics from a price series

def test_one_year_or_less_returns_none():
    assert compute_metrics(prices([100.0] * 252)) is None


def test_metrics_from_known_series():
    close = prices([100.0] * 252 + [110.0])
    years = (close.index[-1] - close.index[0]).days / 365.25
    vol = statistics.stdev([0.0] * 251 + [0.1]) * math.sqrt(252) * 100

    m = compute_metrics(close)

    assert m["last_close"] == 110.0
    assert m["last_close_date"] == close.index[-1].date().isoformat()
    assert m["return_1y_pct"] == 10.0
    assert m["return_3y_annualised_pct"] == round((1.1 ** (1 / years) - 1) * 100, 2)
    assert m["volatility_1y_pct"] == round(vol, 2)
    assert m["max_drawdown_3y_pct"] == 0.0


def test_max_drawdown():
    m = compute_metrics(prices([100.0] * 100 + [50.0] * 100 + [110.0] * 100))

    assert m["max_drawdown_3y_pct"] == -50.0


def test_nan_prices_dropped():
    gappy = prices([100.0] * 253 + [110.0])
    gappy.iloc[10] = float("nan")

    assert compute_metrics(gappy) == compute_metrics(gappy.drop(gappy.index[10]))
    # 252 real prices plus a gap is still under a year
    assert compute_metrics(prices([100.0] * 251 + [float("nan"), 110.0])) is None


def test_nan_result_becomes_null():
    assert _round(float("nan")) is None
    assert _round(1.234) == 1.23


# Display metrics reuse allocation prices without another download.

@pytest.mark.parametrize('source', ['live', 'saved'])
def test_metrics_reuse_prices(monkeypatch, source):
    close = pd.DataFrame({"IVV": prices([100.0] * 252 + [110.0])})
    close.attrs['source'] = source
    def unexpected(*a, **kw):
        raise AssertionError('Display metrics must not download prices')
    monkeypatch.setattr(market_data.yf, 'download', unexpected)
    metrics = get_metrics(close)
    assert metrics['IVV']['source'] == source
    assert metrics['IVV']['return_1y_pct'] == 10.0


# Aligned price history for allocation (yfinance is always mocked)

def test_price_history_and_daily_returns(monkeypatch):
    close = pd.DataFrame({"IVV": prices([100.0] * 252 + [110.0]), "AGG": prices([50.0] * 253)})
    monkeypatch.setattr(market_data.yf, "download", lambda *a, **kw: {"Close": close})

    r = get_price_history(["IVV", "AGG"])

    assert list(r.columns) == ["IVV", "AGG"]
    assert len(r) == 253
    daily = r.pct_change(fill_method=None).iloc[1:]
    assert math.isclose(daily["IVV"].iloc[-1], 0.1) and daily["AGG"].sum() == 0


def test_daily_returns_download_failure_is_none(monkeypatch):
    def fail(*a, **kw):
        raise ConnectionError("offline")

    monkeypatch.setattr(market_data.yf, "download", fail)

    assert get_price_history(["IVV"]) is None


def test_failed_candidate_is_excluded_without_losing_good_data(monkeypatch):
    # Bad candidates are excluded instead of destroying the common history
    close = pd.DataFrame({"IVV": prices([100.0] * 253), "VTI": prices([float("nan")] * 253)})
    monkeypatch.setattr(market_data.yf, "download", lambda *a, **kw: {"Close": close})

    r = get_price_history(["IVV", "VTI"])
    assert list(r.columns) == ["IVV"]
    assert len(r) == 253


def test_daily_returns_rejects_short_history(monkeypatch):
    close = pd.DataFrame({"IVV": prices([100.0] * 300)})
    monkeypatch.setattr(market_data.yf, "download", lambda *a, **kw: {"Close": close})
    assert get_price_history(["IVV"], min_days=504) is None


def test_daily_returns_excludes_gaps_and_nonpositive_prices(monkeypatch):
    close = pd.DataFrame({t: prices([100.0] * 600) for t in ["OK", "GAP", "ZERO"]})
    close.loc[close.index[100], "GAP"] = float("nan")
    close.loc[close.index[100], "ZERO"] = 0
    monkeypatch.setattr(market_data.yf, "download", lambda *a, **kw: {"Close": close})
    r = get_price_history(["OK", "GAP", "ZERO"], min_days=504)
    assert list(r.columns) == ["OK"]
    assert len(r) == 600


def test_daily_returns_aligns_different_inception_dates(monkeypatch):
    close = pd.DataFrame({"A": prices([100.0] * 600), "B": prices([float("nan")] * 20 + [100.0] * 580)})
    monkeypatch.setattr(market_data.yf, "download", lambda *a, **kw: {"Close": close})
    r = get_price_history(["A", "B"], min_days=504)
    assert len(r) == 580
    assert not r.isna().any().any()


def test_missing_optional_display_metrics_does_not_fail_allocation():
    assert get_metrics(None) == {}
    assert get_metrics(pd.DataFrame()) == {}


def test_live_history_is_saved_and_reused_offline(monkeypatch):
    close = pd.DataFrame({'IVV': prices([100.0] * 300 + [110.0])})
    monkeypatch.setattr(market_data.yf, 'download', lambda *a, **kw: {'Close': close})
    live = get_price_history(['IVV'])
    assert live.attrs['source'] == 'live'
    def fail(*a, **kw):
        raise ConnectionError('offline')
    monkeypatch.setattr(market_data.yf, 'download', fail)
    saved = get_price_history(['IVV'])
    assert saved.attrs['source'] == 'saved'
    pd.testing.assert_frame_equal(saved, live, check_freq=False, check_dtype=False)
    assert saved.index[-1] == close.index[-1]
    assert get_metrics(saved)['IVV']['source'] == 'saved'


def test_empty_download_does_not_overwrite_saved_prices(monkeypatch):
    close = pd.DataFrame({'IVV': prices([100.0] * 300)})
    market_data.save_price_history(close)
    before = market_data.c.PRICE_HISTORY_PATH.read_bytes()
    monkeypatch.setattr(market_data.yf, 'download', lambda *a, **kw: {'Close': pd.DataFrame()})
    assert get_price_history(['IVV']).attrs['source'] == 'saved'
    assert market_data.c.PRICE_HISTORY_PATH.read_bytes() == before


def test_corrupt_cache_does_not_break_fallback(monkeypatch):
    market_data.c.PRICE_HISTORY_PATH.write_text('not-json')
    monkeypatch.setattr(market_data.yf, 'download', lambda *a, **kw: {'Close': pd.DataFrame()})
    assert get_price_history(['IVV']) is None


def test_saving_subset_retains_other_cached_funds():
    market_data.save_price_history(pd.DataFrame({'A': prices([100.0] * 300), 'B': prices([50.0] * 300)}))
    market_data.save_price_history(pd.DataFrame({'A': prices([120.0] * 300)}))
    cached = market_data.load_price_history()
    assert set(cached.columns) == {'A', 'B'}
    assert cached['A'].iloc[-1] == 120
    assert cached['B'].iloc[-1] == 50


@pytest.mark.parametrize('source', ['live', 'saved'])
def test_recommendation_reuses_one_download_for_all_metrics(monkeypatch, source):
    from decimal import Decimal
    from types import SimpleNamespace
    from unittest.mock import Mock
    from uuid import uuid4

    from app.recommendation.router import build
    from app.schemas import Holding, PortfolioMetrics

    close = pd.DataFrame({'IVV': prices([100.0 * 1.001 ** day for day in range(301)])})
    if source == 'saved':
        market_data.save_price_history(close)
        download = Mock(side_effect=ConnectionError('offline'))
    else:
        download = Mock(return_value={'Close': close})
    monkeypatch.setattr(market_data.yf, 'download', download)
    assessment = SimpleNamespace(user_id='test', currency='USD', exclusions=[],
                                 invest_amount=Decimal('10000'), monthly_amount=Decimal('500'), max_loss='5')
    result = build(assessment, SimpleNamespace(id=uuid4(), level=1))

    download.assert_called_once()
    assert PortfolioMetrics.model_validate(result.portfolio).source == source
    invested = [Holding.model_validate(h) for h in result.holdings if h['ticker']]
    assert [h.ticker for h in invested] == ['IVV']
    assert invested[0].metrics.source == source
    assert invested[0].metrics.last_close_date == close.index[-1].date()
    assert invested[0].metrics.return_1y_pct == compute_metrics(close['IVV'])['return_1y_pct']
    assert result.portfolio['end_date'] == close.index[-1].date().isoformat()
