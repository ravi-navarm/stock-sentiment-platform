# app/services/twitter_service.py

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")


def _empty_twitter_df() -> pd.DataFrame:
    return pd.DataFrame(
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


# very tiny lexicon-based sentiment so we don't need extra libraries
_POS_WORDS = {"good", "great", "bull", "bullish", "up", "gain", "gains", "green"}
_NEG_WORDS = {"bad", "terrible", "bear", "bearish", "down", "loss", "losses", "red"}


def _simple_sentiment(text: str) -> float:
    """
    Heuristic sentiment in [-1, 1] using a tiny keyword lexicon.
    This is intentionally simple – just to have a numeric signal.
    """
    text_l = text.lower()
    score = 0
    for w in _POS_WORDS:
        if w in text_l:
            score += 1
    for w in _NEG_WORDS:
        if w in text_l:
            score -= 1

    if score == 0:
        return 0.0
    # clamp to [-1, 1]
    if score > 0:
        return 1.0
    return -1.0


def _fetch_twitter_for_single(
    ticker: str, start: date, end: date
) -> pd.DataFrame:
    """
    Fetch recent tweets for one ticker between start and end (as best as Twitter allows).

    Returns a raw DataFrame with columns:
      ['ticker', 'created_at', 'text', 'sentiment']
    or an empty DataFrame on error.
    """
    if not TWITTER_BEARER_TOKEN:
        logger.warning("TWITTER_BEARER_TOKEN not set; skipping Twitter data.")
        return pd.DataFrame(columns=["ticker", "created_at", "text", "sentiment"])

    # Twitter recent search only supports ~last 7 days.
    # We'll clip the start date to (today - 7 days) to avoid 400 errors.
    now_utc = datetime.now(timezone.utc)
    seven_days_ago = now_utc - timedelta(days=7)

    # convert start/end (naive dates) into datetimes in UTC
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc)

    if start_dt < seven_days_ago:
        logger.info(
            "Twitter start date %s is older than 7 days; clipping to %s",
            start_dt,
            seven_days_ago,
        )
        start_dt = seven_days_ago

    # Twitter requires end_time to be at least 10s before now
    safe_end = now_utc - timedelta(seconds=10)
    if end_dt > safe_end:
        logger.info(
            "Twitter end date %s is too close to now; clipping to %s",
            end_dt,
            safe_end,
        )
        end_dt = safe_end

    # If after clipping the range is invalid, skip
    if start_dt >= end_dt:
        logger.warning(
            "Twitter time window invalid after clipping: start=%s, end=%s. Skipping.",
            start_dt,
            end_dt,
        )
        return pd.DataFrame(columns=["ticker", "created_at", "text", "sentiment"])

    query = f"(${ticker} OR {ticker}) (stock OR shares OR market) lang:en -is:retweet"

    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    params: Dict[str, Any] = {
        "query": query,
        "max_results": 50,
        "tweet.fields": "created_at,text,lang",
        "start_time": start_dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "end_time": end_dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
    }

    logger.info("Calling Twitter API for %s: %s", ticker, url)
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        logger.error("Twitter API error: %s %s", resp.status_code, resp.text)
        return pd.DataFrame(columns=["ticker", "created_at", "text", "sentiment"])

    data = resp.json()
    tweets = data.get("data", [])
    if not tweets:
        logger.info("No tweets found for %s in the given window", ticker)
        return pd.DataFrame(columns=["ticker", "created_at", "text", "sentiment"])

    rows = []
    for tw in tweets:
        text = tw.get("text", "")
        created_at_str = tw.get("created_at")
        try:
            created_at = datetime.fromisoformat(
                created_at_str.replace("Z", "+00:00")
            )
        except Exception:
            created_at = now_utc

        sent = _simple_sentiment(text)
        rows.append(
            {
                "ticker": ticker,
                "created_at": created_at,
                "text": text,
                "sentiment": sent,
            }
        )

    df = pd.DataFrame(rows)
    return df


def fetch_twitter_for_tickers(
    tickers: List[str], start: date, end: date
) -> pd.DataFrame:
    """
    Public function used by sentiment_service.build_training_frame.

    Returns daily aggregates with columns:
      ['ticker', 'date',
       'tw_sent_mean', 'tw_sent_std', 'tw_count',
       'tw_pos_share', 'tw_neg_share']
    """
    all_raw: List[pd.DataFrame] = []

    for ticker in tickers:
        df_raw = _fetch_twitter_for_single(ticker, start, end)
        logger.info("Twitter raw rows for %s: %d", ticker, len(df_raw))
        if not df_raw.empty:
            all_raw.append(df_raw)

    if not all_raw:
        logger.info("No Twitter data found for tickers %s", tickers)
        return _empty_twitter_df()

    df_all = pd.concat(all_raw, ignore_index=True)
    df_all["date"] = df_all["created_at"].dt.date

    grouped = df_all.groupby(["ticker", "date"], as_index=False)

    def _agg(group: pd.DataFrame) -> pd.Series:
        sentiments = group["sentiment"].astype(float)
        count = len(sentiments)
        pos = (sentiments > 0).sum()
        neg = (sentiments < 0).sum()
        return pd.Series(
            {
                "tw_sent_mean": float(sentiments.mean()) if count > 0 else 0.0,
                "tw_sent_std": float(sentiments.std(ddof=0)) if count > 0 else 0.0,
                "tw_count": int(count),
                "tw_pos_share": float(pos / count) if count > 0 else 0.0,
                "tw_neg_share": float(neg / count) if count > 0 else 0.0,
            }
        )

    df_daily = grouped.apply(_agg).reset_index(drop=True)

    # Ensure column order
    df_daily = df_daily[
        [
            "ticker",
            "date",
            "tw_sent_mean",
            "tw_sent_std",
            "tw_count",
            "tw_pos_share",
            "tw_neg_share",
        ]
    ]

    logger.info(
        "Aggregated twitter sentiment shape: rows=%d, cols=%d",
        df_daily.shape[0],
        df_daily.shape[1],
    )
    return df_daily


# Optional: backwards-compatible alias if old code used a different name
def fetch_twitter(
    tickers: List[str], start: date, end: date
) -> pd.DataFrame:
    """Alias to keep older imports from breaking."""
    return fetch_twitter_for_tickers(tickers, start, end)