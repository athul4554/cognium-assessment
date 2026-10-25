import math
import statistics

import pandas as pd

from app.recommendation import market_data
from app.recommendation.market_data import _round, compute_metrics, get_daily_returns, get_metrics, load_snapshot


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


# Live data with snapshot fallback (yfinance is always mocked)

def snapshot_of(ticker) -> dict:
    return {k: v for k, v in load_snapshot()[ticker].items() if k != "ticker"} | {"source": "snapshot"}


def test_live_data_used(monkeypatch):
    close = pd.DataFrame({"IVV": prices([100.0] * 252 + [110.0])})
    monkeypatch.setattr(market_data.yf, "download", lambda *a, **kw: {"Close": close})

    m = get_metrics(["IVV"])

    assert m["IVV"]["source"] == "live"
    assert m["IVV"]["return_1y_pct"] == 10.0


def test_download_failure_uses_snapshot(monkeypatch):
    def fail(*a, **kw):
        raise ConnectionError("offline")

    monkeypatch.setattr(market_data.yf, "download", fail)

    assert get_metrics(["IVV", "VTI"]) == {"IVV": snapshot_of("IVV"), "VTI": snapshot_of("VTI")}


def test_one_ticker_failure_uses_snapshot(monkeypatch):
    close = pd.DataFrame({
        "IVV": prices([100.0] * 252 + [110.0]),
        "VTI": prices([float("nan")] * 253),
    })
    monkeypatch.setattr(market_data.yf, "download", lambda *a, **kw: {"Close": close})

    m = get_metrics(["IVV", "VTI"])

    assert m["IVV"]["source"] == "live"
    assert m["VTI"] == snapshot_of("VTI")


# Daily returns for weighting the picks (yfinance is always mocked)

def test_daily_returns(monkeypatch):
    close = pd.DataFrame({"IVV": prices([100.0] * 252 + [110.0]), "AGG": prices([50.0] * 253)})
    monkeypatch.setattr(market_data.yf, "download", lambda *a, **kw: {"Close": close})

    r = get_daily_returns(["IVV", "AGG"])

    assert list(r.columns) == ["IVV", "AGG"]
    assert len(r) == 252
    assert r["IVV"].iloc[-1] == 0.1 and r["AGG"].sum() == 0


def test_daily_returns_download_failure_is_none(monkeypatch):
    def fail(*a, **kw):
        raise ConnectionError("offline")

    monkeypatch.setattr(market_data.yf, "download", fail)

    assert get_daily_returns(["IVV"]) is None


def test_daily_returns_short_history_is_none(monkeypatch):
    # One ticker with no prices leaves no common days
    close = pd.DataFrame({"IVV": prices([100.0] * 253), "VTI": prices([float("nan")] * 253)})
    monkeypatch.setattr(market_data.yf, "download", lambda *a, **kw: {"Close": close})

    assert get_daily_returns(["IVV", "VTI"]) is None
