# tests/test_model_predict.py

from fastapi.testclient import TestClient
from app.services import model_service


def train_for_predict(client: TestClient):
    """Helper: train a model we can use for predict tests."""
    payload = {
        "tickers": ["AAPL"],
        "start_date": "2025-11-01",
        "end_date": "2025-12-04",
    }
    resp = client.post("/api/v1/model/train", json=payload)
    assert resp.status_code == 200


def test_P1_predict_after_train(client: TestClient):
    """
    P1: train first, then call /predict-next -> 200 + prob_up in [0,1].
    """
    train_for_predict(client)

    resp = client.post(
        "/api/v1/model/predict-next",
        json={"ticker": "AAPL"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["ticker"] == "AAPL"
    assert 0.0 <= data["prob_up"] <= 1.0


def test_P2_predict_without_train(client: TestClient, monkeypatch):
    """
    P2: model not trained in this process -> 400 with proper error message.
    We forcibly reset _GLOBAL_MODEL and _LAST_TRAIN_DF.
    """
    # force reset global state
    model_service._GLOBAL_MODEL = None
    model_service._LAST_TRAIN_DF = None

    resp = client.post(
        "/api/v1/model/predict-next",
        json={"ticker": "AAPL"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "Model has not been trained yet" in data["detail"]


def test_P3_predict_for_unknown_ticker(client: TestClient):
    """
    P3: train only on AAPL, then predict for MSFT -> 400 'No training samples found'.
    """
    train_for_predict(client)

    resp = client.post(
        "/api/v1/model/predict-next",
        json={"ticker": "MSFT"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "No training samples found for ticker 'MSFT'" in data["detail"]


def test_P4_predict_invalid_body(client: TestClient):
    """
    P4: send bad JSON (e.g. no ticker field) -> 422 from FastAPI.
    """
    resp = client.post("/api/v1/model/predict-next", json={})
    assert resp.status_code == 422
    data = resp.json()
    assert data["detail"][0]["loc"] == ["body", "ticker"]
