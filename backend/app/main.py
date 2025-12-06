# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_sentiment import router as sentiment_router
from app.api.routes_symbols import router as symbols_router  # now this file exists

app = FastAPI(title="Stock Sentiment Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "message": "Stock Sentiment API"}


# Mount routers
app.include_router(symbols_router, prefix="/api/v1")
app.include_router(sentiment_router, prefix="/api/v1")