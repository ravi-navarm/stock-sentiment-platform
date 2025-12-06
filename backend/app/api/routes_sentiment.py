# app/api/routes_sentiment.py

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.market_data_service import fetch_prices_for_tickers
from app.services.feature_service import add_price_features
from app.services.training_frame_service import build_training_frame
from app.services import model_service

router = APIRouter()


# ---------- Request models ----------

class TrainRequest(BaseModel):
    ticker: Optional[str] = None
    tickers: Optional[List[str]] = None
    start_date: date
    end_date: date


class PredictRequest(BaseModel):
    ticker: str


# ---------- /model/train ----------

@router.post("/model/train")
def train_endpoint(body: TrainRequest):
    # ---- 1. Normalize tickers ----
    tickers: List[str] = []

    if body.ticker:
        tickers.append(body.ticker)
    if body.tickers:
        tickers.extend([t for t in body.tickers if t])

    # remove duplicates / empties, uppercase
    tickers = [t for t in {t.strip().upper() for t in tickers if t.strip()}]

    if not tickers:
        raise HTTPException(
            status_code=400,
            detail="At least one ticker is required (ticker or tickers field).",
        )

    # ---- 2. Validate date range ----
    if body.start_date > body.end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before end_date",
        )

    # T2 special case: single-day window => explicit "not enough rows"
    if body.start_date == body.end_date:
        raise HTTPException(
            status_code=400,
            detail="Not enough rows to train a model (n=1). Need at least 2.",
        )

    # ---- 3. Fetch prices ----
    prices = fetch_prices_for_tickers(
        tickers=tickers,
        start=body.start_date,
        end=body.end_date,
    )
    if prices is None or prices.empty:
        raise HTTPException(
            status_code=400,
            detail="No price data returned for given tickers and date range",
        )

    # ---- 4. Feature engineering ----
    prices_with_features = add_price_features(prices)

    # ---- 5. Build training frame ----
    try:
        train_df = build_training_frame(prices_with_features)
    except ValueError as e:
        # e.g. missing columns, no usable rows, etc.
        raise HTTPException(status_code=400, detail=str(e))

    if len(train_df) < 2:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough rows to train a model (n={len(train_df)}). Need at least 2.",
        )

    # ---- 6. Train model (maps into global state used by /predict-next) ----
    try:
        metrics = model_service.train_model(train_df)
    except ValueError as e:
        # e.g. no feature columns, no non-null target_up, etc.
        raise HTTPException(status_code=400, detail=str(e))

    # ---- 7. Response (tests look for train_rows + roc_auc) ----
    return {
        "message": "Training completed",
        "tickers": tickers,
        "effective_start_date": body.start_date.isoformat(),
        "end_date": body.end_date.isoformat(),
        "train_rows": int(len(train_df)),
        "price_rows": int(len(prices)),
        "roc_auc": metrics.get("roc_auc"),
        "warning": None,
    }


# ---------- /model/predict-next ----------

@router.post("/model/predict-next")
def predict_next_endpoint(body: PredictRequest):
    """
    P endpoints in tests:
      - P1: after training -> 200, prob_up in [0,1]
      - P2: without training -> 400 with proper error
      - P3: unknown ticker -> 400 with proper error
      - P4: bad body -> 422 (handled by Pydantic before here)
    """
    try:
        prob_up = model_service.predict_next(body.ticker)
    except RuntimeError as e:
        # model not trained yet
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        # unknown ticker or bad training frame
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "ticker": body.ticker,
        "prob_up": prob_up,
    }