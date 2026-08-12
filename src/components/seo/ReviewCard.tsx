import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Check, X, Lightbulb, Sparkles, Trash2 } from "lucide-react";

export interface Review {
  task_id: string;
  page_url: string;
  message: string;
}

interface ReviewCardProps {
  reviews: Review[];
  loading: boolean;
  onApprove: (taskId: string, approved: boolean) => void;
  onDelete?: (taskId: string) => void;
}

const ReviewCard = ({ reviews, loading, onApprove, onDelete }: ReviewCardProps) => {
  return (
    <div className="card-review-gradient rounded-2xl border border-border p-5 shadow-soft flex-1 min-h-[200px]">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-primary" />
        </div>
        <div>
          <h3 className="font-semibold text-sm">Sugestões da IA</h3>
          <p className="text-xs text-muted-foreground">
            {reviews.length > 0 ? `${reviews.length} sugestão(ões) pendente(s)` : "Aguardando análise"}
          </p>
        </div>
      </div>

      {reviews.length === 0 ? (
        <div className="text-center py-8">
          <Lightbulb className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground mb-1">
            Nenhuma sugestão carregada.
          </p>
          <p className="text-xs text-muted-foreground/70">
            Clique em <span className="text-primary font-medium">"Ver sugestões da IA"</span> após uma varredura.
          </p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[360px] overflow-auto scrollbar-thin pr-1">
          {reviews.map((review, index) => (
            <div
              key={review.task_id}
              className="rounded-xl border border-primary/30 bg-black/30 p-4 hover:border-primary/50 transition-colors group"
            >
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="w-5 h-5 rounded-full bg-primary/20 text-primary text-xs font-bold flex items-center justify-center shrink-0">
                    {index + 1}
                  </span>
                  <span className="text-xs text-primary font-medium truncate">
                    {review.page_url.replace(/^https?:\/\//, '')}
                  </span>
                </div>
                {onDelete && (
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive shrink-0"
                        disabled={loading}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Descartar sugestão?</AlertDialogTitle>
                        <AlertDialogDescription>
                          Esta sugestão será removida permanentemente. Uma nova análise poderá gerar novas sugestões para esta página.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => onDelete(review.task_id)}
                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                          Descartar
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                )}
              </div>
              <pre className="text-xs text-foreground/80 whitespace-pre-wrap bg-muted/30 border border-border/50 rounded-lg p-3 max-h-[150px] overflow-auto scrollbar-thin font-mono leading-relaxed">
                {review.message}
              </pre>
              <div className="flex justify-end gap-2 mt-3">
                <Button
                  size="sm"
                  onClick={() => onApprove(review.task_id, false)}
                  disabled={loading}
                  variant="outline"
                  className="rounded-full border-destructive/40 text-destructive hover:bg-destructive/10 hover:border-destructive text-xs px-4"
                >
                  <X className="w-3 h-3 mr-1" />
                  Rejeitar
                </Button>
                <Button
                  size="sm"
                  onClick={() => onApprove(review.task_id, true)}
                  disabled={loading}
                  className="rounded-full bg-green-600 hover:bg-green-500 text-white text-xs px-4"
                >
                  <Check className="w-3 h-3 mr-1" />
                  Aprovar
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ReviewCard;
