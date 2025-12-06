# Stock Sentiment Platform (Monorepo)

This repository contains both the **backend API** and the **frontend web app** for my stock sentiment platform.

The idea is simple:

- Pull historical price data for selected tickers
- Engineer features (returns, volatility, sentiment, etc.)
- Train a classification model to predict whether the next day’s close will be **up or down**
- Expose the model via a FastAPI backend
- Interact with everything through a React + TypeScript frontend

---

## Tech stack

- **Backend**

  - Python
  - FastAPI
  - scikit-learn, pandas, numpy
  - pytest for tests

- **Frontend**
  - React
  - TypeScript
  - Vite
  - Tailwind CSS
  - shadcn/ui for components

---

## Repository structure

```text
backend/   → FastAPI app, ML training, model serving
frontend/  → React + TypeScript app (UI for training & predictions)
```
# stock-sentiment-platform
