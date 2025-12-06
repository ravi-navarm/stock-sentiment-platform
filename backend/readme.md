# Stock Sentiment Platform – Backend API Test Cases & Results

This document collects the high–level behavior of the automated tests in:

- `tests/test_model_train.py`
- `tests/test_model_predict.py`

It summarizes **what each test does**, **the request it makes**, and **what the
response should look like** (status code + important JSON fields).

At the time of capture:

- ✅ 16 tests passed
- ⚠️ 15 warnings (non‑fatal, mostly from `yfinance` and `pandas`)

---

## 1. Overall Pytest Run

**Command (example):**

```bash
pytest -q
```

**Result:**

```text
................                                                         [100%]
=============================== warnings summary ===============================
tests/test_model_predict.py::test_P1_predict_after_train
tests/test_model_predict.py::test_P3_predict_for_unknown_ticker
tests/test_model_train.py::test_T3_small_window_ok
tests/test_model_train.py::test_T4_invalid_ticker_no_price_data
tests/test_model_train.py::test_T5_future_dates_no_price_data
tests/test_model_train.py::test_T10_large_window_train_success
tests/test_model_train.py::test_T11_large_window_again_idempotent
tests/test_model_train.py::test_T12_multi_ticker_train
tests/test_model_train.py::test_T12_multi_ticker_train
  app/services/market_data_service.py:38: FutureWarning: YF.download() has changed argument auto_adjust default to True
    df_yf = yf.download(

tests/test_model_predict.py::test_P1_predict_after_train
tests/test_model_predict.py::test_P3_predict_for_unknown_ticker
tests/test_model_train.py::test_T3_small_window_ok
tests/test_model_train.py::test_T10_large_window_train_success
tests/test_model_train.py::test_T11_large_window_again_idempotent
tests/test_model_train.py::test_T12_multi_ticker_train
  app/services/feature_service.py:203: FutureWarning: DataFrameGroupBy.apply operated on the grouping columns. This behavior is deprecated, and in a future version of pandas the grouping columns will be excluded from the operation. Either pass `include_groups=False` to exclude the groupings or explicitly select the grouping columns after groupby to silence this warning.

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
16 passed, 15 warnings in 3.78s
```

Warnings are **non‑fatal** and come from:

- `yfinance` – change in `auto_adjust` default.
- `pandas` – deprecation of `DataFrameGroupBy.apply` including grouping columns.

---

## 2. Prediction Endpoint Tests – `/api/v1/model/predict-next`

These tests live in `tests/test_model_predict.py`.

### 2.1 `test_P1_predict_after_train`

**Intent:**  
Verify we can **train** on AAPL for a non‑trivial window and then **predict**
the next‑day probability for AAPL.

#### Step 1 – Train

- **Endpoint:** `POST /api/v1/model/train`
- **JSON body (example used in tests):**

```json
{
  "tickers": ["AAPL"],
  "start_date": "2025-11-01",
  "end_date": "2025-12-04"
}
```

**Expected response:**

- Status: `200 OK`
- JSON:
  - `tickers` – list containing `"AAPL"`
  - `start_date` – `"2025-11-01"`
  - `end_date` – `"2025-12-04"`
  - `n_rows` (or `n_samples`) – integer `>= 2`
  - `n_features` – integer `> 0`
  - `roc_auc` – either `null` or a float between `0.0` and `1.0`

Example:

```json
{
  "tickers": ["AAPL"],
  "start_date": "2025-11-01",
  "end_date": "2025-12-04",
  "n_rows": 22,
  "n_samples": 22,
  "n_features": 10,
  "roc_auc": 0.65
}
```

(Exact numbers may differ; the tests only assert basic constraints.)

#### Step 2 – Predict next

- **Endpoint:** `GET /api/v1/model/predict-next?ticker=AAPL`

**Expected response:**

- Status: `200 OK`
- JSON:
  - `ticker` – `"AAPL"` (uppercased)
  - `prob_up` – float between `0.0` and `1.0`

Example:

```json
{
  "ticker": "AAPL",
  "prob_up": 0.57
}
```

### 2.2 `test_P3_predict_for_unknown_ticker`

**Intent:**  
Verify that after training on AAPL only, if we call `/predict-next` for a
ticker **not present in the training data** (e.g. MSFT), we get a **400** with
a clear error message.

#### Step 1 – Train on AAPL (same as above)

- `POST /api/v1/model/train` with:

```json
{
  "tickers": ["AAPL"],
  "start_date": "2025-11-01",
  "end_date": "2025-12-04"
}
```

> Expect **200 OK** like in P1.

#### Step 2 – Predict for MSFT

- **Endpoint:** `GET /api/v1/model/predict-next?ticker=MSFT`

**Expected response:**

- Status: `400 Bad Request`
- JSON:

```json
{
  "detail": "No training samples found for ticker 'MSFT'"
}
```

The exact string might vary slightly, but tests look for the phrase
`"No training samples found"` in the `detail`.

---

## 3. Training Endpoint Tests – `/api/v1/model/train`

These tests live in `tests/test_model_train.py`.

### 3.1 `test_T1_missing_tickers`

**Intent:**  
If neither `ticker` nor `tickers` is provided, the API should **reject** the
request with a clear 400 error.

- **Endpoint:** `POST /api/v1/model/train`
- **JSON body:**

```json
{
  "start_date": "2025-11-01",
  "end_date": "2025-11-10"
}
```

**Expected response:**

- Status: `400 Bad Request`
- JSON:

```json
{
  "detail": "At least one ticker is required (ticker or tickers field)."
}
```

### 3.2 `test_T2_start_equals_end_not_enough_rows`

**Intent:**  
If `start_date == end_date`, tests treat this as a **single‑row** window and
expect a **"Not enough rows"** error.

- **Endpoint:** `POST /api/v1/model/train`
- **JSON body:**

```json
{
  "tickers": ["AAPL"],
  "start_date": "2025-12-01",
  "end_date": "2025-12-01"
}
```

**Expected response:**

- Status: `400 Bad Request`
- JSON `detail` containing:

```text
"Not enough rows to train a model (n=1). Need at least 2."
```

(The test asserts that `"Not enough rows"` is in the `detail`.)

### 3.3 `test_T3_small_window_ok`

**Intent:**  
For a small but valid window (e.g. a few days), model training should succeed.

- **Endpoint:** `POST /api/v1/model/train`
- **JSON body:**

```json
{
  "tickers": ["AAPL"],
  "start_date": "2025-12-01",
  "end_date": "2025-12-04"
}
```

**Expected response:**

- Status: `200 OK`
- JSON fields:
  - `tickers` includes `"AAPL"`
  - `start_date` and `end_date` match the request
  - `n_rows >= 2`
  - `n_features > 0`
  - `roc_auc` is `null` or a float in `[0,1]`

Example:

```json
{
  "tickers": ["AAPL"],
  "start_date": "2025-12-01",
  "end_date": "2025-12-04",
  "n_rows": 3,
  "n_samples": 3,
  "n_features": 10,
  "roc_auc": 0.5
}
```

### 3.4 `test_T4_invalid_ticker_no_price_data`

**Intent:**  
If `yfinance` / market data service returns no rows (because the ticker is
invalid or there is no data for the window), the API should respond with a
400 + error message about missing price data.

- **Endpoint:** `POST /api/v1/model/train`
- **JSON body:**

```json
{
  "tickers": ["THIS_TICKER_DOES_NOT_EXIST_123"],
  "start_date": "2025-11-01",
  "end_date": "2025-11-10"
}
```

**Expected response:**

- Status: `400 Bad Request`
- JSON:

```json
{
  "detail": "No price data returned for given tickers and date range"
}
```

### 3.5 `test_T5_future_dates_no_price_data`

**Intent:**  
If `start_date` and `end_date` are in the future (no market data yet), the
data service will return an empty frame and training should fail similarly to
T4.

- **Endpoint:** `POST /api/v1/model/train`
- **JSON body:**

```json
{
  "tickers": ["AAPL"],
  "start_date": "2100-01-01",
  "end_date": "2100-01-05"
}
```

**Expected response:**

- Status: `400 Bad Request`
- JSON:

```json
{
  "detail": "No price data returned for given tickers and date range"
}
```

### 3.6 `test_T6_start_after_end_invalid_range`

**Intent:**  
If `start_date > end_date`, the API should reject the request.

- **Endpoint:** `POST /api/v1/model/train`
- **JSON body:**

```json
{
  "tickers": ["AAPL"],
  "start_date": "2025-12-10",
  "end_date": "2025-11-01"
}
```

**Expected response:**

- Status: `400 Bad Request`
- JSON:

```json
{
  "detail": "start_date must be before end_date"
}
```

### 3.7 `test_T7_single_ticker_via_ticker_field`

**Intent:**  
Verify that the single `ticker` field is accepted, not just `tickers`.

- **Endpoint:** `POST /api/v1/model/train`
- **JSON body:**

```json
{
  "ticker": "AAPL",
  "start_date": "2025-11-01",
  "end_date": "2025-11-10"
}
```

**Expected response:**

- Status: `200 OK`
- JSON:
  - `tickers` list includes `"AAPL"`
  - other fields as in previous successful training tests.

### 3.8 `test_T8_tickers_with_duplicates_and_spaces`

**Intent:**  
Ensure ticker normalization: uppercase, trim spaces, remove duplicates.

- **Endpoint:** `POST /api/v1/model/train`
- **JSON body (example):**

```json
{
  "tickers": [" aapl ", "AAPL", "aApL  "],
  "start_date": "2025-11-01",
  "end_date": "2025-11-10"
}
```

**Expected behavior:**

- After training, the response `tickers` should be something like:

```json
{
  "tickers": ["AAPL"],
  "start_date": "2025-11-01",
  "end_date": "2025-11-10",
  "n_rows": 7,
  "n_features": 10,
  "roc_auc": 0.55
}
```

- Only one `"AAPL"` is present.
- Status: `200 OK`.

### 3.9 `test_T9_train_handles_small_sample_warning`

**Intent:**  
When there are very few rows (but at least 2), training should still succeed;
the logging may emit a warning, but API must still return 200.

- **Endpoint:** `POST /api/v1/model/train`
- **JSON body:**

```json
{
  "tickers": ["AAPL"],
  "start_date": "2025-12-02",
  "end_date": "2025-12-04"
}
```

**Expected response:**

- Status: `200 OK`
- JSON with `n_rows >= 2`, `n_features > 0`.
- `roc_auc` may be `null` if all labels in the training set are 0 or 1.

### 3.10 `test_T10_large_window_train_success`

**Intent:**  
Verify that a larger training window works and returns sane metrics.

- **Endpoint:** `POST /api/v1/model/train`
- **JSON body:**

```json
{
  "tickers": ["AAPL"],
  "start_date": "2025-11-01",
  "end_date": "2025-12-04"
}
```

**Expected response:**

- Status: `200 OK`
- JSON:
  - `tickers`: `["AAPL"]`
  - `start_date`, `end_date` echo the request.
  - `n_rows >= 2`
  - `n_features > 0`
  - `roc_auc` is `null` or float in `[0,1]`

### 3.11 `test_T11_large_window_again_idempotent`

**Intent:**  
Call the same large‑window training as T10 again to ensure behavior is stable
(idempotent-ish, i.e., no crashes, 200 OK).

- **Endpoint:** `POST /api/v1/model/train`
- **JSON body:** **same as T10**

```json
{
  "tickers": ["AAPL"],
  "start_date": "2025-11-01",
  "end_date": "2025-12-04"
}
```

**Expected response:**

- Status: `200 OK`
- JSON: same fields/constraints as T10.

### 3.12 `test_T12_multi_ticker_train`

**Intent:**  
Ensure that **multi‑ticker training** (e.g. `["AAPL", "MSFT"]`) works even
with yfinance’s multi‑ticker data shapes and that our feature engineering is
robust.

- **Endpoint:** `POST /api/v1/model/train`
- **JSON body:**

```json
{
  "tickers": ["AAPL", "MSFT"],
  "start_date": "2025-11-01",
  "end_date": "2025-12-04"
}
```

**Expected response:**

- Status: `200 OK`
- JSON (example):

```json
{
  "tickers": ["AAPL", "MSFT"],
  "start_date": "2025-11-01",
  "end_date": "2025-12-04",
  "n_rows": 44,
  "n_samples": 44,
  "n_features": 10,
  "roc_auc": 0.62
}
```

- `tickers` must include **both** `"AAPL"` and `"MSFT"` (order not important).

---

## 4. Notes on Implementation

- `add_price_features` is responsible for:

  - normalizing yfinance outputs (MultiIndex columns, index levels `Ticker`/`Date`)
  - ensuring columns `["ticker", "date", "Close", "Volume"]` exist
  - computing features like `ret_1d`, `ret_5d`, `vol_5d`, `vol_21d`, `volume_z`, `day_of_week`.

- `train_global_model` (or `train_model` in some versions) is responsible for:

  - selecting numeric feature columns
  - cleaning NaNs
  - fitting a `LogisticRegression` or `RandomForest`
  - computing training‑set ROC‑AUC when both classes are present.

- `/api/v1/model/predict-next` uses the last trained DataFrame and model to
  grab the **latest row** for the requested ticker and returns
  `prob_up = P(target_up=1 | features)`.

---

_End of test case summary file._
