# app/services/training_frame_service.py

from __future__ import annotations

import pandas as pd


def build_training_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the training DataFrame from price+feature data.

    Requirements:
      - 'ticker', 'date', 'Close' columns
    Produces:
      - all original feature columns
      - 'target_up' = 1 if next day's close > today's close, else 0
      - drops the last row per ticker (no next-day close to compare)
    """
    required_cols = {"ticker", "date", "Close"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"build_training_frame: missing required columns: {missing}")

    out = df.copy()
    out = out.sort_values(["ticker", "date"])

    # next day's close per ticker
    out["next_close"] = out.groupby("ticker")["Close"].shift(-1)

    # drop rows with no next_close (last row per ticker)
    out = out[out["next_close"].notna()].copy()

    # binary target: 1 if next close is higher than today's close
    out["target_up"] = (out["next_close"] > out["Close"]).astype(int)

    out.drop(columns=["next_close"], inplace=True)

    if out.empty:
        raise ValueError("No rows available to build training frame.")

    return out