import { Brain, Loader2 } from "lucide-react";

const LoadingState = () => {
  return (
    <div className="flex flex-col items-center justify-center py-16 space-y-6 animate-fade-in">
      <div className="relative">
        <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl animate-pulse" />
        <div className="relative bg-gradient-to-br from-primary to-accent p-6 rounded-full">
          <Brain className="h-12 w-12 text-primary-foreground animate-pulse" />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Loader2 className="h-5 w-5 animate-spin text-primary" />
        <p className="text-lg text-muted-foreground">Training sentiment model...</p>
      </div>
      <p className="text-sm text-muted-foreground/70">This may take a few moments</p>
    </div>
  );
};

export default LoadingState;
