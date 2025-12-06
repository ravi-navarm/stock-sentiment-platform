# app/services/news_service.py

from __future__ import annotations

import logging
import os
from datetime import date, datetime
from typing import List

import requests
import pandas as pd

logger = logging.getLogger(__name__)

# Try both common env var names so we don't break existing setup
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY") or os.getenv("NEWS_API_KEY")
MEDIASTACK_KEY = os.getenv("MEDIASTACK_API_KEY") or os.getenv("MEDIASTACK_KEY")


# ---------- Simple keyword-based sentiment (no extra libs) ----------

POS_WORDS = {
    "gain", "gains", "rally", "rallies", "surge", "surges", "up",
    "bullish", "beat", "beats", "strong", "record", "profit", "profits",
    "growth", "soar", "soars", "upgrade", "upgraded",
}

NEG_WORDS = {
    "loss", "losses", "fall", "falls", "drop", "drops", "down",
    "bearish", "miss", "misses", "weak", "plunge", "plunges",
    "selloff", "downgrade", "downgraded", "lawsuit",
}


def _score_text(text: str) -> float:
    """
    Very rough sentiment score in [-1, 1] based on simple word counts.
    You can later replace this with a proper library if you want.
    """
    if not text:
        return 0.0

    txt = text.lower()
    pos = sum(w in txt for w in POS_WORDS)
    neg = sum(w in txt for w in NEG_WORDS)

    if pos == 0 and neg == 0:
        return 0.0

    score = (pos - neg) / float(pos + neg)
    return max(-1.0, min(1.0, score))


# ---------- NewsAPI ----------

def fetch_newsapi_news(ticker: str, start: date, end: date) -> pd.DataFrame:
    """
    Fetch raw articles from NewsAPI for a single ticker and return a DataFrame
    with columns: ['ticker', 'date', 'title', 'description', 'sentiment'].
    """
    if not NEWSAPI_KEY:
        logger.warning("NEWSAPI_KEY not set; skipping NewsAPI for %s", ticker)
        return pd.DataFrame(
            columns=["ticker", "date", "title", "description", "sentiment"]
        )

    url = "https://newsapi.org/v2/everything"
    query = f'"{ticker}" AND (stock OR share OR earnings OR market)'

    params = {
        "q": query,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": 100,
        "apiKey": NEWSAPI_KEY,
    }

    resp = requests.get(url, params=params, timeout=15)
    logger.info("NewsAPI request status=%s url=%s", resp.status_code, resp.url)

    if resp.status_code != 200:
        logger.warning("NewsAPI error for %s: %s", ticker, resp.text)
        return pd.DataFrame(
            columns=["ticker", "date", "title", "description", "sentiment"]
        )

    data = resp.json()
    if data.get("status") != "ok":
        logger.warning("NewsAPI returned non-ok status for %s: %s", ticker, data)
        return pd.DataFrame(
            columns=["ticker", "date", "title", "description", "sentiment"]
        )

    rows = []
    for a in data.get("articles", []):
        title = a.get("title") or ""
        desc = a.get("description") or ""
        text = f"{title}. {desc}".strip()
        sent = _score_text(text)

        published_at = a.get("publishedAt")
        if published_at:
            try:
                dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                d = dt.date()
            except Exception:
                d = start
        else:
            d = start

        rows.append(
            {
                "ticker": ticker,
                "date": d,
                "title": title,
                "description": desc,
                "sentiment": float(sent),
            }
        )

    df = pd.DataFrame(rows)
    logger.info("NewsAPI returned %d articles for %s", len(df), ticker)
    return df


# ---------- Mediastack ----------

def fetch_mediastack_news(ticker: str, start: date, end: date) -> pd.DataFrame:
    """
    Fetch raw articles from Mediastack for a single ticker.
    Returns same columns as fetch_newsapi_news.
    """
    if not MEDIASTACK_KEY:
        logger.warning("MEDIASTACK_API_KEY not set; skipping Mediastack for %s", ticker)
        return pd.DataFrame(
            columns=["ticker", "date", "title", "description", "sentiment"]
        )

    url = "http://api.mediastack.com/v1/news"
    params = {
        "access_key": MEDIASTACK_KEY,
        "symbols": ticker,
        "date": f"{start.isoformat()},{end.isoformat()}",
        "languages": "en",
        "limit": 100,
        "sort": "popularity",
    }

    resp = requests.get(url, params=params, timeout=15)
    logger.info("Mediastack request status=%s url=%s", resp.status_code, resp.url)

    if resp.status_code != 200:
        logger.warning("Mediastack error for %s: %s", ticker, resp.text)
        return pd.DataFrame(
            columns=["ticker", "date", "title", "description", "sentiment"]
        )

    data = resp.json()
    articles = data.get("data", []) or []

    rows = []
    for a in articles:
        title = a.get("title") or ""
        desc = a.get("description") or ""
        text = f"{title}. {desc}".strip()
        sent = _score_text(text)

        published_at = a.get("published_at")
        if published_at:
            try:
                dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                d = dt.date()
            except Exception:
                d = start
        else:
            d = start

        rows.append(
            {
                "ticker": ticker,
                "date": d,
                "title": title,
                "description": desc,
                "sentiment": float(sent),
            }
        )

    df = pd.DataFrame(rows)
    logger.info("Mediastack returned %d articles for %s", len(df), ticker)
    return df


# ---------- High-level: daily aggregates per ticker ----------

def fetch_news_for_tickers(
    tickers: List[str],
    start: date,
    end: date,
) -> pd.DataFrame:
    """
    For each ticker:
      - pull news from NewsAPI and Mediastack,
      - combine,
      - compute daily aggregates:
          news_sent_mean
          news_sent_std
          news_count
          news_pos_share
          news_neg_share
    Returns columns:
      ['ticker', 'date', 'news_sent_mean', 'news_sent_std',
       'news_count', 'news_pos_share', 'news_neg_share']
    """
    all_rows = []

    for t in tickers:
        try:
            newsapi_df = fetch_newsapi_news(t, start, end)
        except Exception as e:
            logger.exception("Error fetching NewsAPI for %s: %s", t, e)
            newsapi_df = pd.DataFrame(
                columns=["ticker", "date", "title", "description", "sentiment"]
            )

        try:
            mediastack_df = fetch_mediastack_news(t, start, end)
        except Exception as e:
            logger.exception("Error fetching Mediastack for %s: %s", t, e)
            mediastack_df = pd.DataFrame(
                columns=["ticker", "date", "title", "description", "sentiment"]
            )

        combined = pd.concat(
            [newsapi_df, mediastack_df], ignore_index=True
        ).dropna(subset=["date"])

        if combined.empty:
            continue

        combined["date"] = pd.to_datetime(combined["date"]).dt.date
        all_rows.append(combined)

    if not all_rows:
        logger.warning("No news data returned for tickers=%s", tickers)
        return pd.DataFrame(
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

    all_df = pd.concat(all_rows, ignore_index=True)

    agg = (
        all_df.groupby(["ticker", "date"])["sentiment"]
        .agg(
            news_sent_mean="mean",
            news_sent_std="std",
            news_count="count",
            news_pos_share=lambda s: (s > 0).mean(),
            news_neg_share=lambda s: (s < 0).mean(),
        )
        .reset_index()
    )

    logger.info(
        "Aggregated news sentiment shape: rows=%d, cols=%d",
        agg.shape[0],
        agg.shape[1],
    )
    return agg