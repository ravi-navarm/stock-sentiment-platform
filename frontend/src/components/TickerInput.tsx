import { useState, KeyboardEvent } from "react";
import { X, Plus, TrendingUp } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface TickerInputProps {
  tickers: string[];
  onTickersChange: (tickers: string[]) => void;
}

const POPULAR_STOCKS = [
  { ticker: "AAPL", name: "Apple" },
  { ticker: "GOOGL", name: "Google" },
  { ticker: "MSFT", name: "Microsoft" },
  { ticker: "AMZN", name: "Amazon" },
  { ticker: "TSLA", name: "Tesla" },
  { ticker: "META", name: "Meta" },
  { ticker: "NVDA", name: "NVIDIA" },
  { ticker: "JPM", name: "JPMorgan" },
];

const TickerInput = ({ tickers, onTickersChange }: TickerInputProps) => {
  const [inputValue, setInputValue] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);

  const addTicker = (ticker?: string) => {
    const tickerToAdd = (ticker || inputValue).trim().toUpperCase();
    if (tickerToAdd && !tickers.includes(tickerToAdd)) {
      onTickersChange([...tickers, tickerToAdd]);
      setInputValue("");
    }
    setShowSuggestions(false);
  };

  const removeTicker = (tickerToRemove: string) => {
    onTickersChange(tickers.filter((t) => t !== tickerToRemove));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addTicker();
    }
  };

  const availableSuggestions = POPULAR_STOCKS.filter(
    (stock) => !tickers.includes(stock.ticker)
  );

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium text-foreground">
        Stock Tickers
      </label>
      <div className="relative">
        <div className="flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            placeholder="Enter ticker (e.g., AAPL)"
            className="flex-1 bg-input/50 border-border/50 focus:border-primary"
          />
          <Button
            type="button"
            onClick={() => addTicker()}
            variant="secondary"
            size="icon"
            disabled={!inputValue.trim()}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        {/* Suggestions Dropdown */}
        {showSuggestions && availableSuggestions.length > 0 && (
          <div className="absolute z-50 w-full mt-2 p-2 rounded-lg bg-popover border border-border shadow-xl animate-fade-in">
            <div className="flex items-center gap-2 px-2 py-1.5 mb-2 text-xs text-muted-foreground uppercase tracking-wider">
              <TrendingUp className="h-3 w-3" />
              Popular Stocks
            </div>
            <div className="grid grid-cols-2 gap-1">
              {availableSuggestions.map((stock) => (
                <button
                  key={stock.ticker}
                  type="button"
                  onClick={() => addTicker(stock.ticker)}
                  className="flex items-center justify-between px-3 py-2 rounded-md text-left hover:bg-secondary transition-colors"
                >
                  <span className="font-mono font-semibold text-foreground">
                    {stock.ticker}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {stock.name}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {tickers.length > 0 && (
        <div className="flex flex-wrap gap-2 animate-fade-in">
          {tickers.map((ticker) => (
            <Badge
              key={ticker}
              variant="secondary"
              className="px-3 py-1.5 text-sm font-mono bg-secondary/80 hover:bg-secondary transition-colors"
            >
              {ticker}
              <button
                type="button"
                onClick={() => removeTicker(ticker)}
                className="ml-2 hover:text-destructive transition-colors"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
};

export default TickerInput;
