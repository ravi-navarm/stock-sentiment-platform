# app/services/model_service.py

from __future__ import annotations

import logging
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

# Features we *try* to use; we intersect with actual columns at runtime
FEATURE_COLS: List[str] = [
    "news_sent_mean", "news_sent_std", "news_count",
    "news_pos_share", "news_neg_share",
    "tw_sent_mean", "tw_sent_std", "tw_count",
    "tw_pos_share", "tw_neg_share",
    "ret_1d", "ret_5d", "vol_5d", "vol_21d",
    "day_of_week",
]

# Global state used by the API/tests
_GLOBAL_MODEL: Optional[Tuple[RandomForestClassifier, List[str]]] = None
_LAST_TRAIN_DF: Optional[pd.DataFrame] = None


def _select_feature_cols(df: pd.DataFrame) -> List[str]:
    """
    Return the subset of FEATURE_COLS that are actually present in df.
    Raises if none of the expected feature columns are available.
    """
    cols = [c for c in FEATURE_COLS if c in df.columns]
    if not cols:
        raise ValueError("No expected feature columns found in training DataFrame")
    return cols


def train_model(train_df: pd.DataFrame) -> Dict[str, Optional[float]]:
    """
    Train a RandomForest model on the given training frame.

    Expects:
      - 'target_up' column as the binary target (0/1)
      - some subset of FEATURE_COLS as features
      - 'ticker' and 'date' may be present but are not used as features

    Side effects:
      - sets _GLOBAL_MODEL to (clf, feature_cols)
      - sets _LAST_TRAIN_DF to the cleaned training DataFrame

    Returns:
      - dict with at least {"roc_auc": <float or None>}
    """
    global _GLOBAL_MODEL, _LAST_TRAIN_DF

    if train_df is None or train_df.empty:
        raise ValueError("train_model received an empty training DataFrame")

    df = train_df.copy()

    if "target_up" not in df.columns:
        raise ValueError(
            "Training DataFrame must contain 'target_up' column "
            "(did build_training_frame run correctly?)"
        )

    # Keep only rows with non-null target
    df = df[df["target_up"].notna()].copy()
    if df.empty:
        raise ValueError("No rows with non-null target_up in training DataFrame")

    df["target_up"] = df["target_up"].astype(int)

    # Select usable feature columns
    feature_cols = _select_feature_cols(df)
    logger.info("Using feature columns: %s", feature_cols)

    X = df[feature_cols].fillna(0.0)
    y = df["target_up"]

    n = len(df)
    if n < 20:
        logger.warning("Very small training set (n=%d). Model quality may be poor.", n)
    if n < 2:
        msg = f"Not enough rows to train a model (n={n}). Need at least 2."
        logger.warning(msg)
        raise ValueError(msg)

    # Simple time-series-ish split (no shuffling)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    # ROC-AUC only if both classes present
    roc_auc: Optional[float] = None
    unique_labels = np.unique(y_test)
    if len(unique_labels) > 1:
        y_proba = clf.predict_proba(X_test)[:, 1]
        roc_auc = float(roc_auc_score(y_test, y_proba))
        logger.info("Test ROC-AUC: %.4f", roc_auc)
    else:
        logger.warning(
            "Only one class present in y_test; ROC-AUC is undefined. Labels: %s",
            unique_labels,
        )

    _GLOBAL_MODEL = (clf, feature_cols)
    _LAST_TRAIN_DF = df

    # Use None instead of NaN so JSON encoding doesn't break
    return {"roc_auc": roc_auc}


def predict_next(ticker: str) -> float:
    """
    Predict the probability that the next day's close for this ticker will be UP.
    Uses the last trained model and the last available feature row for this ticker.

    Raises:
      - RuntimeError if model was never trained
      - ValueError if ticker not seen in training
    """
    global _GLOBAL_MODEL, _LAST_TRAIN_DF

    if _GLOBAL_MODEL is None or _LAST_TRAIN_DF is None:
        raise RuntimeError("Model has not been trained yet in this process")

    clf, feature_cols = _GLOBAL_MODEL
    df = _LAST_TRAIN_DF

    if "ticker" not in df.columns:
        raise ValueError("Training DataFrame does not contain 'ticker' column")
    if "date" not in df.columns:
        raise ValueError("Training DataFrame does not contain 'date' column")

    df_t = df[df["ticker"] == ticker]
    if df_t.empty:
        raise ValueError(f"No training samples found for ticker '{ticker}'")

    df_t = df_t.sort_values("date")
    last_row = df_t.iloc[-1:]

    X = last_row[feature_cols].fillna(0.0)
    proba = clf.predict_proba(X)[0, 1]

    prob_up = float(proba)
    logger.info("predict_next(%s) -> prob_up=%.4f", ticker, prob_up)
    return prob_up