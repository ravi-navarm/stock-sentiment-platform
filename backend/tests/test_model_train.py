# tests/test_model_train.py

from fastapi.testclient import TestClient


def test_T2_small_range_not_enough_rows(client: TestClient):
    """
    T2: start_date == end_date -> too few rows -> 400 with clear message.
    """
    payload = {
        "tickers": ["AAPL"],
        "start_date": "2025-12-04",
        "end_date": "2025-12-04",
    }
    resp = client.post("/api/v1/model/train", json=payload)
    # After your try/except this should be 400, not 500
    assert resp.status_code == 400
    data = resp.json()
    assert "Not enough rows" in data["detail"]


def test_T3_small_window_ok(client: TestClient):
    """
    T3: small but valid window (a few days), training should succeed.
    """
    payload = {
        "tickers": ["AAPL"],
        "start_date": "2025-12-01",
        "end_date": "2025-12-04",
    }
    resp = client.post("/api/v1/model/train", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["message"] == "Training completed"
    assert data["tickers"] == ["AAPL"]
    assert data["train_rows"] >= 1
    assert data["price_rows"] >= data["train_rows"]
    # roc_auc may be None if only one class in y_test
    assert "roc_auc" in data


def test_T4_invalid_ticker_no_price_data(client: TestClient):
    """
    T4: bogus ticker -> yfinance returns empty -> 400 with 'No price data' detail.
    """
    payload = {
        "tickers": ["THIS_TICKER_DOES_NOT_EXIST_123"],
        "start_date": "2025-11-01",
        "end_date": "2025-11-10",
    }
    resp = client.post("/api/v1/model/train", json=payload)
    assert resp.status_code == 400
    data = resp.json()
    assert data["detail"].startswith("No price data returned for given tickers")


def test_T5_future_dates_no_price_data(client: TestClient):
    """
    T5: very future dates where AAPL has no prices -> 400 + no price data.
    """
    payload = {
        "tickers": ["AAPL"],
        "start_date": "2099-01-01",
        "end_date": "2099-01-10",
    }
    resp = client.post("/api/v1/model/train", json=payload)
    assert resp.status_code == 400
    data = resp.json()
    assert data["detail"].startswith("No price data returned for given tickers")


def test_T6_missing_tickers_empty_list(client: TestClient):
    """
    T6: tickers=[] or only empty strings -> 400 'At least one ticker is required'.
    """
    payload = {
        "tickers": [],
        "start_date": "2025-11-01",
        "end_date": "2025-12-04",
    }
    resp = client.post("/api/v1/model/train", json=payload)
    assert resp.status_code == 400
    data = resp.json()
    assert "At least one ticker is required" in data["detail"]


def test_T7_missing_ticker_fields_entirely(client: TestClient):
    """
    T7: no 'ticker' or 'tickers' fields at all -> same 400 error.
    """
    payload = {
        "start_date": "2025-11-01",
        "end_date": "2025-12-04",
    }
    resp = client.post("/api/v1/model/train", json=payload)
    assert resp.status_code == 400
    data = resp.json()
    assert "At least one ticker is required" in data["detail"]


def test_T8_invalid_date_format(client: TestClient):
    """
    T8: invalid date strings -> Pydantic validation error (422).
    Matches the error you saw for '11-01-2025' and '2025/12/04'.
    """
    payload = {
        "tickers": ["AAPL"],
        "start_date": "11-01-2025",   # wrong format
        "end_date": "2025/12/04",     # wrong separator
    }
    resp = client.post("/api/v1/model/train", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    # Just sanity check we got validation issues for both fields
    locs = [err["loc"] for err in data["detail"]]
    assert ["body", "start_date"] in locs
    assert ["body", "end_date"] in locs


def test_T9_start_after_end(client: TestClient):
    """
    T9: start_date > end_date -> 400 'start_date must be before end_date'.
    """
    payload = {
        "tickers": ["AAPL"],
        "start_date": "2025-12-04",
        "end_date": "2025-11-01",
    }
    resp = client.post("/api/v1/model/train", json=payload)
    assert resp.status_code == 400
    data = resp.json()
    assert data["detail"] == "start_date must be before end_date"


def test_T10_large_window_train_success(client: TestClient):
    """
    T10: bigger window (like your example) -> success, >=2 rows, roc_auc present.
    """
    payload = {
        "tickers": ["AAPL"],
        "start_date": "2025-11-01",
        "end_date": "2025-12-04",
    }
    resp = client.post("/api/v1/model/train", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["message"] == "Training completed"
    assert data["tickers"] == ["AAPL"]
    assert data["train_rows"] >= 2
    assert data["price_rows"] >= data["train_rows"]
    assert "roc_auc" in data


def test_T11_large_window_again_idempotent(client: TestClient):
    """
    T11: same as T10 to ensure it stays stable (idempotent-ish).
    """
    payload = {
        "tickers": ["AAPL"],
        "start_date": "2025-11-01",
        "end_date": "2025-12-04",
    }
    resp = client.post("/api/v1/model/train", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["message"] == "Training completed"
    assert data["tickers"] == ["AAPL"]
    assert data["train_rows"] >= 2
    assert data["price_rows"] >= data["train_rows"]


def test_T12_multi_ticker_train(client: TestClient):
    """
    T12: multi-ticker request. Previously crashed in add_price_features,
    now should succeed after the 'ret_1d' bug fix.
    """
    payload = {
        "tickers": ["AAPL", "MSFT"],
        "start_date": "2025-11-01",
        "end_date": "2025-12-04",
    }
    resp = client.post("/api/v1/model/train", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["message"] == "Training completed"
    assert set(data["tickers"]) == {"AAPL", "MSFT"}
    assert data["train_rows"] >= 2