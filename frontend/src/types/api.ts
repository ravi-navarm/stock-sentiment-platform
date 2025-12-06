// Training API types
export interface TrainRequest {
  tickers: string[];
  start_date: string;
  end_date: string;
}

export interface TrainResponse {
  tickers: string[];
  start_date: string;
  end_date: string;
  n_rows: number;
  n_samples: number;
  n_features: number;
  roc_auc: number | null;
}

// Prediction API types
export interface PredictResponse {
  ticker: string;
  prob_up: number;
}

// Error response
export interface ApiError {
  detail: string;
}
