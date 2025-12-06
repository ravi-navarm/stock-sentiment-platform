# app/services/market_data_service.py

from __future__ import annotations

import logging
from datetime import date
from typing import List

import pandas as pd
import yfinance as yf

from app.services.marketstack_service import fetch_marketstack_for_tickers

logger = logging.getLogger(__name__)


def _empty_price_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["ticker", "date", "Open", "High", "Low", "Close", "Volume"]
    )


def fetch_prices_for_tickers(
    tickers: List[str], start: date, end: date
) -> pd.DataFrame:
    """
    Fetch daily OHLCV prices for the given tickers between start and end.

    Primary source: yfinance
    Fallback: Marketstack (if yfinance returns no data for a ticker)

    Returns columns: ticker, date, Open, High, Low, Close, Volume
    """
    frames: List[pd.DataFrame] = []

    for ticker in tickers:
        logger.info("Fetching prices for %s from yfinance", ticker)
        df_yf = yf.download(
            ticker,
            start=start.isoformat(),
            end=end.isoformat(),
        )

        if df_yf is None or df_yf.empty:
            logger.warning("No yfinance data for %s, trying Marketstack", ticker)
            frames.append(
                fetch_marketstack_for_tickers([ticker], start=start, end=end)
            )
            continue

        df_yf = df_yf.reset_index()
        df_yf.rename(
            columns={
                "Date": "date",
                "Open": "Open",
                "High": "High",
                "Low": "Low",
                "Close": "Close",
                "Adj Close": "AdjClose",
                "Volume": "Volume",
            },
            inplace=True,
        )

        df_yf["date"] = pd.to_datetime(df_yf["date"]).dt.date
        df_yf["ticker"] = ticker

        frames.append(
            df_yf[["ticker", "date", "Open", "High", "Low", "Close", "Volume"]]
        )

    frames = [f for f in frames if not f.empty]
    if not frames:
        logger.warning("fetch_prices_for_tickers: no data for %s", tickers)
        return _empty_price_df()

    df_all = pd.concat(frames, ignore_index=True)
    df_all = df_all.sort_values(["ticker", "date"])
    logger.info(
        "Combined price frame: rows=%d, cols=%d", df_all.shape[0], df_all.shape[1]
    )
    return df_all


# --------------------------------------------------------------------
# Backwards-compat wrapper so old imports still work
# routes_sentiment.py and others might still call fetch_price_data(...)
# --------------------------------------------------------------------
def fetch_price_data(
    tickers: List[str], start: date, end: date
) -> pd.DataFrame:
    """
    Backwards-compatible alias for fetch_prices_for_tickers.

    Old signature:
        fetch_price_data(tickers, start, end)

    Now simply forwards to fetch_prices_for_tickers.
    """
    return fetch_prices_for_tickers(tickers, start, end)