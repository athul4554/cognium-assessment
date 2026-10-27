"""Run `python -m app.recommendation.refresh_history` before an offline demo."""

from .builder import load_universe
from .market_data import get_price_history


def main():
    tickers = sorted(f["ticker"] for f in load_universe()["instruments"])
    prices = get_price_history(tickers)
    if prices is None:
        raise SystemExit("No usable Yahoo or saved history; recommendations will use the unallocated-cash fallback.")
    print(f"{prices.attrs['source']}: {len(prices.columns)} funds, {len(prices) - 1} daily returns, "
          f"{prices.index[1].date()} to {prices.index[-1].date()}")


if __name__ == "__main__":
    main()
