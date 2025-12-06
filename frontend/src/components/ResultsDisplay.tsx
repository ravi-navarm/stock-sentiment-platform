import { TrendingUp, TrendingDown, AlertTriangle, BarChart3, Database, Calendar, CheckCircle, Layers } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { TrainResponse, PredictResponse } from "@/types/api";

interface ResultsDisplayProps {
  result: TrainResponse;
  predictions?: PredictResponse[];
}

const ResultsDisplay = ({ result, predictions }: ResultsDisplayProps) => {
  const isDataInsufficient = result.roc_auc === null;

  // Calculate confidence and prediction strength from ROC-AUC
  const getModelConfidence = (rocAuc: number) => {
    // ROC-AUC of 0.5 = random, 1.0 = perfect
    // Convert to confidence percentage: (roc_auc - 0.5) * 200 gives 0-100%
    return Math.max(0, Math.min(100, (rocAuc - 0.5) * 200));
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Main Prediction Card */}
      {isDataInsufficient ? (
        <Card className="glass-card border-warning/30 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-warning/5 to-transparent pointer-events-none" />
          <CardHeader className="relative">
            <CardTitle className="flex items-center gap-3 text-warning">
              <AlertTriangle className="h-6 w-6" />
              Insufficient Data
            </CardTitle>
          </CardHeader>
          <CardContent className="relative space-y-4">
            <p className="text-muted-foreground">
              The selected date range does not contain enough data to train an accurate model.
              Please increase the span of your data by selecting a wider date range.
            </p>
            <div className="p-4 rounded-lg bg-warning/10 border border-warning/20">
              <p className="text-sm text-warning font-medium">
                Recommendation: Extend the date range by at least 30 days to get better predictions.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Model Training Success */}
          <Card className="glass-card border-success/30 overflow-hidden animate-scale-in">
            <div className="absolute inset-0 bg-gradient-to-br from-success/5 to-transparent pointer-events-none" />
            <CardHeader className="relative">
              <CardTitle className="flex items-center justify-between flex-wrap gap-4">
                <span className="flex items-center gap-3">
                  <CheckCircle className="h-6 w-6 text-success animate-pulse" />
                  <span className="text-success">Model Trained Successfully</span>
                </span>
                <div className="flex gap-3">
                  <Badge 
                    variant="outline" 
                    className="font-mono text-lg px-4 py-2 border-success/50 text-success"
                  >
                    ROC-AUC: {(result.roc_auc! * 100).toFixed(1)}%
                  </Badge>
                  <Badge 
                    variant="outline" 
                    className="font-mono text-lg px-4 py-2 border-primary/50 text-primary"
                  >
                    Confidence: {getModelConfidence(result.roc_auc!).toFixed(0)}%
                  </Badge>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="relative space-y-4">
              <p className="text-muted-foreground">
                The model has been trained on <span className="font-mono text-foreground font-semibold">{result.n_rows}</span> samples with <span className="font-mono text-foreground font-semibold">{result.n_features}</span> features.
              </p>
              
              {/* Model Quality Indicator */}
              <div className="p-4 rounded-lg bg-secondary/50 border border-border/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">Model Prediction Accuracy</span>
                  <span className="text-sm font-mono text-foreground">{(result.roc_auc! * 100).toFixed(1)}%</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-primary to-accent rounded-full transition-all duration-1000 ease-out"
                    style={{ width: `${result.roc_auc! * 100}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  {result.roc_auc! >= 0.7 ? "Strong predictive power" : result.roc_auc! >= 0.6 ? "Moderate predictive power" : "Limited predictive power - consider expanding date range"}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Predictions for each ticker */}
          {predictions && predictions.length > 0 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-primary" />
                Next Day Predictions
              </h3>
              <div className="grid gap-4 md:grid-cols-2">
                {predictions.map((prediction, index) => {
                  const isBullish = prediction.prob_up > 0.5;
                  const isNeutral = prediction.prob_up === 0.5;
                  const sentimentStrength = Math.abs(prediction.prob_up - 0.5) * 200; // 0-100%
                  
                  return (
                    <Card 
                      key={prediction.ticker}
                      className={`glass-card overflow-hidden transition-all duration-300 hover:scale-[1.02] ${isBullish ? 'border-success/30' : isNeutral ? 'border-accent/30' : 'border-destructive/30'}`}
                      style={{ animationDelay: `${index * 0.1}s` }}
                    >
                      <div className={`absolute inset-0 bg-gradient-to-br ${isBullish ? 'from-success/5' : isNeutral ? 'from-accent/5' : 'from-destructive/5'} to-transparent pointer-events-none`} />
                      <CardContent className="relative p-4">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-3">
                            {isBullish ? (
                              <TrendingUp className="h-8 w-8 text-success animate-bounce" style={{ animationDuration: '2s' }} />
                            ) : isNeutral ? (
                              <BarChart3 className="h-8 w-8 text-accent" />
                            ) : (
                              <TrendingDown className="h-8 w-8 text-destructive animate-bounce" style={{ animationDuration: '2s' }} />
                            )}
                            <div>
                              <p className="font-mono font-bold text-xl">{prediction.ticker}</p>
                              <p className={`text-sm font-medium ${isBullish ? 'text-success' : isNeutral ? 'text-accent' : 'text-destructive'}`}>
                                {isBullish ? 'Bullish Sentiment' : isNeutral ? 'Neutral Sentiment' : 'Bearish Sentiment'}
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className={`text-3xl font-mono font-bold ${isBullish ? 'text-success' : isNeutral ? 'text-accent' : 'text-destructive'}`}>
                              {(prediction.prob_up * 100).toFixed(1)}%
                            </p>
                            <p className="text-xs text-muted-foreground">Probability Up</p>
                          </div>
                        </div>
                        
                        {/* Sentiment Strength Bar */}
                        <div className="mt-3 pt-3 border-t border-border/30">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-muted-foreground">Sentiment Strength</span>
                            <span className="text-xs font-mono text-foreground">{sentimentStrength.toFixed(0)}%</span>
                          </div>
                          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                            <div 
                              className={`h-full rounded-full transition-all duration-1000 ease-out ${isBullish ? 'bg-success' : isNeutral ? 'bg-accent' : 'bg-destructive'}`}
                              style={{ width: `${sentimentStrength}%` }}
                            />
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="stat-card transition-all duration-300 hover:scale-[1.03] hover:shadow-lg" style={{ animationDelay: '0.1s' }}>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Database className="h-4 w-4" />
              <span className="text-xs uppercase tracking-wider">Samples</span>
            </div>
            <p className="text-2xl font-mono font-semibold text-foreground">{result.n_rows ?? result.n_samples ?? 0}</p>
          </CardContent>
        </Card>

        <Card className="stat-card transition-all duration-300 hover:scale-[1.03] hover:shadow-lg" style={{ animationDelay: '0.15s' }}>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Layers className="h-4 w-4" />
              <span className="text-xs uppercase tracking-wider">Features</span>
            </div>
            <p className="text-2xl font-mono font-semibold text-foreground">{result.n_features ?? 0}</p>
          </CardContent>
        </Card>

        <Card className="stat-card transition-all duration-300 hover:scale-[1.03] hover:shadow-lg" style={{ animationDelay: '0.2s' }}>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Calendar className="h-4 w-4" />
              <span className="text-xs uppercase tracking-wider">From</span>
            </div>
            <p className="text-sm font-mono font-semibold text-foreground">{result.start_date ?? '-'}</p>
          </CardContent>
        </Card>

        <Card className="stat-card transition-all duration-300 hover:scale-[1.03] hover:shadow-lg" style={{ animationDelay: '0.25s' }}>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Calendar className="h-4 w-4" />
              <span className="text-xs uppercase tracking-wider">To</span>
            </div>
            <p className="text-sm font-mono font-semibold text-foreground">{result.end_date ?? '-'}</p>
          </CardContent>
        </Card>
      </div>

      {/* Tickers */}
      <Card className="stat-card">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 text-muted-foreground mb-3">
            <CheckCircle className="h-4 w-4" />
            <span className="text-xs uppercase tracking-wider">Analyzed Tickers</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {result.tickers.map((ticker) => (
              <Badge key={ticker} variant="secondary" className="font-mono text-sm px-3 py-1">
                {ticker}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ResultsDisplay;
