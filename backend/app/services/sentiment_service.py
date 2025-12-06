# app/services/sentiment_service.py

from __future__ import annotations

import logging
from datetime import date
from typing import List

import pandas as pd

from app.services.news_service import fetch_news_for_tickers
from app.services.twitter_service import fetch_twitter_for_tickers

logger = logging.getLogger(__name__)


def _normalize_price_frame(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure the price/features frame has:
      - 'ticker'
      - 'date'
      - 'target_up' (create if missing)
    and no MultiIndex weirdness.
    """
    if prices is None or prices.empty:
        raise ValueError("Prices DataFrame is empty in build_training_frame")

    df = prices.copy()

    # Flatten MultiIndex index if present
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index()

    # Ensure 'date' column
    if "date" not in df.columns:
        if "Date" in df.columns:
            df = df.rename(columns={"Date": "date"})
        elif isinstance(df.index, (pd.DatetimeIndex, pd.Index)):
            df = df.reset_index().rename(columns={"index": "date"})
        else:
            raise ValueError("Could not find 'date' column in prices DataFrame")

    df["date"] = pd.to_datetime(df["date"]).dt.date

    # Ensure 'ticker' column
    if "ticker" not in df.columns:
        raise ValueError("Prices DataFrame does not contain 'ticker' column")

    # If target_up already exists, just return after cleaning NaNs
    if "target_up" in df.columns:
        logger.info("'target_up' already present in prices frame")
        return df

    # Otherwise, compute target_up from a price column
    logger.info("'target_up' not found; computing it from price series")

    # Try to detect any close-like price column
    close_candidates = [
        c
        for c in df.columns
        if "close" in str(c).lower()  # catches Close / close / Adj Close / adj_close, etc.
    ]

    if not close_candidates:
        raise ValueError(
            "Could not find a price column (containing 'close') to compute 'target_up'"
        )

    price_col = close_candidates[0]
    logger.info("Using '%s' as price column to build target_up", price_col)

    df = df.sort_values(["ticker", "date"])
    df["next_close"] = df.groupby("ticker")[price_col].shift(-1)

    # target_up = 1 if next_close > current_close else 0
    df["target_up"] = (df["next_close"] > df[price_col]).astype(float)

    # Drop last row per ticker where next_close is NaN
    df = df.dropna(subset=["target_up"])

    return df


def build_training_frame(
    prices: pd.DataFrame,
    tickers: List[str],
    start: date,
    end: date,
) -> pd.DataFrame:
    """
    Build the final training DataFrame by merging:
      - price/return/volatility features + target_up  (from `prices`)
      - daily aggregated news sentiment               (NewsAPI + Mediastack)
      - daily aggregated twitter sentiment            (Twitter recent search)
    """
    # 1) Normalize prices & ensure target_up
    df = _normalize_price_frame(prices)

    # Filter time window
    mask = (df["date"] >= start) & (df["date"] <= end)
    df = df.loc[mask].copy()

    if df.empty:
        raise ValueError(
            f"No price rows in training window after filtering: start={start}, end={end}"
        )

    # 2) News sentiment (can be empty if keys not set)
    try:
        news_daily = fetch_news_for_tickers(tickers, start, end)
    except Exception as e:
        logger.exception("Error while fetching news sentiment: %s", e)
        news_daily = pd.DataFrame(
            columns=[
                "ticker",
                "date",
                "news_sent_mean",
                "news_sent_std",
                "news_count",
                "news_pos_share",
                "news_neg_share",
            ]
        )

    if not news_daily.empty:
        news_daily["date"] = pd.to_datetime(news_daily["date"]).dt.date

    # 3) Twitter sentiment (can be empty if bearer token not set)
    try:
        tw_daily = fetch_twitter_for_tickers(tickers, start, end)
    except Exception as e:
        logger.exception("Error while fetching twitter sentiment: %s", e)
        tw_daily = pd.DataFrame(
            columns=[
                "ticker",
                "date",
                "tw_sent_mean",
                "tw_sent_std",
                "tw_count",
                "tw_pos_share",
                "tw_neg_share",
            ]
        )

    if not tw_daily.empty:
        tw_daily["date"] = pd.to_datetime(tw_daily["date"]).dt.date

    # 4) Merge on simple columns ['ticker', 'date']
    if not news_daily.empty:
        df = df.merge(news_daily, on=["ticker", "date"], how="left")

    if not tw_daily.empty:
        df = df.merge(tw_daily, on=["ticker", "date"], how="left")

    logger.info(
        "Final training frame shape after merges: rows=%d, cols=%d",
        df.shape[0],
        df.shape[1],
    )

    # Final hard guarantee: target_up must exist here
    if "target_up" not in df.columns:
        raise ValueError(
            "build_training_frame produced a DataFrame without 'target_up'. "
            "Check price feature generation."
        )

    return df