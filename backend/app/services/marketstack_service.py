# app/services/marketstack_service.py

from __future__ import annotations

import logging
import os
from datetime import date
from typing import List

import pandas as pd
import requests

logger = logging.getLogger(__name__)

MARKETSTACK_API_KEY = os.getenv("MARKETSTACK_API_KEY")
MARKETSTACK_BASE_URL = "http://api.marketstack.com/v1/eod"


def _empty_price_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["ticker", "date", "Open", "High", "Low", "Close", "Volume"]
    )


def fetch_marketstack_for_ticker(ticker: str, start: date, end: date) -> pd.DataFrame:
    """
    Fetch EOD prices for a single ticker from Marketstack.
    Returns columns: ticker, date, Open, High, Low, Close, Volume
    """
    if not MARKETSTACK_API_KEY:
        logger.warning("MARKETSTACK_API_KEY not set; skipping Marketstack fetch.")
        return _empty_price_df()

    params = {
        "access_key": MARKETSTACK_API_KEY,
        "symbols": ticker,
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "limit": 1000,
    }

    try:
        resp = requests.get(MARKETSTACK_BASE_URL, params=params, timeout=10)
    except Exception as exc:
        logger.error("Marketstack request failed for %s: %s", ticker, exc)
        return _empty_price_df()

    if resp.status_code != 200:
        logger.error(
            "Marketstack error for %s: status=%s body=%s",
            ticker,
            resp.status_code,
            resp.text,
        )
        return _empty_price_df()

    data = resp.json()
    rows = data.get("data", [])
    records = []

    for row in rows:
        try:
            d = pd.to_datetime(row["date"]).date()
        except Exception:
            continue

        records.append(
            {
                "ticker": ticker,
                "date": d,
                "Open": row.get("open"),
                "High": row.get("high"),
                "Low": row.get("low"),
                "Close": row.get("close"),
                "Volume": row.get("volume"),
            }
        )

    df = pd.DataFrame.from_records(records)
    if df.empty:
        return _empty_price_df()

    df = df.sort_values("date")
    logger.info("Marketstack rows for %s: %d", ticker, len(df))
    return df


def fetch_marketstack_for_tickers(
    tickers: List[str], start: date, end: date
) -> pd.DataFrame:
    frames = [fetch_marketstack_for_ticker(t, start, end) for t in tickers]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return _empty_price_df()
    return pd.concat(frames, ignore_index=True)