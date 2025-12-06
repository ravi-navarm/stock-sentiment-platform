# tests/test_stocks_popular.py

from fastapi.testclient import TestClient


def test_S1_popular_stocks(client: TestClient):
    """
    S1: /api/v1/stocks/popular returns a list of known symbols.
    """
    resp = client.get("/api/v1/stocks/popular")
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 5

    # Make sure some of your expected symbols are present
    symbols = {item["symbol"] for item in data}
    for sym in ["AAPL", "MSFT", "AMZN", "TSLA"]:
        assert sym in symbols
