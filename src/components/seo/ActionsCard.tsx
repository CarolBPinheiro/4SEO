import { Button } from "@/components/ui/button";
import { Rocket, Lightbulb, ExternalLink, FileSearch, Info } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import type { Site } from "./SiteList";

interface ActionsCardProps {
  site: Site;
  loading: boolean;
  onScan: () => void;
  onReview: () => void;
}

const ActionsCard = ({ site, loading, onScan, onReview }: ActionsCardProps) => {
  return (
    <div className="card-gradient rounded-2xl border border-border p-5 shadow-soft">
      {/* Badge de Auditoria */}
      <div className="flex items-center gap-2 mb-4">
        <Badge variant="outline" className="text-xs bg-blue-500/10 text-blue-500 border-blue-500/30">
          <FileSearch className="w-3 h-3 mr-1" />
          Análise de SEO
        </Badge>
      </div>
      
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
            <ExternalLink className="w-5 h-5 text-primary" />
          </div>
          <div className="min-w-0">
            <h2 className="text-lg font-semibold truncate">{site.base_url}</h2>
            <p className="text-xs text-muted-foreground">{site.owner_email}</p>
          </div>
        </div>
        <span className="shrink-0 text-xs px-3 py-1.5 rounded-full border border-primary/20 text-primary bg-primary/5 font-medium self-start sm:self-center">
          {site.platform || "Plataforma não informada"}
        </span>
      </div>

      <div className="flex flex-col sm:flex-row gap-2 mb-4">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                onClick={onScan}
                disabled={loading}
                className="flex-1 rounded-full border-border hover:border-primary hover:bg-primary/10 hover:text-[#F5F5F5] transition-all group/btn"
              >
                <Rocket className="w-4 h-4 mr-2 group-hover/btn:text-[#F5F5F5]" />
                <span className="hidden sm:inline">Rodar varredura</span>
                <span className="sm:hidden">Varredura</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent className="bg-popover border-border">
              <p className="text-xs">Escaneia todas as páginas do site em busca de problemas de SEO</p>
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                onClick={onReview}
                disabled={loading}
                className="flex-1 rounded-full border-border hover:border-primary hover:bg-primary/10 hover:text-[#F5F5F5] transition-all group/btn2"
              >
                <Lightbulb className="w-4 h-4 mr-2 group-hover/btn2:text-[#F5F5F5]" />
                <span className="hidden sm:inline">Ver sugestões da IA</span>
                <span className="sm:hidden">Sugestões</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent className="bg-popover border-border">
              <p className="text-xs">Veja as sugestões de melhoria geradas pela IA</p>
            </TooltipContent>
          </Tooltip>

        </TooltipProvider>
      </div>

      {/* Info sobre modo auditoria */}
      <div className="flex items-start gap-2 text-xs text-muted-foreground bg-blue-500/5 border border-blue-500/20 rounded-lg px-3 py-2">
        <Info className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
        <p>
          <strong>Auditoria SEO:</strong> Analise qualquer site para identificar problemas de SEO. 
          Para aplicar correções automaticamente, conecte sua loja via <strong>Shopify</strong> ou <strong>Nuvemshop</strong>.
        </p>
      </div>
    </div>
  );
};

export default ActionsCard;
