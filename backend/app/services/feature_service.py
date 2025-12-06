# app/services/feature_service.py

from __future__ import annotations

from typing import Optional, Dict

import numpy as np
import pandas as pd
from pandas import DataFrame


def _feat_group(g: DataFrame) -> DataFrame:
    """
    Per-ticker feature engineering on price data.

    Expects columns:
      - date (datetime-like)
      - Close
      - Volume or volume

    Produces:
      - ret_1d, ret_5d
      - vol_5d, vol_21d  (rolling std of 1-day returns)
      - volume_z         (21-day z-score of volume, optional)
      - day_of_week      (0=Monday..6=Sunday)
    """
    g = g.sort_values("date").copy()

    # Ensure datetime
    g["date"] = pd.to_datetime(g["date"])

    # --- Close price as a 1-D Series ---
    close = g["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.astype(float)

    # --- Returns ---
    ret_1d = close.pct_change(periods=1, fill_method=None)
    ret_5d = close.pct_change(periods=5, fill_method=None)

    g["ret_1d"] = ret_1d
    g["ret_5d"] = ret_5d

    # --- Rolling volatility of 1-day returns ---
    g["vol_5d"] = ret_1d.rolling(window=5, min_periods=1).std()
    g["vol_21d"] = ret_1d.rolling(window=21, min_periods=1).std()

    # --- Volume-based features (optional but nice) ---
    vol_col: Optional[str] = None
    if "Volume" in g.columns:
        vol_col = "Volume"
    elif "volume" in g.columns:
        vol_col = "volume"

    if vol_col is not None:
        vol = g[vol_col].astype(float)
        vol_mean_21 = vol.rolling(window=21, min_periods=1).mean()
        vol_std_21 = vol.rolling(window=21, min_periods=1).std()

        volume_z = (vol - vol_mean_21) / vol_std_21
        volume_z = volume_z.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        g["volume_z"] = volume_z
    else:
        g["volume_z"] = np.nan

    # --- Calendar feature ---
    g["day_of_week"] = g["date"].dt.dayofweek

    return g


def _build_from_suffixed(
    df: DataFrame, base_name: str, ticker_col: str = "ticker"
) -> Optional[str]:
    """
    If column `base_name` (e.g. 'Close') is missing, try to build it from
    suffixed columns like 'Close_AAPL', 'Close_MSFT', using the ticker
    value in each row.

    Returns the name of the column that can be used ('Close' or None if failed).
    """
    if base_name in df.columns:
        return base_name  # already present

    # Find columns matching e.g. Close_*, case-insensitive
    mapping: Dict[str, str] = {}
    prefix = base_name.lower() + "_"

    for col in df.columns:
        col_low = col.lower()
        if col_low.startswith(prefix):
            # Extract ticker suffix after 'close_'
            suffix = col[len(base_name) + 1 :]  # after "Close_"
            mapping[suffix.upper()] = col

    if not mapping:
        return None  # nothing to build from

    if ticker_col not in df.columns:
        return None

    # Create the unified column
    col_name = base_name
    df[col_name] = np.nan
    tick_upper = df[ticker_col].astype(str).str.upper()

    for t, src_col in mapping.items():
        mask = tick_upper == t
        if mask.any():
            df.loc[mask, col_name] = df.loc[mask, src_col].astype(float)

    # If everything is still NaN, treat as failure
    if df[col_name].isna().all():
        df.drop(columns=[col_name], inplace=True)
        return None

    return col_name


def add_price_features(df: DataFrame) -> DataFrame:
    """
    Add return/volatility/volume/day-of-week features to the raw price frame.

    Handles various shapes coming from yfinance/market_data_service, e.g.:

      - MultiIndex columns like ('Price', 'Close') -> flattened to 'Close'
      - 'Ticker' / 'Date' in index -> moved to columns
      - Wide columns like 'Close_AAPL', 'Close_MSFT', 'Volume_AAPL', 'Volume_MSFT'

    Expects (after normalization) columns at least:
      - 'ticker'
      - 'date'
      - 'Close'   (can be inferred from 'Close_<TICKER>')
      - 'Volume' or 'volume' (can be inferred from 'Volume_<TICKER>')

    Returns the same rows, with extra feature columns:
      - ret_1d, ret_5d
      - vol_5d, vol_21d
      - volume_z
      - day_of_week
    """
    if df is None or df.empty:
        raise ValueError("add_price_features: received empty price DataFrame")

    df = df.copy()

    # --- 1) Flatten MultiIndex columns if present ---
    if isinstance(df.columns, pd.MultiIndex):
        top_level = df.columns.get_level_values(0)
        if len(set(top_level)) == 1:
            df.columns = df.columns.get_level_values(-1)
        else:
            df.columns = [
                "_".join([str(level) for level in col if level != ""])
                for col in df.columns
            ]

    # --- 2) Move index levels 'Ticker'/'ticker'/'Date'/'date' into columns if needed ---
    if isinstance(df.index, pd.MultiIndex):
        index_names = list(df.index.names)
        if any(name in ("Ticker", "ticker", "Date", "date") for name in index_names):
            df = df.reset_index()
    else:
        if df.index.name in ("Ticker", "ticker", "Date", "date"):
            df = df.reset_index()

    # --- 3) Normalize column names ---
    if "ticker" not in df.columns and "Ticker" in df.columns:
        df = df.rename(columns={"Ticker": "ticker"})
    if "date" not in df.columns and "Date" in df.columns:
        df = df.rename(columns={"Date": "date"})

    # We must at least have ticker + date
    base_required = {"ticker", "date"}
    missing_base = base_required - set(df.columns)
    if missing_base:
        raise ValueError(
            f"add_price_features: missing required columns: {missing_base}"
        )

    # --- 4) Try to ensure we have a 'Close' column ---
    close_col = _build_from_suffixed(df, "Close", ticker_col="ticker")
    if close_col is None:
        # If there was no suffixed source, maybe it's already there and we just didn't see it;
        # but at this point, we truly don't have Close.
        if "Close" not in df.columns:
            raise ValueError(
                "add_price_features: missing required columns: {'Close'}"
            )

    # --- 5) Try to ensure we have some volume column (Volume or volume) ---
    if "Volume" not in df.columns and "volume" not in df.columns:
        # Try to build 'Volume' from 'Volume_<TICKER>'
        vol_col = _build_from_suffixed(df, "Volume", ticker_col="ticker")
        # It's okay if this returns None; _feat_group falls back to NaNs for volume_z

    # Ensure date is datetime and sort
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["ticker", "date"])

    # --- 6) Group by ticker and apply per-ticker feature logic ---
    df_feat = df.groupby("ticker", group_keys=False).apply(_feat_group)

    # Flatten any index weirdness
    df_feat = df_feat.reset_index(drop=True)

    # Replace ±inf with NaN so later code can handle / drop them
    df_feat.replace([np.inf, -np.inf], np.nan, inplace=True)

    return df_feat