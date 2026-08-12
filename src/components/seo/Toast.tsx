import { cn } from "@/lib/utils";
import { CheckCircle, AlertCircle, Info, X } from "lucide-react";
import { useEffect, useState } from "react";

export interface ToastData {
  message: string;
  type: "info" | "success" | "error";
}

interface ToastProps {
  toast: ToastData;
}

const Toast = ({ toast }: ToastProps) => {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(false), 4000);
    return () => clearTimeout(timer);
  }, [toast]);

  if (!visible) return null;

  const Icon = {
    info: Info,
    success: CheckCircle,
    error: AlertCircle,
  }[toast.type];

  const styles = {
    info: "border-primary/40 bg-card/95",
    success: "border-green-500/50 bg-green-950/90",
    error: "border-destructive/60 bg-red-950/90",
  };

  const iconStyles = {
    info: "text-primary",
    success: "text-green-500",
    error: "text-destructive",
  };

  return (
    <div
      className={cn(
        "fixed bottom-5 right-5 px-4 py-3 rounded-xl border shadow-lg z-50 flex items-center gap-3 animate-slide-in backdrop-blur-md max-w-[90vw] sm:max-w-md",
        styles[toast.type]
      )}
    >
      <div className={cn("w-8 h-8 rounded-full flex items-center justify-center shrink-0", 
        toast.type === "success" ? "bg-green-500/20" : 
        toast.type === "error" ? "bg-destructive/20" : "bg-primary/20"
      )}>
        <Icon className={cn("w-4 h-4", iconStyles[toast.type])} />
      </div>
      <span className="text-sm text-foreground flex-1">{toast.message}</span>
      <button
        onClick={() => setVisible(false)}
        className="text-muted-foreground hover:text-foreground transition-colors shrink-0"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

export default Toast;
