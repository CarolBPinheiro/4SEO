import { Loader2 } from "lucide-react";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  text?: string;
  className?: string;
}

const sizes = {
  sm: "w-4 h-4",
  md: "w-6 h-6",
  lg: "w-8 h-8",
};

export function LoadingSpinner({ size = "md", text, className = "" }: LoadingSpinnerProps) {
  return (
    <div className={`flex items-center justify-center gap-2 ${className}`}>
      <Loader2 className={`animate-spin text-primary ${sizes[size]}`} />
      {text && <span className="text-sm text-muted-foreground">{text}</span>}
    </div>
  );
}

interface LoadingCardProps {
  title?: string;
  description?: string;
}

export function LoadingCard({ title = "Carregando...", description }: LoadingCardProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="relative">
        <div className="w-16 h-16 rounded-full border-4 border-muted animate-pulse" />
        <Loader2 className="w-8 h-8 text-primary animate-spin absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
      </div>
      <h3 className="mt-4 font-medium">{title}</h3>
      {description && (
        <p className="mt-1 text-sm text-muted-foreground text-center max-w-xs">
          {description}
        </p>
      )}
    </div>
  );
}

interface LoadingDotsProps {
  text?: string;
}

export function LoadingDots({ text = "Carregando" }: LoadingDotsProps) {
  return (
    <span className="inline-flex items-center gap-1">
      {text}
      <span className="inline-flex gap-0.5">
        <span className="w-1 h-1 rounded-full bg-current animate-bounce" style={{ animationDelay: "0ms" }} />
        <span className="w-1 h-1 rounded-full bg-current animate-bounce" style={{ animationDelay: "150ms" }} />
        <span className="w-1 h-1 rounded-full bg-current animate-bounce" style={{ animationDelay: "300ms" }} />
      </span>
    </span>
  );
}

interface LoadingSkeletonProps {
  className?: string;
  variant?: "text" | "circular" | "rectangular";
}

export function LoadingSkeleton({ className = "", variant = "rectangular" }: LoadingSkeletonProps) {
  const baseClass = "bg-muted animate-pulse";
  
  const variantClasses = {
    text: "h-4 rounded",
    circular: "rounded-full",
    rectangular: "rounded-lg",
  };
  
  return <div className={`${baseClass} ${variantClasses[variant]} ${className}`} />;
}

interface LoadingTableProps {
  rows?: number;
  columns?: number;
}

export function LoadingTable({ rows = 5, columns = 4 }: LoadingTableProps) {
  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex gap-4 pb-2 border-b">
        {Array.from({ length: columns }).map((_, i) => (
          <LoadingSkeleton key={i} className="h-4 flex-1" variant="text" />
        ))}
      </div>
      
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-4 py-2">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <LoadingSkeleton 
              key={colIndex} 
              className={`h-4 ${colIndex === 0 ? "w-32" : "flex-1"}`} 
              variant="text" 
            />
          ))}
        </div>
      ))}
    </div>
  );
}

interface LoadingProductCardProps {
  count?: number;
}

export function LoadingProductCard({ count = 3 }: LoadingProductCardProps) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 p-3 rounded-lg border">
          <LoadingSkeleton className="w-12 h-12 shrink-0" />
          <div className="flex-1 space-y-2">
            <LoadingSkeleton className="h-4 w-3/4" variant="text" />
            <LoadingSkeleton className="h-3 w-1/2" variant="text" />
          </div>
          <LoadingSkeleton className="w-6 h-6" />
        </div>
      ))}
    </div>
  );
}

export default LoadingSpinner;
