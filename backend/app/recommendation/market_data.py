import json
import logging
import math
from functools import lru_cache
from typing import Any

import yfinance as yf

from .. import constants as c

logger = logging.getLogger(__name__)


@lru_cache
def load_snapshot() -> dict[str, dict]:
    with open(c.SNAPSHOT_PATH, encoding="utf-8") as f:
        return {p["ticker"]: p for p in json.load(f)["prices"]}


def _round(value: float) -> float | None:
    # NaN isn't valid JSON, so it goes out as null
    return None if math.isnan(value) else round(value, 2)


def compute_metrics(close) -> dict[str, Any] | None:
    close = close.dropna()
    days = c.TRADING_DAYS_PER_YEAR
    if len(close) <= days:
        return None

    last = float(close.iloc[-1])
    years = (close.index[-1] - close.index[0]).days / 365.25
    daily_returns = close.iloc[-(days + 1):].pct_change().dropna()

    return {
        "last_close": _round(last),
        "last_close_date": close.index[-1].date().isoformat(),
        "return_1y_pct": _round((last / float(close.iloc[-(days + 1)]) - 1) * 100),
        "return_3y_annualised_pct": _round(((last / float(close.iloc[0])) ** (1 / years) - 1) * 100),
        "volatility_1y_pct": _round(float(daily_returns.std()) * math.sqrt(days) * 100),
        "max_drawdown_3y_pct": _round(float((close / close.cummax() - 1).min()) * 100),
    }


def get_metrics(tickers: list[str]) -> dict[str, dict]:
    """Live metrics from yfinance, the snapshot for any ticker that fails."""
    try:
        close = yf.download(
            tickers,
            period=c.MARKET_DATA_PERIOD,
            auto_adjust=True,
            progress=False,
            timeout=c.MARKET_DATA_TIMEOUT_SECONDS,
        )["Close"]
    except Exception as exc:
        logger.warning("yfinance download failed: %s", exc)
        close = None

    metrics = {}
    for ticker in tickers:
        live = None
        try:
            live = compute_metrics(close[ticker])
        except Exception as exc:
            logger.warning("No live prices for %s: %s", ticker, exc)
        if live:
            metrics[ticker] = live | {"source": "live"}
        else:
            snapshot = {k: v for k, v in load_snapshot()[ticker].items() if k != "ticker"}
            metrics[ticker] = snapshot | {"source": "snapshot"}
    return metrics
