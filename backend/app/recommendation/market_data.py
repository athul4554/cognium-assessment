import json
import logging
import math
import os
import tempfile
from datetime import date, timedelta
from io import StringIO
from typing import Any

import yfinance as yf
import numpy as np
import pandas as pd

from .. import constants as c

logger = logging.getLogger(__name__)


def _round(value: float) -> float | None:
    # NaN isn't valid JSON, so it goes out as null
    return None if not math.isfinite(value) else round(value, 2)


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


def get_metrics(close) -> dict[str, dict]:
    """Fund display metrics from the same prices used for allocation."""
    if close is None:
        return {}
    source = close.attrs.get("source", "live")
    return {
        ticker: metrics | {"source": source}
        for ticker in close
        if (metrics := compute_metrics(close[ticker])) is not None
    }


def load_price_history():
    try:
        payload = json.loads(c.PRICE_HISTORY_PATH.read_text())
        return pd.read_json(StringIO(json.dumps(payload)), orient="split")
    except (OSError, ValueError, TypeError, KeyError):
        return pd.DataFrame()


def save_price_history(close):
    """Keep a complete series per ticker; never splice adjusted price series."""
    previous = load_price_history()
    combined = previous.drop(columns=close.columns, errors="ignore").join(close, how="outer")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=c.PRICE_HISTORY_PATH.parent, delete=False) as handle:
            temp_path = handle.name
            handle.write(combined.to_json(orient="split", date_format="iso", double_precision=10))
        os.replace(temp_path, c.PRICE_HISTORY_PATH)
    except OSError as exc:
        logger.warning("Could not save price history: %s", exc)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def aligned_prices(close, tickers, min_days):
    if close is None or close.empty:
        return None
    if isinstance(close, pd.Series):
        close = close.to_frame(tickers[0])
    if not isinstance(close.index, pd.DatetimeIndex) or not close.index.is_unique:
        return None
    close = close.reindex(columns=tickers).sort_index()
    close = close.where(np.isfinite(close) & (close > 0))
    close = close.loc[:, close.count() >= min_days + 1]
    if close.empty:
        return None
    start = max(close[t].first_valid_index() for t in close)
    end = min(close[t].last_valid_index() for t in close)
    # Exclude gaps, never fabricate a daily return by bridging missing dates.
    close = close.loc[start:end].dropna(axis=1)
    return close if not close.empty and len(close) > min_days else None


def get_price_history(tickers: list[str], min_days: int = c.TRADING_DAYS_PER_YEAR):
    """Load aligned adjusted prices from Yahoo, falling back to saved history."""
    if not tickers:
        return None
    try:
        downloaded = yf.download(
            tickers,
            start=(date.today() - timedelta(days=c.MARKET_DATA_LOOKBACK_DAYS)).isoformat(),
            end=(date.today() + timedelta(days=1)).isoformat(),
            interval="1d",
            auto_adjust=True,
            progress=False,
            timeout=c.MARKET_DATA_TIMEOUT_SECONDS,
        )["Close"]
        close = aligned_prices(downloaded, tickers, min_days)
    except Exception as exc:
        logger.warning("yfinance download failed: %s", exc)
        close = None
    source = "live"
    if close is not None:
        save_price_history(close)
    else:
        close = aligned_prices(load_price_history(), tickers, min_days)
        source = "saved"
    if close is None:
        return None
    close.attrs["source"] = source
    return close
