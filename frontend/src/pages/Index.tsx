import { useState } from "react";
import { format } from "date-fns";
import { Brain, Sparkles, Activity, AlertCircle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import TickerInput from "@/components/TickerInput";
import DateRangePicker from "@/components/DateRangePicker";
import ResultsDisplay from "@/components/ResultsDisplay";
import LoadingState from "@/components/LoadingState";
import type { TrainResponse, PredictResponse, ApiError } from "@/types/api";

const API_BASE = "http://127.0.0.1:8000/api/v1/model";

const Index = () => {
  const [tickers, setTickers] = useState<string[]>([]);
  const [startDate, setStartDate] = useState<Date | undefined>();
  const [endDate, setEndDate] = useState<Date | undefined>();
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<TrainResponse | null>(null);
  const [predictions, setPredictions] = useState<PredictResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const fetchPredictions = async (trainedTickers: string[]): Promise<PredictResponse[]> => {
    const results: PredictResponse[] = [];
    
    for (const ticker of trainedTickers) {
      try {
        const response = await fetch(`${API_BASE}/predict-next?ticker=${ticker}`);
        if (response.ok) {
          const data: PredictResponse = await response.json();
          results.push(data);
        }
      } catch {
        // Skip failed predictions silently
      }
    }
    
    return results;
  };

  const handleTrain = async () => {
    if (tickers.length === 0) {
      toast({
        title: "No tickers selected",
        description: "Please add at least one stock ticker to analyze.",
        variant: "destructive",
      });
      return;
    }

    if (!startDate || !endDate) {
      toast({
        title: "Date range required",
        description: "Please select both start and end dates.",
        variant: "destructive",
      });
      return;
    }

    if (startDate > endDate) {
      toast({
        title: "Invalid date range",
        description: "Start date must be before end date.",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);
    setPredictions([]);

    try {
      const response = await fetch(`${API_BASE}/train`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          tickers,
          start_date: format(startDate, "yyyy-MM-dd"),
          end_date: format(endDate, "yyyy-MM-dd"),
        }),
      });

      if (!response.ok) {
        const errorData: ApiError = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data: TrainResponse = await response.json();
      setResult(data);

      if (data.roc_auc === null) {
        toast({
          title: "Insufficient Data",
          description: "Please increase the date range for better predictions.",
          variant: "destructive",
        });
      } else {
        // Fetch predictions for each ticker after successful training
        const predictionResults = await fetchPredictions(data.tickers);
        setPredictions(predictionResults);
        
        toast({
          title: "Analysis Complete",
          description: `Model trained with ROC-AUC of ${(data.roc_auc * 100).toFixed(1)}%.`,
        });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to train model";
      setError(message);
      toast({
        title: "Error",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const isFormValid = tickers.length > 0 && startDate !== undefined && endDate !== undefined;

  const handleReset = () => {
    setTickers([]);
    setStartDate(undefined);
    setEndDate(undefined);
    setResult(null);
    setPredictions([]);
    setError(null);
  };

  const hasAnyData = tickers.length > 0 || startDate || endDate || result || error;

  return (
    <div className="min-h-screen bg-background">
      {/* Ambient background effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-accent/5 rounded-full blur-3xl" />
      </div>

      <div className="relative container mx-auto px-4 py-8 md:py-16 max-w-4xl">
        {/* Header */}
        <header className="text-center mb-12 animate-fade-in">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-6">
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-primary">AI-Powered Analysis</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            <span className="text-gradient">Stock Sentiment</span>
            <br />
            <span className="text-foreground">Predictor</span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Leverage advanced sentiment analysis to predict stock price movements. 
            Enter your tickers and date range to get AI-driven insights.
          </p>
        </header>

        {/* Main Form Card */}
        <Card className="glass-card mb-8 animate-fade-in" style={{ animationDelay: "0.1s" }}>
          <CardHeader>
            <CardTitle className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/10">
                <Brain className="h-5 w-5 text-primary" />
              </div>
              Configure Analysis
            </CardTitle>
            <CardDescription>
              Select the stocks and date range for sentiment prediction
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <TickerInput tickers={tickers} onTickersChange={setTickers} />
            <DateRangePicker
              startDate={startDate}
              endDate={endDate}
              onStartDateChange={setStartDate}
              onEndDateChange={setEndDate}
            />
            <div className="flex gap-3">
              <Button
                onClick={handleTrain}
                disabled={!isFormValid || isLoading}
                variant="glow"
                size="lg"
                className="flex-1 transition-all duration-200"
              >
                {isLoading ? (
                  <>
                    <Activity className="h-5 w-5 animate-pulse" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Brain className="h-5 w-5" />
                    Analyze Sentiment
                  </>
                )}
              </Button>
              {hasAnyData && (
                <Button
                  onClick={handleReset}
                  variant="outline"
                  size="lg"
                  className="px-4 transition-all duration-200 hover:bg-destructive/10 hover:border-destructive/50 hover:text-destructive"
                  disabled={isLoading}
                >
                  <RotateCcw className="h-5 w-5" />
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Loading State */}
        {isLoading && <LoadingState />}

        {/* Error State */}
        {error && !isLoading && (
          <Card className="glass-card border-destructive/30 animate-fade-in">
            <CardContent className="p-6 flex items-start gap-4">
              <div className="p-2 rounded-lg bg-destructive/10">
                <AlertCircle className="h-5 w-5 text-destructive" />
              </div>
              <div>
                <h3 className="font-semibold text-destructive mb-1">Error</h3>
                <p className="text-sm text-muted-foreground">{error}</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Results */}
        {result && !isLoading && <ResultsDisplay result={result} predictions={predictions} />}

        {/* Footer */}
        <footer className="mt-16 text-center text-sm text-muted-foreground animate-fade-in" style={{ animationDelay: "0.2s" }}>
          <p>Stock Sentiment Predictor • Powered by Machine Learning</p>
        </footer>
      </div>
    </div>
  );
};

export default Index;
