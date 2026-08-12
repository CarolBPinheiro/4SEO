import { Loader2 } from "lucide-react";

const LoadingOverlay = () => {
  return (
    <div className="fixed inset-0 bg-background/90 backdrop-blur-md flex flex-col items-center justify-center gap-5 z-50">
      <div className="relative">
        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
        </div>
        <div className="absolute inset-0 rounded-full bg-primary/20 animate-ping" />
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-foreground mb-1">
          Processando com IA
        </p>
        <p className="text-xs text-muted-foreground">
          Isso pode levar alguns segundos...
        </p>
      </div>
    </div>
  );
};

export default LoadingOverlay;
