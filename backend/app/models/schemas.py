# backend/app/models/schemas.py
from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class TrainRequest(BaseModel):
    tickers: List[str]
    start_date: date
    end_date: date


class TrainResponse(BaseModel):
    message: str
    tickers: List[str]
    start_date: date
    end_date: date
    test_auc: Optional[float] = None


class PredictionRequest(BaseModel):
    ticker: str


class PredictionResponse(BaseModel):
    ticker: str
    prob_up: float
    label: str  # "UP" or "DOWN/FLAT"


class SentimentSummaryItem(BaseModel):
    date: date
    news_sent_mean: float | None = None
    news_count: int | None = None
    tw_sent_mean: float | None = None
    tw_count: int | None = None


class SentimentSummaryResponse(BaseModel):
    ticker: str
    items: List[SentimentSummaryItem]


class PopularStock(BaseModel):
    ticker: str
    name: str


class PopularStocksResponse(BaseModel):
    stocks: List[PopularStock]