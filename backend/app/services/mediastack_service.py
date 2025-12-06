# app/services/mediastack_service.py

from __future__ import annotations

import logging
import os
from datetime import date
from typing import List

import pandas as pd
import requests

logger = logging.getLogger(__name__)

MEDIASTACK_API_KEY = os.getenv("MEDIASTACK_API_KEY")
MEDIASTACK_BASE_URL = "http://api.mediastack.com/v1/news"


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["ticker", "date", "title", "description", "source"]
    )


def fetch_mediastack_for_ticker(ticker: str, start: date, end: date) -> pd.DataFrame:
    """
    Fetch news for a single ticker from Mediastack and return a normalized DataFrame:
    columns: ticker, date, title, description, source
    """
    if not MEDIASTACK_API_KEY:
        logger.warning("MEDIASTACK_API_KEY not set; skipping Mediastack fetch.")
        return _empty_df()

    params = {
        "access_key": MEDIASTACK_API_KEY,
        "languages": "en",
        "limit": 100,
        "sort": "published_desc",
        # Mediastack expects date range as "YYYY-MM-DD,YYYY-MM-DD"
        "date": f"{start.isoformat()},{end.isoformat()}",
        # broad stock-related search
        "keywords": f'"{ticker}" stock OR share OR market',
    }

    try:
        resp = requests.get(MEDIASTACK_BASE_URL, params=params, timeout=10)
    except Exception as exc:
        logger.error("Mediastack request failed for %s: %s", ticker, exc)
        return _empty_df()

    if resp.status_code != 200:
        logger.error(
            "Mediastack error for %s: status=%s body=%s",
            ticker,
            resp.status_code,
            resp.text,
        )
        return _empty_df()

    data = resp.json()
    raw_articles = data.get("data", [])
    records = []

    for art in raw_articles:
        published = art.get("published_at") or art.get("published") or art.get("date")
        if not published:
            continue

        try:
            d = pd.to_datetime(published).date()
        except Exception:
            continue

        records.append(
            {
                "ticker": ticker,
                "date": d,
                "title": art.get("title") or "",
                "description": art.get("description") or art.get("snippet") or "",
                "source": art.get("source") or art.get("source_name") or "",
            }
        )

    df = pd.DataFrame.from_records(records)
    logger.info("Mediastack rows for %s: %d", ticker, len(df))
    if df.empty:
        return _empty_df()
    return df


def fetch_mediastack_for_tickers(
    tickers: List[str], start: date, end: date
) -> pd.DataFrame:
    frames = [fetch_mediastack_for_ticker(t, start, end) for t in tickers]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return _empty_df()
    return pd.concat(frames, ignore_index=True)